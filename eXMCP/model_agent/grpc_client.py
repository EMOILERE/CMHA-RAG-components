import grpc
import asyncio
import proto.agent_comm_pb2 as pb2
import proto.agent_comm_pb2_grpc as pb2_grpc

class GRPCClient:
    def __init__(self, endpoint, api_key):
        self.endpoint = endpoint
        self.api_key = api_key
        self.channel = grpc.aio.insecure_channel(endpoint)
        self.stub = pb2_grpc.AgentCommStub(self.channel)
        self.agent_id = None
        self._heartbeat_task = None
        self._running = False

    async def connect(self):
        self._running = True
        # 可扩展为注册/心跳等
        pass

    async def register(self, agent_id, agent_type, meta=""):
        self.agent_id = agent_id
        req = pb2.RegisterRequest(agent_id=agent_id, agent_type=agent_type, api_key=self.api_key, meta=meta)
        return await self.stub.RegisterAgent(req)

    async def unregister(self):
        # 可扩展为注销接口（如有）
        self._running = False
        await self.channel.close()

    async def heartbeat(self, cpu, processes):
        req = pb2.HeartbeatRequest(agent_id=self.agent_id, cpu=cpu, processes=processes, api_key=self.api_key)
        return await self.stub.Heartbeat(req)

    async def heartbeat_loop(self, interval=5):
        while self._running:
            import psutil
            cpu = psutil.cpu_percent()
            processes = len(psutil.pids())
            try:
                await self.heartbeat(cpu, processes)
            except Exception as e:
                print(f"[GRPCClient] Heartbeat failed: {e}")
            await asyncio.sleep(interval)

    async def send(self, target, content, priority=0):
        req = pb2.MessageRequest(sender=self.agent_id, target=target, content=content, priority=priority, api_key=self.api_key)
        return await self.stub.SendMessage(req)

    async def recv_stream(self):
        # 拉取任务流式接口
        req = pb2.NextTaskRequest(agent_id=self.agent_id, api_key=self.api_key)
        async for task in self.stub.NextTask(req):
            yield task

    async def send_task_result(self, task_id, result):
        req = pb2.TaskResultRequest(agent_id=self.agent_id, task_id=task_id, result=result, api_key=self.api_key)
        return await self.stub.TaskResult(req) 