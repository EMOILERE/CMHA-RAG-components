import grpc
from concurrent import futures
import proto.agent_comm_pb2 as pb2
import proto.agent_comm_pb2_grpc as pb2_grpc
from mcp_utils.auth import APIKeyAuth
from mcp_utils.priority_queue import PriorityTaskQueue
from mcp_utils.registry import AgentRegistry
import threading
import time

# 全局注册表和任务队列
registry = AgentRegistry()
tasks = {}  # task_id -> task dict
agents_priority_queues = {}  # agent_id -> PriorityTaskQueue

auth = APIKeyAuth.from_env()

class AgentCommServicer(pb2_grpc.AgentCommServicer):
    def SendMessage(self, request, context):
        api_key = getattr(request, 'api_key', '')
        if not auth.verify(api_key):
            context.abort(grpc.StatusCode.UNAUTHENTICATED, 'Invalid API Key')
        # 任务分发：将消息作为任务入队
        agent_id = request.target
        priority = getattr(request, 'priority', 0) if hasattr(request, 'priority') else 0
        task_id = str(int(time.time() * 1000))
        task = {
            'task_id': task_id,
            'from': request.sender,
            'to': agent_id,
            'content': request.content,
            'priority': priority,
            'status': 'pending',
        }
        queue = agents_priority_queues.setdefault(agent_id, PriorityTaskQueue())
        queue.put(task, priority=priority)
        tasks[task_id] = task
        return pb2.MessageReply(content=f"任务已入队: {task_id}", status="ok")

    def StreamMessages(self, request_iterator, context):
        for req in request_iterator:
            api_key = getattr(req, 'api_key', '')
            if not auth.verify(api_key):
                context.abort(grpc.StatusCode.UNAUTHENTICATED, 'Invalid API Key')
            agent_id = req.target
            priority = getattr(req, 'priority', 0) if hasattr(req, 'priority') else 0
            task_id = str(int(time.time() * 1000))
            task = {
                'task_id': task_id,
                'from': req.sender,
                'to': agent_id,
                'content': req.content,
                'priority': priority,
                'status': 'pending',
            }
            queue = agents_priority_queues.setdefault(agent_id, PriorityTaskQueue())
            queue.put(task, priority=priority)
            tasks[task_id] = task
            yield pb2.MessageReply(content=f"流式任务已入队: {task_id}", status="ok")

def serve(host='0.0.0.0', port=50051):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_AgentCommServicer_to_server(AgentCommServicer(), server)
    server.add_insecure_port(f'{host}:{port}')
    print(f"[CentralAgent] gRPC server running at {host}:{port}")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve() 