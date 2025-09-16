from flask import Flask
from config import Config
from extensions import db, migrate, login_manager
from routes import main_bp, api_bp, admin_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = '请先登录以访问此页面'
    
    # 配置用户加载器
    @login_manager.user_loader
    def load_user(user_id):
        # 导入User模型（在函数内部导入避免循环导入）
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from models import User
        return User.query.get(int(user_id))
    
    # 注册蓝图
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
