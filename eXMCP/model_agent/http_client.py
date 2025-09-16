import httpx
import os

class ModelAgentHTTPClient:
    def __init__(self, central_url: str, agent_id: str, agent_type: str, meta: dict = None):
        self.central_url = central_url.rstrip('/')
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.meta = meta or {}
        self.client = httpx.Client()

    def register(self):
        resp = self.client.post(f"{self.central_url}/register", json={
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "meta": self.meta
        })
        resp.raise_for_status()
        return resp.json()

    def unregister(self):
        resp = self.client.post(f"{self.central_url}/unregister", json={
            "agent_id": self.agent_id
        })
        resp.raise_for_status()
        return resp.json()

    def list_agents(self):
        resp = self.client.get(f"{self.central_url}/agents")
        resp.raise_for_status()
        return resp.json()

    def send_task_result(self, task_id: str, result: dict):
        # 可扩展：向中心agent汇报任务结果
        resp = self.client.post(f"{self.central_url}/task_result", json={
            "agent_id": self.agent_id,
            "task_id": task_id,
            "result": result
        })
        resp.raise_for_status()
        return resp.json()

    def next_task(self):
        resp = self.client.post(f"{self.central_url}/next_task", json={
            "agent_id": self.agent_id
        })
        resp.raise_for_status()
        return resp.json()

    def heartbeat(self, cpu: float, processes: int):
        resp = self.client.post(f"{self.central_url}/heartbeat", json={
            "agent_id": self.agent_id,
            "cpu": cpu,
            "processes": processes
        })
        resp.raise_for_status()
        return resp.json() 