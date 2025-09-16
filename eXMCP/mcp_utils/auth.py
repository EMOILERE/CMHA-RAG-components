class APIKeyAuth:
    def __init__(self, valid_keys):
        self.valid_keys = set(valid_keys)

    def verify(self, api_key: str) -> bool:
        return api_key in self.valid_keys

    @staticmethod
    def from_env(env_var='AGENT_API_KEYS'):
        import os
        keys = os.getenv(env_var, '').split(',')
        return APIKeyAuth([k.strip() for k in keys if k.strip()]) 