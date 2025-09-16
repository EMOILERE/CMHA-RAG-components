from mcp.server.stdio import ServerSession
from mcp import ServerNotification
from mcp_utils.redis_registry import RedisRegistry
import asyncio
import time

REDIS_URL = 'redis://localhost:6379/0'
registry = RedisRegistry(REDIS_URL)

async def handle_notification(session, notification):
    method = notification.method
    params = notification.params or {}
    agent_id = params.get('agent_id')
    if method == 'agent/register':
        registry.register_agent(agent_id, params)
        print(f"[MCP] Agent {agent_id} 注册: {params}")
    elif method == 'agent/unregister':
        registry.unregister_agent(agent_id)
        print(f"[MCP] Agent {agent_id} 注销")
    elif method == 'agent/heartbeat':
        registry.heartbeat(agent_id)
        print(f"[MCP] Agent {agent_id} 心跳: cpu={params.get('cpu')}, processes={params.get('processes')}")
    else:
        print(f"[MCP] Unknown notification: {method}")

async def mcp_server_main(read_stream, write_stream):
    async with ServerSession(read_stream, write_stream) as session:
        await session.initialize()
        while True:
            notification = await session.read_notification()
            await handle_notification(session, notification)

# 用法示例（需与具体MCP transport集成，如stdio、http、ws等）
# asyncio.run(mcp_server_main(read_stream, write_stream)) 