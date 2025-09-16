# Anthropic Claude等模型适配层（占位）
class AnthropicBackend:
    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
        # TODO: 初始化Anthropic SDK

    def chat(self, messages):
        # TODO: 调用Anthropic API
        return "[AnthropicBackend] Not implemented yet." 