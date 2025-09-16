import uuid
import time
import threading
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from mcp_utils.registry import AgentRegistry
from mcp_utils.auth import APIKeyAuth
from mcp_utils.priority_queue import PriorityTaskQueue
from mcp_utils.redis_registry import RedisRegistry
from mcp_utils.notify import notify_webhook

# -------------------- 配置与全局变量 --------------------

app = FastAPI()
REDIS_URL = 'redis://localhost:6379/0'
WEBHOOK_URL = 'http://your-webhook-server/agent-removed'

registry = RedisRegistry(REDIS_URL)

# 任务状态管理
class TaskStatus:
    PENDING = 'pending'
    RUNNING = 'running'
    FINISHED = 'finished'
    FAILED = 'failed'
    CANCELLED = 'cancelled'

# 任务队列和状态
agent_task_queues: Dict[str, List[dict]] = {}
tasks: Dict[str, dict] = {}  # task_id -> {task, status, result, agent_id, error, ...}
agent_status: Dict[str, dict] = {}  # agent_id -> {cpu, processes, last_heartbeat, ...}

# 任务重试、超时、取消参数
TASK_TIMEOUT = 60  # 秒
TASK_MAX_RETRIES = 3
AGENT_TIMEOUT = 30  # 秒

# -------------------- 数据模型 --------------------

class RegisterRequest(BaseModel):
    agent_id: str
    agent_type: str
    meta: Dict[str, Any] = {}
    cpu: float = 0.0
    processes: int = 0

class UnregisterRequest(BaseModel):
    agent_id: str

class HeartbeatRequest(BaseModel):
    agent_id: str
    cpu: float
    processes: int

class TaskRequest(BaseModel):
    agent_id: str
    task: Dict[str, Any]

class BatchTaskRequest(BaseModel):
    agent_id: str
    tasks: list

class CancelTaskRequest(BaseModel):
    task_id: str

class NextTaskRequest(BaseModel):
    agent_id: str

class AssignTaskResponse(BaseModel):
    task_id: str
    status: str

# -------------------- Agent 注册与心跳 --------------------

@app.post('/register')
def register_agent(req: RegisterRequest):
    registry.register(req.agent_id, req.agent_type, req.meta)
    agent_status[req.agent_id] = {
        'cpu': req.cpu,
        'processes': req.processes,
        'last_heartbeat': time.time()
    }
    return {"status": "registered", "agent_id": req.agent_id}

@app.post('/unregister')
def unregister_agent(req: UnregisterRequest):
    registry.unregister(req.agent_id)
    agent_status.pop(req.agent_id, None)
    return {"status": "unregistered", "agent_id": req.agent_id}

@app.post('/heartbeat')
def heartbeat(req: HeartbeatRequest):
    agent_status[req.agent_id] = {
        'cpu': req.cpu,
        'processes': req.processes,
        'last_heartbeat': time.time()
    }
    return {"status": "heartbeat_received"}

@app.get('/agents')
def list_agents():
    return {"agents": registry.get_all_agents(), "status": agent_status}

@app.get('/agent_status')
def get_agent_status():
    # 查询所有agent状态和心跳时间（从Redis）
    heartbeats = registry.get_agent_heartbeats()
    agents = registry.get_all_agents()
    now = time.time()
    return {
        agent_id: {
            **agents.get(agent_id, {}),
            'last_heartbeat': heartbeats.get(agent_id, 0),
            'online': (now - heartbeats.get(agent_id, 0) <= AGENT_TIMEOUT)
        }
        for agent_id in agents.keys()
    }

# -------------------- 任务分发与管理 --------------------

# 初始化API Key认证（从环境变量AGENT_API_KEYS加载）
auth = APIKeyAuth.from_env()

# agent任务队列改为优先级队列
tagents_priority_queues = {}  # agent_id -> PriorityTaskQueue

@app.post('/task')
def assign_task(req: TaskRequest):
    # API Key认证
    import os
    api_key = os.getenv('API_KEY') or ''
    if not auth.verify(api_key):
        from fastapi import status
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"error": "Invalid API Key"})
    # 任务优先级
    priority = req.task.get('priority', 0)
    task_id = str(uuid.uuid4())
    task = req.task.copy()
    task['task_id'] = task_id
    queue = agents_priority_queues.setdefault(req.agent_id, PriorityTaskQueue())
    queue.put(task, priority=priority)
    tasks[task_id] = {
        'task': task,
        'status': TaskStatus.PENDING,
        'result': None,
        'agent_id': req.agent_id,
        'error': None,
        'retries': 0,
        'created_at': time.time(),
        'cancelled': False,
        'priority': priority
    }
    return AssignTaskResponse(task_id=task_id, status=TaskStatus.PENDING)

@app.post('/batch_task')
def batch_task(req: BatchTaskRequest):
    # API Key认证
    import os
    api_key = os.getenv('API_KEY') or ''
    if not auth.verify(api_key):
        from fastapi import status
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"error": "Invalid API Key"})
    task_ids = []
    for t in req.tasks:
        priority = t.get('priority', 0)
        task_id = str(uuid.uuid4())
        t['task_id'] = task_id
        queue = agents_priority_queues.setdefault(req.agent_id, PriorityTaskQueue())
        queue.put(t, priority=priority)
        tasks[task_id] = {
            'task': t,
            'status': TaskStatus.PENDING,
            'result': None,
            'agent_id': req.agent_id,
            'error': None,
            'retries': 0,
            'created_at': time.time(),
            'cancelled': False,
            'priority': priority
        }
        task_ids.append(task_id)
    return {"task_ids": task_ids, "status": TaskStatus.PENDING}

@app.post('/cancel_task')
def cancel_task(req: CancelTaskRequest):
    # API Key认证
    import os
    api_key = os.getenv('API_KEY') or ''
    if not auth.verify(api_key):
        from fastapi import status
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"error": "Invalid API Key"})
    task_id = req.task_id
    if task_id in tasks:
        tasks[task_id]['cancelled'] = True
        tasks[task_id]['status'] = TaskStatus.CANCELLED
        return {"status": "cancelled", "task_id": task_id}
    return JSONResponse(status_code=404, content={"error": "Task not found"})

@app.get('/task_status/{task_id}')
def get_task_status(task_id: str):
    """查询任务状态和结果。"""
    if task_id not in tasks:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    t = tasks[task_id]
    return {
        "task_id": task_id,
        "status": t['status'],
        "result": t['result'],
        "agent_id": t['agent_id'],
        "error": t['error'],
        "retries": t.get('retries', 0),
        "created_at": t.get('created_at'),
        "cancelled": t.get('cancelled', False)
    }

@app.post('/next_task')
def next_task(req: NextTaskRequest):
    queue = agents_priority_queues.setdefault(req.agent_id, PriorityTaskQueue())
    while not queue.empty():
        task = queue.get()
        task_id = task.get('task_id')
        if task_id and task_id in tasks:
            if tasks[task_id].get('cancelled', False):
                tasks[task_id]['status'] = TaskStatus.CANCELLED
                continue  # 跳过已取消任务
            tasks[task_id]['status'] = TaskStatus.RUNNING
            tasks[task_id]['started_at'] = time.time()
        return {"task": task}
    return {"task": None}

@app.post('/task_result')
def task_result(result: Dict[str, Any]):
    """agent提交任务结果。"""
    task_id = result.get('task_id')
    if not task_id or task_id not in tasks:
        return JSONResponse(status_code=400, content={"error": "Invalid task_id"})
    try:
        tasks[task_id]['result'] = result.get('result')
        tasks[task_id]['status'] = TaskStatus.FINISHED
        tasks[task_id]['error'] = None
        return {"status": "result_received", **result}
    except Exception as e:
        tasks[task_id]['status'] = TaskStatus.FAILED
        tasks[task_id]['error'] = str(e)
        return JSONResponse(status_code=500, content={"error": str(e)})

# -------------------- 任务超时与重试监控 --------------------

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

# -------------------- 动态任务分配（示例） --------------------
def select_agent_for_task():
    """选择CPU占用最低且进程数最少的agent。"""
    if not agent_status:
        return None
    sorted_agents = sorted(agent_status.items(), key=lambda x: (x[1]['cpu'], x[1]['processes']))
    return sorted_agents[0][0] if sorted_agents else None 

def agent_status_monitor():
    while True:
        now = time.time()
        heartbeats = registry.get_agent_heartbeats()
        to_remove = []
        for agent_id, last_heartbeat in heartbeats.items():
            if now - last_heartbeat > AGENT_TIMEOUT:
                print(f"[CentralAgent] Agent {agent_id} 超时未心跳，自动剔除")
                notify_webhook(WEBHOOK_URL, agent_id, "timeout")
                to_remove.append(agent_id)
        for agent_id in to_remove:
            registry.unregister_agent(agent_id)
        time.sleep(5)

import threading
threading.Thread(target=agent_status_monitor, daemon=True).start() 

@app.post('/mcp_notify')
def mcp_notify(payload: Dict[str, Any]):
    method = payload.get('method')
    params = payload.get('params', {})
    agent_id = params.get('agent_id')
    if method == 'agent/register':
        registry.register_agent(agent_id, params)
        print(f"[MCP] Agent {agent_id} 注册: {params}")
        return {"status": "registered"}
    elif method == 'agent/unregister':
        registry.unregister_agent(agent_id)
        print(f"[MCP] Agent {agent_id} 注销")
        return {"status": "unregistered"}
    elif method == 'agent/heartbeat':
        registry.heartbeat(agent_id)
        print(f"[MCP] Agent {agent_id} 心跳: cpu={params.get('cpu')}, processes={params.get('processes')}")
        return {"status": "heartbeat_received"}
    else:
        return {"status": "ignored", "reason": "unknown method"} 