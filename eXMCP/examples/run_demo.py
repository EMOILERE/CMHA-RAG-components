"""
多协议混合场景端到端demo：
- 启动中心agent（支持HTTP+WebSocket）
- 启动model agent1（HTTP）
- 启动model agent2（WebSocket）
- 启动model agent3（MCP，伪代码）
"""
import os
import subprocess
import time

# 启动中心agent（支持多协议，假设main.py已支持）
subprocess.Popen([
    'python', 'central_agent/main.py', '--protocol', 'http'
])
subprocess.Popen([
    'python', 'central_agent/main.py', '--protocol', 'ws', '--port', '8001'
])

# 启动model agent1（HTTP）
os.environ['AGENT_API_KEY'] = '<your-openai-api-key>'
os.environ['AGENT_AGENT_TYPE'] = 'openai'
os.environ['AGENT_MODEL_NAME'] = 'gpt-4'
os.environ['AGENT_AGENT_ID'] = 'openai-agent-http'
os.environ['AGENT_MCP_ENDPOINT'] = 'http://localhost:8000'
os.environ['AGENT_PROTOCOLS'] = 'http'
subprocess.Popen([
    'python', 'model_agent/main.py', '--protocol', 'http'
])

# 启动model agent2（WebSocket）
os.environ['AGENT_AGENT_ID'] = 'openai-agent-ws'
os.environ['AGENT_PROTOCOLS'] = 'ws'
os.environ['AGENT_MCP_ENDPOINT'] = 'ws://localhost:8001'
subprocess.Popen([
    'python', 'model_agent/main.py', '--protocol', 'ws'
])

# 启动model agent3（MCP）
os.environ['AGENT_AGENT_ID'] = 'openai-agent-mcp'
os.environ['AGENT_PROTOCOLS'] = 'mcp'
os.environ['AGENT_MCP_ENDPOINT'] = '<your-mcp-endpoint>'
os.environ['AGENT_API_KEY'] = '<your-mcp-api-key>'
subprocess.Popen([
    'python', 'model_agent/main.py', '--protocol', 'mcp'
])

# 启动model agent4（gRPC）
os.environ['AGENT_AGENT_ID'] = 'openai-agent-grpc'
os.environ['AGENT_PROTOCOLS'] = 'grpc'
os.environ['AGENT_MCP_ENDPOINT'] = 'localhost:50051'
os.environ['AGENT_API_KEY'] = '<your-grpc-api-key>'
subprocess.Popen([
    'python', 'model_agent/main.py', '--protocol', 'grpc'
])

print('Demo agents started. 请根据实际情况完善MCP端到端集成。') 