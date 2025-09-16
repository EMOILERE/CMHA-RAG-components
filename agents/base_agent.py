from abc import ABC, abstractmethod
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class AgentType(Enum):
    """智能体类型枚举"""
    CLASSIFIER = "classifier"  # 分类智能体
    REASONER = "reasoner"      # 推理智能体
    COORDINATOR = "coordinator"  # 协调智能体
    VALIDATOR = "validator"    # 验证智能体
    ESCALATOR = "escalator"    # 升级智能体

class ActionType(Enum):
    """动作类型枚举"""
    ANALYZE = "analyze"
    CLASSIFY = "classify"
    REASON = "reason"
    VALIDATE = "validate"
    COORDINATE = "coordinate"
    ESCALATE = "escalate"
    CONSENSUS = "consensus"

@dataclass
class ThoughtStep:
    """思维链中的单个思考步骤"""
    step_id: str
    agent_id: str
    thought: str
    reasoning: str
    confidence: float
    evidence: List[str]
    timestamp: datetime
    
    def to_dict(self):
        return {
            "step_id": self.step_id,
            "agent_id": self.agent_id,
            "thought": self.thought,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "timestamp": self.timestamp.isoformat()
        }

@dataclass
class ActionStep:
    """动作链中的单个动作步骤"""
    action_id: str
    agent_id: str
    action_type: ActionType
    action_description: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    success: bool
    error_message: Optional[str]
    execution_time: float
    timestamp: datetime
    
    def to_dict(self):
        return {
            "action_id": self.action_id,
            "agent_id": self.agent_id,
            "action_type": self.action_type.value,
            "action_description": self.action_description,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "success": self.success,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp.isoformat()
        }

@dataclass
class AgentDecision:
    """智能体决策结果"""
    agent_id: str
    decision: str
    confidence: float
    reasoning: str
    supporting_evidence: List[str]
    timestamp: datetime
    
    def to_dict(self):
        return {
            "agent_id": self.agent_id,
            "decision": self.decision,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "supporting_evidence": self.supporting_evidence,
            "timestamp": self.timestamp.isoformat()
        }

class BaseAgent(ABC):
    """智能体基类"""
    
    def __init__(self, agent_id: str, agent_type: AgentType, config: Dict[str, Any]):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.config = config
        self.thought_chain: List[ThoughtStep] = []
        self.action_chain: List[ActionStep] = []
        self.performance_metrics = {
            "total_decisions": 0,
            "correct_decisions": 0,
            "average_confidence": 0.0,
            "average_processing_time": 0.0
        }
        
    def add_thought(self, thought: str, reasoning: str, confidence: float, evidence: List[str]) -> str:
        """添加思考步骤到思维链"""
        step_id = f"{self.agent_id}_thought_{len(self.thought_chain)}"
        thought_step = ThoughtStep(
            step_id=step_id,
            agent_id=self.agent_id,
            thought=thought,
            reasoning=reasoning,
            confidence=confidence,
            evidence=evidence,
            timestamp=datetime.utcnow()
        )
        self.thought_chain.append(thought_step)
        logger.debug(f"Agent {self.agent_id} added thought: {thought}")
        return step_id
    
    def add_action(self, action_type: ActionType, description: str, 
                   input_data: Dict[str, Any], output_data: Dict[str, Any],
                   success: bool, execution_time: float, error_message: Optional[str] = None) -> str:
        """添加动作步骤到动作链"""
        action_id = f"{self.agent_id}_action_{len(self.action_chain)}"
        action_step = ActionStep(
            action_id=action_id,
            agent_id=self.agent_id,
            action_type=action_type,
            action_description=description,
            input_data=input_data,
            output_data=output_data,
            success=success,
            error_message=error_message,
            execution_time=execution_time,
            timestamp=datetime.utcnow()
        )
        self.action_chain.append(action_step)
        logger.debug(f"Agent {self.agent_id} performed action: {description}")
        return action_id
    
    def get_thought_chain_summary(self) -> str:
        """获取思维链摘要"""
        if not self.thought_chain:
            return "无思考记录"
        
        summary = f"智能体 {self.agent_id} 的思维过程：\n"
        for i, thought in enumerate(self.thought_chain[-5:], 1):  # 最近5个思考步骤
            summary += f"{i}. {thought.thought}\n"
            summary += f"   推理：{thought.reasoning}\n"
            summary += f"   置信度：{thought.confidence:.2f}\n\n"
        
        return summary
    
    def get_action_chain_summary(self) -> str:
        """获取动作链摘要"""
        if not self.action_chain:
            return "无动作记录"
        
        summary = f"智能体 {self.agent_id} 的动作历史：\n"
        for i, action in enumerate(self.action_chain[-5:], 1):  # 最近5个动作
            status = "成功" if action.success else "失败"
            summary += f"{i}. {action.action_description} [{status}]\n"
            summary += f"   耗时：{action.execution_time:.2f}秒\n\n"
        
        return summary
    
    @abstractmethod
    async def process(self, content: str, context: Dict[str, Any]) -> AgentDecision:
        """处理内容并返回决策"""
        pass
    
    @abstractmethod
    async def collaborate(self, other_agents: List['BaseAgent'], 
                         shared_context: Dict[str, Any]) -> Dict[str, Any]:
        """与其他智能体协作"""
        pass
    
    def update_performance_metrics(self, is_correct: bool, processing_time: float, confidence: float):
        """更新性能指标"""
        self.performance_metrics["total_decisions"] += 1
        if is_correct:
            self.performance_metrics["correct_decisions"] += 1
        
        # 更新平均置信度
        current_avg = self.performance_metrics["average_confidence"]
        total = self.performance_metrics["total_decisions"]
        self.performance_metrics["average_confidence"] = (current_avg * (total - 1) + confidence) / total
        
        # 更新平均处理时间
        current_avg_time = self.performance_metrics["average_processing_time"]
        self.performance_metrics["average_processing_time"] = (current_avg_time * (total - 1) + processing_time) / total
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        total = self.performance_metrics["total_decisions"]
        correct = self.performance_metrics["correct_decisions"]
        accuracy = (correct / total) if total > 0 else 0.0
        
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type.value,
            "total_decisions": total,
            "accuracy": accuracy,
            "average_confidence": self.performance_metrics["average_confidence"],
            "average_processing_time": self.performance_metrics["average_processing_time"]
        }
    
    def reset_chains(self):
        """重置思维链和动作链（用于新的处理任务）"""
        self.thought_chain = []
        self.action_chain = []
