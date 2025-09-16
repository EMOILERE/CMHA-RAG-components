# Google Gemini等模型适配层（占位）
class GeminiBackend:
    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
        # TODO: 初始化Gemini SDK

    def chat(self, messages):
        # TODO: 调用Gemini API
        return "[GeminiBackend] Not implemented yet." 