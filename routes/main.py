from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import User, ContentSubmission, ModerationRecord
from extensions import db
from agents.multi_agent_system import MultiAgentSystem
from models2.sentox_glda import SenToxGLDA
from config import Config
import logging
import asyncio

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

# 全局变量：多智能体系统和SenTox模型
multi_agent_system = None
sentox_model = None

def init_systems():
    """初始化多智能体系统和SenTox模型"""
    global multi_agent_system, sentox_model
    
    if multi_agent_system is None:
        config = {
            'dashscope_api_key': Config.DASHSCOPE_API_KEY,
            'max_agents': Config.AGENT_SYSTEM_CONFIG['max_agents'],
            'coordination_timeout': Config.AGENT_SYSTEM_CONFIG['coordination_timeout'],
            'reasoning_depth': Config.AGENT_SYSTEM_CONFIG['reasoning_depth'],
            'consensus_threshold': Config.AGENT_SYSTEM_CONFIG['consensus_threshold']
        }
        multi_agent_system = MultiAgentSystem(config)
        logger.info("多智能体系统初始化完成")
    
    if sentox_model is None:
        sentox_model = SenToxGLDA(Config.SENTOX_MODEL_PATH)
        logger.info("SenTox-GLDA模型初始化完成")

@main_bp.route('/')
def index():
    """首页 - 展示平台概览和功能介绍"""
    init_systems()
    
    # 获取系统统计数据
    total_submissions = ContentSubmission.query.count()
    total_moderated = ModerationRecord.query.count()
    
    # 获取最近的审核活动
    recent_records = ModerationRecord.query.order_by(ModerationRecord.started_at.desc()).limit(5).all()
    
    return render_template('index.html', 
                         total_submissions=total_submissions,
                         total_moderated=total_moderated,
                         recent_records=recent_records)

@main_bp.route('/submit', methods=['GET', 'POST'])
def submit_content():
    """内容提交页面"""
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        platform = request.form.get('platform', 'web')
        
        if not content:
            flash('请输入要审核的内容', 'error')
            return redirect(url_for('main.submit_content'))
        
        if len(content) > 5000:
            flash('内容长度不能超过5000字符', 'error')
            return redirect(url_for('main.submit_content'))
        
        try:
            # 创建内容提交记录
            submission = ContentSubmission(
                content=content,
                platform=platform,
                submitted_by=current_user.id if current_user.is_authenticated else None,
                status='processing'
            )
            db.session.add(submission)
            db.session.commit()
            
            # 异步处理内容审核
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            init_systems()
            result = loop.run_until_complete(
                multi_agent_system.process_content(content, platform)
            )
            
            # 保存审核结果
            moderation_record = ModerationRecord(
                submission_id=submission.id,
                final_decision=result['final_decision'],
                final_confidence=result['confidence'],
                reasoning_chain=result['reasoning'],
                agent_decisions=str(result['agent_decisions']),
                processing_time=result['processing_time']
            )
            moderation_record.completed_at = moderation_record.started_at
            
            db.session.add(moderation_record)
            submission.status = 'completed'
            db.session.commit()
            
            flash('内容审核完成！', 'success')
            return redirect(url_for('main.view_result', submission_id=submission.id))
            
        except Exception as e:
            logger.error(f"内容处理失败: {str(e)}")
            flash(f'处理失败: {str(e)}', 'error')
            return redirect(url_for('main.submit_content'))
    
    return render_template('submit.html')

@main_bp.route('/result/<int:submission_id>')
def view_result(submission_id):
    """查看审核结果"""
    submission = ContentSubmission.query.get_or_404(submission_id)
    moderation_record = ModerationRecord.query.filter_by(submission_id=submission_id).first()
    
    if not moderation_record:
        flash('审核结果不存在', 'error')
        return redirect(url_for('main.index'))
    
    # 解析智能体决策数据
    agent_decisions = {}
    reasoning_chain = []
    
    try:
        import json
        if moderation_record.agent_decisions:
            agent_decisions = eval(moderation_record.agent_decisions)  # 注意：生产环境应使用json.loads
        
        if moderation_record.reasoning_chain:
            reasoning_chain = json.loads(moderation_record.reasoning_chain)
    except:
        pass
    
    return render_template('result.html', 
                         submission=submission,
                         record=moderation_record,
                         agent_decisions=agent_decisions,
                         reasoning_chain=reasoning_chain)

@main_bp.route('/batch')
@login_required
def batch_moderation():
    """批量审核页面"""
    return render_template('batch.html')

@main_bp.route('/realtime')
@login_required
def realtime_monitor():
    """实时监控页面"""
    init_systems()
    
    # 获取系统状态
    system_status = multi_agent_system.get_system_status()
    
    # 获取最近的处理历史
    recent_history = multi_agent_system.get_recent_processing_history(20)
    
    return render_template('realtime.html', 
                         system_status=system_status,
                         recent_history=recent_history)

@main_bp.route('/analytics')
@login_required
def analytics():
    """数据分析页面"""
    # 获取统计数据
    stats = {
        'total_submissions': ContentSubmission.query.count(),
        'total_approved': ModerationRecord.query.filter_by(final_decision='approved').count(),
        'total_rejected': ModerationRecord.query.filter_by(final_decision='rejected').count(),
        'total_escalated': ModerationRecord.query.filter_by(final_decision='escalated').count(),
    }
    
    # 获取平台分布
    platform_stats = db.session.query(
        ContentSubmission.platform,
        db.func.count(ContentSubmission.id)
    ).group_by(ContentSubmission.platform).all()
    
    # 获取最近7天的审核趋势
    from datetime import datetime, timedelta
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    
    daily_stats = db.session.query(
        db.func.date(ModerationRecord.started_at),
        db.func.count(ModerationRecord.id)
    ).filter(ModerationRecord.started_at >= seven_days_ago).group_by(
        db.func.date(ModerationRecord.started_at)
    ).all()
    
    return render_template('analytics.html', 
                         stats=stats,
                         platform_stats=platform_stats,
                         daily_stats=daily_stats)

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('请输入用户名和密码', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('登录成功', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        else:
            flash('用户名或密码错误', 'error')
    
    return render_template('login.html')

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    """注册页面"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # 验证输入
        if not all([username, email, password, confirm_password]):
            flash('所有字段都是必填的', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('两次输入的密码不一致', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('密码长度至少6个字符', 'error')
            return render_template('register.html')
        
        # 检查用户名和邮箱是否已存在
        if User.query.filter_by(username=username).first():
            flash('用户名已存在', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('邮箱已注册', 'error')
            return render_template('register.html')
        
        # 创建新用户
        try:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            flash('注册成功，请登录', 'success')
            return redirect(url_for('main.login'))
        except Exception as e:
            logger.error(f"用户注册失败: {str(e)}")
            flash('注册失败，请稍后重试', 'error')
    
    return render_template('register.html')

@main_bp.route('/logout')
@login_required
def logout():
    """登出"""
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('main.index'))

@main_bp.route('/profile')
@login_required
def profile():
    """用户个人资料页面"""
    user_submissions = ContentSubmission.query.filter_by(
        submitted_by=current_user.id
    ).order_by(ContentSubmission.submitted_at.desc()).limit(10).all()
    
    return render_template('profile.html', submissions=user_submissions)

@main_bp.route('/about')
def about():
    """关于页面 - 介绍科研背景和技术原理"""
    init_systems()
    
    # 获取模型信息
    sentox_info = sentox_model.get_model_info()
    system_status = multi_agent_system.get_system_status()
    
    return render_template('about.html', 
                         sentox_info=sentox_info,
                         system_status=system_status)

@main_bp.route('/health')
def health_check():
    """系统健康检查"""
    try:
        init_systems()
        
        # 检查数据库连接
        db.session.execute('SELECT 1')
        
        # 检查模型状态
        sentox_status = sentox_model.get_model_info()
        
        # 异步检查多智能体系统
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        agent_health = loop.run_until_complete(multi_agent_system.health_check())
        
        return jsonify({
            'status': 'healthy',
            'timestamp': '2024-01-01T00:00:00Z',
            'database': 'connected',
            'sentox_model': sentox_status,
            'multi_agent_system': agent_health
        })
        
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': '2024-01-01T00:00:00Z'
        }), 500
