import uuid
import time
import threading
from typing import Dict, Any, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from mcp_utils.registry import AgentRegistry
from mcp_utils.auth import APIKeyAuth
from mcp_utils.priority_queue import PriorityTaskQueue

app = FastAPI()
registry = AgentRegistry()

# 任务状态管理
class TaskStatus:
    PENDING = 'pending'
    RUNNING = 'running'
    FINISHED = 'finished'
    FAILED = 'failed'
    CANCELLED = 'cancelled'

# 任务队列和状态
agent_task_queues: Dict[str, List[dict]] = {}
tasks: Dict[str, dict] = {}
agent_status: Dict[str, dict] = {}
ws_connections: Dict[str, WebSocket] = {}  # agent_id -> WebSocket

# agent任务队列改为优先级队列
tagents_priority_queues: Dict[str, PriorityTaskQueue] = {}

TASK_TIMEOUT = 60
TASK_MAX_RETRIES = 3

auth = APIKeyAuth.from_env()

class RegisterMsg(BaseModel):
    type: str  # 'register'
    agent_id: str
    agent_type: str
    meta: Dict[str, Any] = {}
    cpu: float = 0.0
    processes: int = 0
    api_key: str = ''

class TaskMsg(BaseModel):
    type: str  # 'task'
    task: Dict[str, Any]

class TaskResultMsg(BaseModel):
    type: str  # 'task_result'
    task_id: str
    result: Any
    error: str = None

class HeartbeatMsg(BaseModel):
    type: str  # 'heartbeat'
    agent_id: str
    cpu: float
    processes: int
    api_key: str = ''

@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    agent_id = None
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get('type')
            api_key = data.get('api_key', '')
            if not auth.verify(api_key):
                await websocket.send_json({'type': 'error', 'error': 'Invalid API Key'})
                break
            if msg_type == 'register':
                reg = RegisterMsg(**data)
                agent_id = reg.agent_id
                registry.register(reg.agent_id, reg.agent_type, reg.meta)
                agent_status[reg.agent_id] = {
                    'cpu': reg.cpu,
                    'processes': reg.processes,
                    'last_heartbeat': time.time()
                }
                ws_connections[reg.agent_id] = websocket
                await websocket.send_json({'type': 'register_ack', 'status': 'registered'})
            elif msg_type == 'heartbeat':
                hb = HeartbeatMsg(**data)
                agent_status[hb.agent_id] = {
                    'cpu': hb.cpu,
                    'processes': hb.processes,
                    'last_heartbeat': time.time()
                }
                await websocket.send_json({'type': 'heartbeat_ack'})
            elif msg_type == 'task_result':
                # 校验API Key
                if not auth.verify(api_key):
                    await websocket.send_json({'type': 'error', 'error': 'Invalid API Key'})
                    break
                tr = TaskResultMsg(**data)
                t = tasks.get(tr.task_id)
                if t:
                    t['result'] = tr.result
                    t['status'] = TaskStatus.FINISHED if not tr.error else TaskStatus.FAILED
                    t['error'] = tr.error
                await websocket.send_json({'type': 'task_result_ack', 'task_id': tr.task_id})
            elif msg_type == 'next_task':
                # 校验API Key
                if not auth.verify(api_key):
                    await websocket.send_json({'type': 'error', 'error': 'Invalid API Key'})
                    break
                queue = tagents_priority_queues.setdefault(agent_id, PriorityTaskQueue())
                while not queue.empty():
                    task = queue.get()
                    task_id = task.get('task_id')
                    if task_id and task_id in tasks:
                        if tasks[task_id].get('cancelled', False):
                            tasks[task_id]['status'] = TaskStatus.CANCELLED
                            continue
                        tasks[task_id]['status'] = TaskStatus.RUNNING
                        tasks[task_id]['started_at'] = time.time()
                    await websocket.send_json({'type': 'task', 'task': task})
                    break
                else:
                    await websocket.send_json({'type': 'task', 'task': None})
            elif msg_type == 'unregister':
                if agent_id:
                    registry.unregister(agent_id)
                    agent_status.pop(agent_id, None)
                    ws_connections.pop(agent_id, None)
                    await websocket.send_json({'type': 'unregister_ack', 'status': 'unregistered'})
                    break
    except WebSocketDisconnect:
        if agent_id:
            registry.unregister(agent_id)
            agent_status.pop(agent_id, None)
            ws_connections.pop(agent_id, None)

@app.post('/ws_task')
def ws_assign_task(agent_id: str, task: Dict[str, Any]):
    # 任务分发API，需API Key校验
    from fastapi import Request
    import os
    api_key = os.getenv('API_KEY') or ''
    if not auth.verify(api_key):
        from fastapi import status
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"error": "Invalid API Key"})
    priority = task.get('priority', 0)
    task_id = str(uuid.uuid4())
    task['task_id'] = task_id
    queue = tagents_priority_queues.setdefault(agent_id, PriorityTaskQueue())
    queue.put(task, priority=priority)
    tasks[task_id] = {
        'task': task,
        'status': TaskStatus.PENDING,
        'result': None,
        'agent_id': agent_id,
        'error': None,
        'retries': 0,
        'created_at': time.time(),
        'cancelled': False,
        'priority': priority
    }
    return {'task_id': task_id, 'status': TaskStatus.PENDING}

# 任务超时与重试监控线程同HTTP实现

def task_timeout_monitor():
    while True:
        now = time.time()
        for task_id, t in list(tasks.items()):
            if t['status'] == TaskStatus.RUNNING and not t.get('cancelled', False):
                if now - t.get('started_at', now) > TASK_TIMEOUT:
                    if t.get('retries', 0) < TASK_MAX_RETRIES:
                        t['status'] = TaskStatus.PENDING
                        t['retries'] = t.get('retries', 0) + 1
                        agent_id = t['agent_id']
                        agent_task_queues.setdefault(agent_id, []).append(t['task'])
                    else:
                        t['status'] = TaskStatus.FAILED
                        t['error'] = 'Timeout and max retries reached'
        time.sleep(5)

threading.Thread(target=task_timeout_monitor, daemon=True).start() 