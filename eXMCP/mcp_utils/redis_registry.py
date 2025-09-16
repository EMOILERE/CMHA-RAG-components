import redis
import json
import time

class RedisRegistry:
    def __init__(self, redis_url='redis://localhost:6379/0'):
        self.r = redis.Redis.from_url(redis_url, decode_responses=True)

    def register_agent(self, agent_id, meta):
        self.r.hset('agents', agent_id, json.dumps(meta))
        self.r.hset('agent_heartbeat', agent_id, time.time())

    def heartbeat(self, agent_id):
        self.r.hset('agent_heartbeat', agent_id, time.time())

    def unregister_agent(self, agent_id):
        self.r.hdel('agents', agent_id)
        self.r.hdel('agent_heartbeat', agent_id)

    def get_all_agents(self):
        return {k: json.loads(v) for k, v in self.r.hgetall('agents').items()}

    def get_agent_heartbeats(self):
        return {k: float(v) for k, v in self.r.hgetall('agent_heartbeat').items()} 