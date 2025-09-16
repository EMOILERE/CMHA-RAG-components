import asyncio
import json
import websockets
import psutil
import uuid

class ModelAgentWSClient:
    def __init__(self, ws_url, agent_id, agent_type, model_name, meta=None):
        self.ws_url = ws_url
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.model_name = model_name
        self.meta = meta or {}
        self.ws = None
        self.heartbeat_interval = 5
        self.running = True

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url)
        await self.register()
        asyncio.create_task(self.heartbeat_loop())

    async def register(self):
        cpu = psutil.cpu_percent()
        processes = len(psutil.pids())
        msg = {
            'type': 'register',
            'agent_id': self.agent_id,
            'agent_type': self.agent_type,
            'meta': self.meta,
            'cpu': cpu,
            'processes': processes
        }
        await self.ws.send(json.dumps(msg))
        ack = await self.ws.recv()
        return json.loads(ack)

    async def heartbeat_loop(self):
        while self.running:
            cpu = psutil.cpu_percent()
            processes = len(psutil.pids())
            msg = {
                'type': 'heartbeat',
                'agent_id': self.agent_id,
                'cpu': cpu,
                'processes': processes
            }
            try:
                await self.ws.send(json.dumps(msg))
                await asyncio.wait_for(self.ws.recv(), timeout=2)
            except Exception:
                pass
            await asyncio.sleep(self.heartbeat_interval)

    async def next_task(self):
        await self.ws.send(json.dumps({'type': 'next_task'}))
        resp = await self.ws.recv()
        data = json.loads(resp)
        if data.get('type') == 'task':
            return data.get('task')
        return None

    async def send_task_result(self, task_id, result, error=None):
        msg = {
            'type': 'task_result',
            'task_id': task_id,
            'result': result,
            'error': error
        }
        await self.ws.send(json.dumps(msg))
        ack = await self.ws.recv()
        return json.loads(ack)

    async def unregister(self):
        await self.ws.send(json.dumps({'type': 'unregister'}))
        ack = await self.ws.recv()
        self.running = False
        await self.ws.close()
        return json.loads(ack) 