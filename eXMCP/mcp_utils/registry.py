# Agent注册与发现机制
from typing import Dict, List
import threading

class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, dict] = {}
        self._lock = threading.Lock()

    def register(self, agent_id: str, agent_type: str, meta: dict):
        with self._lock:
            self._agents[agent_id] = {'type': agent_type, 'meta': meta}

    def unregister(self, agent_id: str):
        with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]

    def get_agents_by_type(self, agent_type: str) -> List[str]:
        with self._lock:
            return [aid for aid, info in self._agents.items() if info['type'] == agent_type]

    def get_all_agents(self) -> Dict[str, dict]:
        with self._lock:
            return dict(self._agents) 