import asyncio
import logging
import time
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from .sub_agents import BaseSubAgent, SubAgentType
from .communication_hub import AgentCommunicationHub

logger = logging.getLogger(__name__)

class ToxicityDetectorAgent(BaseSubAgent):
    """毒性检测智能体"""
    
    def __init__(self, communication_hub: AgentCommunicationHub, config: Dict[str, Any]):
        super().__init__("toxicity_detector", SubAgentType.TOXICITY_DETECTOR, communication_hub, config)
        
        # 毒性关键词库
        self.toxicity_keywords = {
            "hate_speech": [
                "傻逼", "智障", "脑残", "白痴", "蠢货", "废物", "垃圾人", "人渣",
                "死胖子", "丑八怪", "穷逼", "贱人", "婊子", "臭婊子"
            ],
            "violence_threats": [
                "杀死你", "弄死你", "打死你", "干掉你", "砍死", "刀你", "炸死",
                "枪毙", "弄残你", "废了你", "整死你", "搞死你", "灭了你"
            ],
            "harassment": [
                "滚", "去死", "操你妈", "草泥马", "他妈的", "妈的", "狗屎",
                "混蛋", "王八蛋", "畜生", "贱货", "下贱"
            ],
            "sexual_content": [
                "做爱", "性交", "操逼", "日你", "黄片", "色情", "裸体", "性器官",
                "强奸", "轮奸", "性奴", "援交", "包养"
            ],
            "discrimination": [
                "黑鬼", "残疾", "智力低下", "农民工", "外地人", "乡巴佬",
                "土包子", "暴发户", "凤凰男", "直男癌"
            ],
            "self_harm": [
                "自杀", "自残", "割腕", "跳楼", "上吊", "服毒", "想死",
                "活不下去", "不想活", "解脱"
            ]
        }
        
        # 风险等级权重
        self.category_weights = {
            "violence_threats": 1.0,
            "hate_speech": 0.9,
            "harassment": 0.8,
            "sexual_content": 0.85,
            "discrimination": 0.75,
            "self_harm": 0.95
        }
    
    async def analyze_content(self, content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """毒性检测分析"""
        # 关键词检测
        keyword_analysis = await self._keyword_based_detection(content)
        
        # 模式检测
        pattern_analysis = await self._pattern_based_detection(content)
        
        # 上下文增强检测
        context_analysis = await self._context_enhanced_detection(content, context)
        
        # LLM增强检测
        llm_analysis = await self._llm_enhanced_detection(content)
        
        # 综合风险评估
        risk_assessment = self._calculate_toxicity_risk(
            keyword_analysis, pattern_analysis, context_analysis, llm_analysis
        )
        
        return {
            "summary": "毒性检测分析完成",
            "keyword_analysis": keyword_analysis,
            "pattern_analysis": pattern_analysis,
            "context_analysis": context_analysis,
            "llm_analysis": llm_analysis,
            "risk_assessment": risk_assessment,
            "confidence": risk_assessment.get("confidence", 0.7)
        }
    
    def get_capabilities(self) -> List[str]:
        return ["toxicity_detection", "hate_speech_recognition", "violence_detection", 
                "harassment_detection", "sexual_content_detection", "self_harm_detection"]
    
    async def _keyword_based_detection(self, content: str) -> Dict[str, Any]:
        """基于关键词的毒性检测"""
        detected_categories = {}
        total_toxic_words = 0
        detected_words = []
        
        for category, keywords in self.toxicity_keywords.items():
            category_matches = []
            for keyword in keywords:
                if keyword in content:
                    category_matches.append(keyword)
                    detected_words.append(keyword)
            
            if category_matches:
                detected_categories[category] = {
                    "count": len(category_matches),
                    "words": category_matches,
                    "severity": len(category_matches) * self.category_weights.get(category, 0.5)
                }
                total_toxic_words += len(category_matches)
        
        # 计算毒性密度
        word_count = len(content.split())
        toxicity_density = total_toxic_words / max(1, word_count)
        
        return {
            "detected_categories": detected_categories,
            "total_toxic_words": total_toxic_words,
            "detected_words": detected_words,
            "toxicity_density": toxicity_density,
            "categories_count": len(detected_categories)
        }
    
    async def _pattern_based_detection(self, content: str) -> Dict[str, Any]:
        """基于模式的毒性检测"""
        patterns = {
            "repeated_chars": r'(.)\1{3,}',  # 重复字符（如：草草草草）
            "excessive_punctuation": r'[!！]{3,}|[?？]{3,}',  # 过度标点
            "caps_shouting": r'[A-Z]{5,}',  # 大写字母喊叫
            "number_letter_mix": r'[0-9]+[a-zA-Z]+[0-9]+',  # 数字字母混合（可能是绕过检测）
            "special_char_flood": r'[#@$%^&*]{3,}',  # 特殊字符刷屏
            "url_suspicious": r'http[s]?://[^\s]+|www\.[^\s]+',  # 可疑链接
            "contact_info": r'(?:QQ|微信|电话|手机)[:：]?\s*\d+',  # 联系方式
        }
        
        pattern_matches = {}
        total_pattern_score = 0
        
        for pattern_name, pattern in patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                pattern_matches[pattern_name] = {
                    "count": len(matches),
                    "matches": matches[:5],  # 只保留前5个匹配
                    "severity": len(matches) * 0.2
                }
                total_pattern_score += len(matches) * 0.2
        
        return {
            "pattern_matches": pattern_matches,
            "total_pattern_score": min(1.0, total_pattern_score),
            "pattern_count": len(pattern_matches)
        }
    
    async def _context_enhanced_detection(self, content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """上下文增强的毒性检测"""
        platform = context.get("platform", "unknown")
        user_history = context.get("user_history", {})
        
        # 平台特定规则
        platform_risk_factor = {
            "weibo": 1.1,  # 微博相对宽松
            "wechat": 1.3,  # 微信群聊可能更严格
            "douyin": 1.2,  # 抖音中等
            "zhihu": 1.0,   # 知乎相对理性
            "unknown": 1.0
        }.get(platform, 1.0)
        
        # 用户历史行为影响
        user_risk_factor = 1.0
        if user_history.get("previous_violations", 0) > 2:
            user_risk_factor = 1.5
        elif user_history.get("reputation_score", 0) > 0.8:
            user_risk_factor = 0.8
        
        # 内容长度影响
        length_factor = 1.0
        if len(content) < 10:
            length_factor = 1.2  # 短内容更可能是垃圾信息
        elif len(content) > 200:
            length_factor = 0.9  # 长内容可能更有价值
        
        # 时间上下文（如果有）
        time_factor = 1.0
        current_hour = datetime.now().hour
        if 22 <= current_hour or current_hour <= 6:
            time_factor = 1.1  # 深夜发布内容风险稍高
        
        combined_factor = platform_risk_factor * user_risk_factor * length_factor * time_factor
        
        return {
            "platform_risk_factor": platform_risk_factor,
            "user_risk_factor": user_risk_factor,
            "length_factor": length_factor,
            "time_factor": time_factor,
            "combined_context_factor": combined_factor,
            "context_considerations": [
                f"平台: {platform}",
                f"用户历史违规: {user_history.get('previous_violations', 0)}次",
                f"内容长度: {len(content)}字符"
            ]
        }
    
    async def _llm_enhanced_detection(self, content: str) -> Dict[str, Any]:
        """LLM增强的毒性检测"""
        toxicity_prompt = f"""
你是一个专业的中文内容毒性检测系统。请仔细分析以下内容是否包含有害信息：

内容：{content}

请从以下维度进行分析：
1. 仇恨言论：是否包含针对特定群体的仇恨或偏见
2. 暴力威胁：是否包含威胁、恐吓或煽动暴力的内容
3. 骚扰辱骂：是否包含人身攻击、辱骂或恶意骚扰
4. 色情内容：是否包含不当的性相关内容
5. 歧视言论：是否包含基于身份特征的歧视
6. 自我伤害：是否包含自杀、自残等内容
7. 虚假信息：是否可能是谣言或误导性信息
8. 垃圾信息：是否是广告、诈骗或无意义内容

请按以下JSON格式回答：
{{
    "is_toxic": true/false,
    "toxicity_score": 0.0-1.0的毒性评分,
    "detected_types": ["检测到的毒性类型"],
    "severity_level": 1-5的严重程度,
    "explanation": "详细解释",
    "confidence": 0.0-1.0的置信度
}}
"""
        
        llm_result = await self.available_tools["llm_caller"](toxicity_prompt)
        
        if llm_result.get("status") == "success":
            return self._parse_toxicity_result(llm_result.get("response", ""))
        else:
            return {
                "is_toxic": False,
                "toxicity_score": 0.1,
                "detected_types": [],
                "severity_level": 1,
                "explanation": "LLM分析失败，使用保守判断",
                "confidence": 0.3
            }
    
    def _parse_toxicity_result(self, llm_response: str) -> Dict[str, Any]:
        """解析LLM的毒性检测结果"""
        try:
            import json
            start_idx = llm_response.find('{')
            end_idx = llm_response.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = llm_response[start_idx:end_idx]
                result = json.loads(json_str)
                
                # 验证字段
                required_fields = ["is_toxic", "toxicity_score", "confidence"]
                if all(field in result for field in required_fields):
                    return result
        except:
            pass
        
        return {
            "is_toxic": False,
            "toxicity_score": 0.2,
            "detected_types": ["parse_error"],
            "severity_level": 1,
            "explanation": "无法解析LLM响应",
            "confidence": 0.2
        }
    
    def _calculate_toxicity_risk(self, keyword_analysis: Dict, pattern_analysis: Dict,
                                context_analysis: Dict, llm_analysis: Dict) -> Dict[str, Any]:
        """计算综合毒性风险"""
        # 关键词检测权重40%
        keyword_score = 0
        if keyword_analysis["total_toxic_words"] > 0:
            keyword_score = min(1.0, keyword_analysis["toxicity_density"] * 5)
        
        # 模式检测权重20%
        pattern_score = pattern_analysis["total_pattern_score"]
        
        # LLM检测权重35%
        llm_score = llm_analysis.get("toxicity_score", 0)
        
        # 上下文调整权重5%
        context_factor = context_analysis["combined_context_factor"]
        
        # 综合评分
        base_score = (keyword_score * 0.4 + pattern_score * 0.2 + llm_score * 0.35)
        final_score = min(1.0, base_score * context_factor)
        
        # 确定风险等级
        if final_score >= 0.8:
            risk_level = "high"
            recommendation = "reject"
        elif final_score >= 0.6:
            risk_level = "medium"
            recommendation = "review"
        elif final_score >= 0.3:
            risk_level = "low"
            recommendation = "monitor"
        else:
            risk_level = "minimal"
            recommendation = "approve"
        
        # 置信度计算
        confidence_factors = [
            keyword_analysis["total_toxic_words"] > 0,  # 有明确关键词
            pattern_analysis["pattern_count"] > 0,      # 有可疑模式
            llm_analysis.get("confidence", 0.5) > 0.7  # LLM高置信度
        ]
        confidence = 0.5 + sum(confidence_factors) * 0.15
        
        return {
            "toxicity_score": final_score,
            "risk_level": risk_level,
            "recommendation": recommendation,
            "confidence": min(1.0, confidence),
            "score_breakdown": {
                "keyword_contribution": keyword_score * 0.4,
                "pattern_contribution": pattern_score * 0.2,
                "llm_contribution": llm_score * 0.35,
                "context_factor": context_factor
            },
            "detected_issues": self._summarize_detected_issues(
                keyword_analysis, pattern_analysis, llm_analysis
            )
        }
    
    def _summarize_detected_issues(self, keyword_analysis: Dict, 
                                  pattern_analysis: Dict, llm_analysis: Dict) -> List[str]:
        """总结检测到的问题"""
        issues = []
        
        # 关键词问题
        if keyword_analysis["total_toxic_words"] > 0:
            categories = list(keyword_analysis["detected_categories"].keys())
            issues.append(f"检测到毒性关键词，涉及类别: {', '.join(categories)}")
        
        # 模式问题
        if pattern_analysis["pattern_count"] > 0:
            patterns = list(pattern_analysis["pattern_matches"].keys())
            issues.append(f"检测到可疑模式: {', '.join(patterns)}")
        
        # LLM检测问题
        if llm_analysis.get("is_toxic"):
            llm_types = llm_analysis.get("detected_types", [])
            if llm_types:
                issues.append(f"LLM检测到毒性类型: {', '.join(llm_types)}")
        
        return issues if issues else ["未检测到明显问题"]

class ContextAnalyzerAgent(BaseSubAgent):
    """上下文分析智能体"""
    
    def __init__(self, communication_hub: AgentCommunicationHub, config: Dict[str, Any]):
        super().__init__("context_analyzer", SubAgentType.CONTEXT_ANALYZER, communication_hub, config)
    
    async def analyze_content(self, content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """上下文分析"""
        # 文化背景分析
        cultural_analysis = await self._cultural_context_analysis(content)
        
        # 社交媒体上下文分析
        social_context = await self._social_media_context_analysis(content, context)
        
        # 隐含意义分析
        implicit_analysis = await self._implicit_meaning_analysis(content)
        
        # 时间敏感性分析
        temporal_analysis = await self._temporal_context_analysis(content, context)
        
        return {
            "summary": "上下文分析完成",
            "cultural_analysis": cultural_analysis,
            "social_context": social_context,
            "implicit_analysis": implicit_analysis,
            "temporal_analysis": temporal_analysis,
            "confidence": 0.75
        }
    
    def get_capabilities(self) -> List[str]:
        return ["cultural_context_analysis", "social_media_context", "implicit_meaning_detection", 
                "temporal_context_analysis", "platform_specific_analysis"]
    
    async def _cultural_context_analysis(self, content: str) -> Dict[str, Any]:
        """文化背景分析"""
        # 地域特色词汇
        regional_words = {
            "北方": ["俺", "咱", "嘞", "呗", "整", "老铁"],
            "南方": ["阿", "嘅", "咧", "啦", "係", "嘢"],
            "网络文化": ["yyds", "绝绝子", "cpdd", "u1s1", "awsl", "xswl"],
            "年轻人": ["好家伙", "绝了", "真香", "我吐了", "芜湖", "起飞"],
            "传统文化": ["古风", "汉服", "国潮", "传统", "文化", "古典"]
        }
        
        detected_cultural_markers = {}
        for category, words in regional_words.items():
            matches = [word for word in words if word in content]
            if matches:
                detected_cultural_markers[category] = matches
        
        # 正式程度分析
        formal_indicators = ["请", "您", "敬请", "恳请", "谨", "此致", "敬礼"]
        informal_indicators = ["哈哈", "嘿嘿", "哎呀", "哇", "咋", "啥", "嘛"]
        
        formal_count = sum(1 for word in formal_indicators if word in content)
        informal_count = sum(1 for word in informal_indicators if word in content)
        
        if formal_count > informal_count:
            formality_level = "formal"
        elif informal_count > formal_count:
            formality_level = "informal"
        else:
            formality_level = "neutral"
        
        return {
            "cultural_markers": detected_cultural_markers,
            "formality_level": formality_level,
            "formal_indicators": formal_count,
            "informal_indicators": informal_count,
            "cultural_diversity_score": len(detected_cultural_markers)
        }
    
    async def _social_media_context_analysis(self, content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """社交媒体上下文分析"""
        platform = context.get("platform", "unknown")
        
        # 平台特定特征
        platform_features = {
            "weibo": {"hashtags": r'#[^#\s]+#', "mentions": r'@[\w\u4e00-\u9fa5]+'},
            "douyin": {"challenges": r'#[^#\s]+挑战', "music": r'♪.*♪'},
            "wechat": {"emoji": r'\[[\w\u4e00-\u9fa5]+\]', "voice": r'语音'},
            "zhihu": {"topic": r'话题', "professional": r'专业|学术|研究'}
        }
        
        detected_features = {}
        if platform in platform_features:
            for feature_name, pattern in platform_features[platform].items():
                matches = re.findall(pattern, content)
                if matches:
                    detected_features[feature_name] = matches
        
        # 互动意图分析
        interaction_patterns = {
            "求关注": r'关注|点赞|转发|收藏',
            "求互动": r'评论|讨论|交流|分享',
            "营销推广": r'链接|购买|优惠|促销|代理',
            "求助": r'求助|帮忙|请教|怎么办',
            "炫耀": r'晒|秀|炫|展示'
        }
        
        interaction_intents = {}
        for intent, pattern in interaction_patterns.items():
            if re.search(pattern, content):
                interaction_intents[intent] = True
        
        return {
            "platform": platform,
            "platform_specific_features": detected_features,
            "interaction_intents": interaction_intents,
            "likely_audience": self._infer_target_audience(content, detected_features)
        }
    
    def _infer_target_audience(self, content: str, features: Dict[str, Any]) -> str:
        """推断目标受众"""
        if "professional" in features:
            return "专业人士"
        elif any(word in content for word in ["宝宝", "妈妈", "育儿"]):
            return "父母群体"
        elif any(word in content for word in ["游戏", "电竞", "主播"]):
            return "游戏玩家"
        elif any(word in content for word in ["学习", "考试", "作业"]):
            return "学生群体"
        else:
            return "普通用户"
    
    async def _implicit_meaning_analysis(self, content: str) -> Dict[str, Any]:
        """隐含意义分析"""
        implicit_prompt = f"""
请分析以下中文内容是否包含隐含意义、暗示或需要背景知识才能理解的信息：

内容：{content}

请分析：
1. 是否存在反讽或讽刺
2. 是否有文化梗或网络梗
3. 是否有隐晦的表达
4. 是否需要特定背景知识
5. 是否存在双关语

请以JSON格式回答：
{{
    "has_implicit_meaning": true/false,
    "irony_detected": true/false,
    "cultural_references": ["文化梗或网络梗"],
    "requires_background": true/false,
    "implicit_risk_level": 0.0-1.0,
    "explanation": "解释说明"
}}
"""
        
        llm_result = await self.available_tools["llm_caller"](implicit_prompt)
        
        if llm_result.get("status") == "success":
            return self._parse_implicit_result(llm_result.get("response", ""))
        else:
            return {
                "has_implicit_meaning": False,
                "irony_detected": False,
                "cultural_references": [],
                "requires_background": False,
                "implicit_risk_level": 0.1,
                "explanation": "LLM分析失败"
            }
    
    def _parse_implicit_result(self, llm_response: str) -> Dict[str, Any]:
        """解析隐含意义分析结果"""
        try:
            import json
            start_idx = llm_response.find('{')
            end_idx = llm_response.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = llm_response[start_idx:end_idx]
                return json.loads(json_str)
        except:
            pass
        
        return {
            "has_implicit_meaning": False,
            "irony_detected": False,
            "cultural_references": [],
            "requires_background": False,
            "implicit_risk_level": 0.2,
            "explanation": "解析失败"
        }
    
    async def _temporal_context_analysis(self, content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """时间敏感性分析"""
        # 时间相关词汇
        time_references = {
            "urgent": r'紧急|急|马上|立即|赶紧|火速',
            "deadline": r'截止|期限|最后|结束|到期',
            "trending": r'热点|热门|流行|最新|最近',
            "outdated": r'过时|老旧|以前|原来|过去'
        }
        
        time_features = {}
        for category, pattern in time_references.items():
            matches = re.findall(pattern, content)
            if matches:
                time_features[category] = len(matches)
        
        # 分析时效性
        urgency_score = sum(time_features.get(cat, 0) for cat in ["urgent", "deadline"])
        relevance_score = sum(time_features.get(cat, 0) for cat in ["trending"])
        
        return {
            "time_features": time_features,
            "urgency_score": min(1.0, urgency_score * 0.3),
            "relevance_score": min(1.0, relevance_score * 0.2),
            "time_sensitivity": "high" if urgency_score > 2 else "low"
        }

class RiskAssessorAgent(BaseSubAgent):
    """风险评估智能体"""
    
    def __init__(self, communication_hub: AgentCommunicationHub, config: Dict[str, Any]):
        super().__init__("risk_assessor", SubAgentType.RISK_ASSESSOR, communication_hub, config)
    
    async def analyze_content(self, content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """综合风险评估"""
        # 收集其他智能体的分析结果
        peer_analyses = await self._collect_peer_analyses(context)
        
        # 执行独立风险分析
        independent_analysis = await self._independent_risk_analysis(content)
        
        # 综合风险评估
        comprehensive_risk = await self._comprehensive_risk_assessment(
            content, independent_analysis, peer_analyses
        )
        
        return {
            "summary": "综合风险评估完成",
            "independent_analysis": independent_analysis,
            "peer_analyses_summary": peer_analyses,
            "comprehensive_risk": comprehensive_risk,
            "confidence": comprehensive_risk.get("confidence", 0.8)
        }
    
    def get_capabilities(self) -> List[str]:
        return ["comprehensive_risk_assessment", "peer_analysis_integration", 
                "impact_assessment", "mitigation_recommendation"]
    
    async def _collect_peer_analyses(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """收集其他智能体的分析结果"""
        session_id = context.get("session_id", "")
        
        # 从共享上下文获取其他智能体的结果
        shared_data = self.comm_hub.get_shared_context()
        
        peer_results = {}
        for key, value in shared_data.items():
            if session_id in key and "result" in key:
                agent_type = key.replace(f"{session_id}_", "").replace("_result", "")
                peer_results[agent_type] = value
        
        return peer_results
    
    async def _independent_risk_analysis(self, content: str) -> Dict[str, Any]:
        """独立风险分析"""
        # 内容风险因子
        risk_factors = {
            "length_risk": self._assess_length_risk(content),
            "complexity_risk": self._assess_complexity_risk(content),
            "emotional_risk": self._assess_emotional_risk(content),
            "linguistic_risk": self._assess_linguistic_risk(content)
        }
        
        # 计算综合风险
        total_risk = sum(risk_factors.values()) / len(risk_factors)
        
        return {
            "risk_factors": risk_factors,
            "total_risk_score": total_risk,
            "risk_level": self._categorize_risk_level(total_risk)
        }
    
    def _assess_length_risk(self, content: str) -> float:
        """评估长度相关风险"""
        length = len(content)
        if length < 5:
            return 0.8  # 过短内容风险高
        elif length > 1000:
            return 0.3  # 过长内容相对安全
        else:
            return 0.1  # 正常长度
    
    def _assess_complexity_risk(self, content: str) -> float:
        """评估复杂度风险"""
        words = content.split()
        unique_ratio = len(set(words)) / max(1, len(words))
        
        if unique_ratio < 0.3:
            return 0.6  # 重复度高，可能是垃圾信息
        elif unique_ratio > 0.8:
            return 0.2  # 词汇丰富，相对安全
        else:
            return 0.3
    
    def _assess_emotional_risk(self, content: str) -> float:
        """评估情感风险"""
        emotional_intensifiers = ['！', '？', '!!!', '???', '非常', '极其', '超级']
        intensity_count = sum(content.count(word) for word in emotional_intensifiers)
        
        return min(1.0, intensity_count * 0.2)
    
    def _assess_linguistic_risk(self, content: str) -> float:
        """评估语言风险"""
        # 检测可能的编码或替换字符
        substitution_patterns = r'[0-9]{2,}|[a-zA-Z]{3,}|[@#$%^&*]{2,}'
        substitutions = len(re.findall(substitution_patterns, content))
        
        return min(1.0, substitutions * 0.3)
    
    def _categorize_risk_level(self, risk_score: float) -> str:
        """分类风险等级"""
        if risk_score >= 0.7:
            return "high"
        elif risk_score >= 0.4:
            return "medium"
        elif risk_score >= 0.2:
            return "low"
        else:
            return "minimal"
    
    async def _comprehensive_risk_assessment(self, content: str, independent: Dict, 
                                           peer_analyses: Dict) -> Dict[str, Any]:
        """综合风险评估"""
        # 收集所有风险评分
        risk_scores = [independent["total_risk_score"]]
        
        # 从其他智能体结果中提取风险评分
        for agent_type, analysis in peer_analyses.items():
            if isinstance(analysis, dict):
                # 尝试提取各种可能的风险评分
                score = (analysis.get("risk_score") or 
                        analysis.get("toxicity_score") or 
                        analysis.get("confidence", 0.5))
                if isinstance(score, (int, float)):
                    risk_scores.append(score)
        
        # 计算加权平均风险
        if len(risk_scores) > 1:
            # 给独立分析更高权重
            weights = [0.4] + [0.6 / (len(risk_scores) - 1)] * (len(risk_scores) - 1)
            final_risk = sum(score * weight for score, weight in zip(risk_scores, weights))
        else:
            final_risk = risk_scores[0]
        
        # 置信度评估
        confidence = 0.6 + (len(peer_analyses) * 0.1)  # 更多智能体参与提高置信度
        confidence = min(1.0, confidence)
        
        # 生成建议
        recommendations = self._generate_risk_recommendations(final_risk, peer_analyses)
        
        return {
            "final_risk_score": final_risk,
            "risk_level": self._categorize_risk_level(final_risk),
            "confidence": confidence,
            "contributing_factors": risk_scores,
            "peer_contributions": len(peer_analyses),
            "recommendations": recommendations,
            "assessment_summary": self._generate_assessment_summary(final_risk, peer_analyses)
        }
    
    def _generate_risk_recommendations(self, risk_score: float, peer_analyses: Dict) -> List[str]:
        """生成风险处理建议"""
        recommendations = []
        
        if risk_score >= 0.8:
            recommendations.append("强烈建议拒绝发布")
            recommendations.append("标记用户进行进一步审查")
        elif risk_score >= 0.6:
            recommendations.append("建议人工审核")
            recommendations.append("可考虑限制传播范围")
        elif risk_score >= 0.3:
            recommendations.append("可以发布但需监控反馈")
            recommendations.append("建议增加内容标签")
        else:
            recommendations.append("可以正常发布")
            recommendations.append("定期抽查即可")
        
        # 基于特定问题的建议
        if any("toxicity" in str(analysis) for analysis in peer_analyses.values()):
            recommendations.append("检测到毒性内容，建议加强过滤")
        
        return recommendations
    
    def _generate_assessment_summary(self, risk_score: float, peer_analyses: Dict) -> str:
        """生成评估摘要"""
        risk_level = self._categorize_risk_level(risk_score)
        agent_count = len(peer_analyses)
        
        summary = f"综合{agent_count}个智能体的分析结果，最终风险等级为{risk_level}（评分: {risk_score:.2f}）。"
        
        if risk_level == "high":
            summary += "存在明显风险因素，不建议发布。"
        elif risk_level == "medium":
            summary += "存在潜在风险，建议谨慎处理。"
        else:
            summary += "风险在可接受范围内。"
        
        return summary
