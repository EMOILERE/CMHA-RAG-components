import asyncio
import uuid
import atexit
import time
import psutil
import threading
from model_agent.config import load_config
from model_agent.openai_backend import OpenAIBackend
from mcp_utils.comm_interface import HTTPCommAdapter, WSCommAdapter, GRPCCommAdapter, MCPCommAdapter
from model_agent.http_client import ModelAgentHTTPClient
from model_agent.ws_client import ModelAgentWSClient
from model_agent.grpc_client import GRPCClient
from model_agent.mcp_client import MCPClient

HEARTBEAT_INTERVAL = 5

async def handle_message(msg):
    # 统一的任务处理逻辑
    print(f"[ModelAgent] Received message: {msg}")
    # 这里可根据msg内容调用大模型推理并回传结果
    # ...

async def agent_lifecycle(adapter, proto, agent_id, agent_type, model_name, meta, api_key):
    # 注册
    if hasattr(adapter, 'register'):
        await adapter.register(agent_id, agent_type, meta)
    # 启动心跳
    if hasattr(adapter, 'heartbeat_loop'):
        asyncio.create_task(adapter.heartbeat_loop(HEARTBEAT_INTERVAL))
    # 注销
    def cleanup():
        if hasattr(adapter, 'unregister'):
            try:
                asyncio.get_event_loop().run_until_complete(adapter.unregister())
            except Exception:
                pass
    atexit.register(cleanup)

async def main():
    config = load_config()
    agent_id = config.agent_id or f"agent-{uuid.uuid4()}"
    print(f"[ModelAgent] Starting as {agent_id}, type={config.agent_type}, model={config.model_name}, protocols={config.protocols}")

    # 多协议适配器
    adapters = []
    for proto in config.protocols:
        if proto == 'http':
            http_client = ModelAgentHTTPClient(config.mcp_endpoint, agent_id, config.agent_type, meta={"model_name": config.model_name}, api_key=config.api_key)
            adapter = HTTPCommAdapter(http_client)
        elif proto == 'ws':
            ws_client = ModelAgentWSClient(config.mcp_endpoint, agent_id, config.agent_type, config.model_name, meta={"model_name": config.model_name}, api_key=config.api_key)
            adapter = WSCommAdapter(ws_client)
        elif proto == 'grpc':
            grpc_client = GRPCClient(config.mcp_endpoint, api_key=config.api_key)
            adapter = GRPCCommAdapter(grpc_client)
        elif proto == 'mcp':
            mcp_client = MCPClient(config.mcp_endpoint, api_key=config.api_key)
            adapter = MCPCommAdapter(mcp_client)
        else:
            continue
        adapters.append(adapter)
        # 启动注册/心跳/注销机制
        asyncio.create_task(agent_lifecycle(
            adapter, proto, agent_id, config.agent_type, config.model_name, {"model_name": config.model_name}, config.api_key
        ))

    # 启动所有协议的监听
    await asyncio.gather(*(adapter.start() for adapter in adapters))
    await asyncio.gather(*(adapter.receive_message(handle_message) for adapter in adapters))

if __name__ == '__main__':
    asyncio.run(main()) 