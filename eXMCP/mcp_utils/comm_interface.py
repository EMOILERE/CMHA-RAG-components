import abc
from typing import Any, Callable, Awaitable
import asyncio

class AgentCommInterface(abc.ABC):
    @abc.abstractmethod
    async def send_message(self, target: str, content: dict) -> Any:
        pass

    @abc.abstractmethod
    async def receive_message(self, handler: Callable[[dict], Awaitable[None]]):
        pass

    @abc.abstractmethod
    async def start(self):
        pass

# MCP适配器
class MCPCommAdapter(AgentCommInterface):
    def __init__(self, mcp_client):
        self.mcp_client = mcp_client

    async def send_message(self, target: str, content: dict) -> Any:
        return await self.mcp_client.send(target, content)

    async def receive_message(self, handler: Callable[[dict], Awaitable[None]]):
        # 假设mcp_client.recv_stream()为异步生成器
        async for msg in self.mcp_client.recv_stream():
            await handler(msg)

    async def start(self):
        await self.mcp_client.connect()

# HTTP适配器
class HTTPCommAdapter(AgentCommInterface):
    def __init__(self, http_client):
        self.http_client = http_client
        self._handler = None
        self._polling = False

    async def send_message(self, target: str, content: dict) -> Any:
        return self.http_client.assign_task(target, content)

    async def receive_message(self, handler: Callable[[dict], Awaitable[None]]):
        self._handler = handler
        self._polling = True
        async def poll():
            while self._polling:
                task = self.http_client.next_task()
                if task:
                    await handler(task)
                await asyncio.sleep(2)
        asyncio.create_task(poll())

    async def start(self):
        pass

# WebSocket适配器
class WSCommAdapter(AgentCommInterface):
    def __init__(self, ws_client):
        self.ws_client = ws_client
        self._handler = None

    async def send_message(self, target: str, content: dict) -> Any:
        return await self.ws_client.send(target, content)

    async def receive_message(self, handler: Callable[[dict], Awaitable[None]]):
        self._handler = handler
        async def listen():
            while True:
                msg = await self.ws_client.recv()
                await handler(msg)
        asyncio.create_task(listen())

    async def start(self):
        await self.ws_client.connect()

# gRPC适配器
class GRPCCommAdapter(AgentCommInterface):
    def __init__(self, grpc_client):
        self.grpc_client = grpc_client
        self._handler = None

    async def send_message(self, target: str, content: dict) -> Any:
        return await self.grpc_client.send(target, content)

    async def receive_message(self, handler: Callable[[dict], Awaitable[None]]):
        self._handler = handler
        async for msg in self.grpc_client.recv_stream():
            await handler(msg)

    async def start(self):
        await self.grpc_client.connect() 