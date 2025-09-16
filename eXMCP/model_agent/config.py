import os
from pydantic import BaseSettings
from typing import List

class AgentConfig(BaseSettings):
    agent_id: str = 'model-agent-1'
    agent_type: str = 'openai'  # openai/anthropic/gemini等
    api_key: str
    model_name: str = 'gpt-4'
    mcp_endpoint: str = 'http://central-agent:8000'
    protocols: List[str] = ['http']  # 支持多协议组合，如['http', 'ws', 'mcp']

    class Config:
        env_prefix = 'AGENT_'
        env_file = '.env'

def load_config():
    return AgentConfig() 