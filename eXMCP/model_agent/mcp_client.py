from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession, CreateMessageRequest, ClientNotification
import asyncio
import psutil

class MCPClient:
    def __init__(self, url, api_key):
        self.url = url
        self.api_key = api_key
        self.agent_id = None
        self.session = None
        self.read_stream = None
        self.write_stream = None
        self.read_stream_ctx = None
        self._running = False

    async def connect(self):
        self.read_stream_ctx = streamablehttp_client(url=self.url)
        self.read_stream, self.write_stream, _ = await self.read_stream_ctx.__aenter__()
        self.session = ClientSession(self.read_stream, self.write_stream)
        await self.session.initialize()
        self._running = True

    async def register(self, agent_id, agent_type, meta=""):
        self.agent_id = agent_id
        # 发送自定义注册通知
        notification = ClientNotification(
            method="agent/register",
            params={
                "agent_id": agent_id,
                "agent_type": agent_type,
                "meta": meta,
                "api_key": self.api_key
            }
        )
        await self.session.send_notification(notification)

    async def unregister(self):
        self._running = False
        # 发送自定义注销通知
        if self.session:
            notification = ClientNotification(
                method="agent/unregister",
                params={"agent_id": self.agent_id, "api_key": self.api_key}
            )
            try:
                await self.session.send_notification(notification)
            except Exception:
                pass
        await self.close()

    async def heartbeat(self, cpu, processes):
        # 发送自定义心跳通知
        if self.session:
            notification = ClientNotification(
                method="agent/heartbeat",
                params={
                    "agent_id": self.agent_id,
                    "cpu": cpu,
                    "processes": processes,
                    "api_key": self.api_key
                }
            )
            await self.session.send_notification(notification)

    async def heartbeat_loop(self, interval=5):
        while self._running:
            cpu = psutil.cpu_percent()
            processes = len(psutil.pids())
            try:
                await self.heartbeat(cpu, processes)
            except Exception as e:
                print(f"[MCPClient] Heartbeat failed: {e}")
            await asyncio.sleep(interval)

    async def send(self, target, content, priority=0):
        req = CreateMessageRequest(role='user', content=content, api_key=self.api_key)
        return await self.session.create_message(req)

    async def recv_stream(self):
        while self._running:
            msg = await self.session.read_message()
            yield msg

    async def pull_and_process_tasks(self, process_func, interval=2):
        """
        自动拉取任务，调用process_func处理，并回传结果。
        process_func: async function(task_content) -> result
        """
        while self._running:
            # 拉取任务（假设中心agent通过MCP create_message分发任务，agent通过read_message获取）
            msg = await self.session.read_message()
            if msg and hasattr(msg, 'content') and msg.content:
                print(f"[MCPClient] 拉取到任务: {msg.content}")
                try:
                    result = await process_func(msg.content)
                    # 回传结果，parent_id为任务ID
                    await self.send_result(msg.message_id, result)
                except Exception as e:
                    print(f"[MCPClient] 任务处理失败: {e}")
            await asyncio.sleep(interval)

    async def send_result(self, parent_id, result):
        """
        回传任务结果到中心agent，parent_id为原任务ID。
        """
        req = CreateMessageRequest(role='agent', content=result, parent_id=parent_id, api_key=self.api_key)
        await self.session.create_message(req)

    async def close(self):
        if self.session:
            await self.session.__aexit__(None, None, None)
        if self.read_stream_ctx:
            await self.read_stream_ctx.__aexit__(None, None, None) 