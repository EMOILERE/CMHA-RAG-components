# MCP协议适配层（修正版，基于ClientSession）
from mcp import ClientSession, CreateMessageRequest, CreateMessageResult
import asyncio

class MCPProtocol:
    def __init__(self, read_stream, write_stream, api_key=None):
        self.read_stream = read_stream
        self.write_stream = write_stream
        self.session = None
        self._msg_handler = None
        self.api_key = api_key

    async def start(self):
        async with ClientSession(self.read_stream, self.write_stream) as session:
            self.session = session
            await session.initialize()
            # 消息监听主循环
            while True:
                msg = await self.session.read_message()
                if self._msg_handler:
                    await self._msg_handler(msg)

    async def send_message(self, content: dict):
        if not self.session:
            raise RuntimeError("MCP session not initialized")
        # 自动附加api_key
        if self.api_key:
            content = dict(content)
            content['api_key'] = self.api_key
        req = CreateMessageRequest(**content)
        result: CreateMessageResult = await self.session.create_message(req)
        return result

    def receive_message(self, handler):
        # handler: async function(msg: Message)
        self._msg_handler = handler 