import openai

class OpenAIBackend:
    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
        openai.api_key = api_key

    def chat(self, messages):
        response = openai.ChatCompletion.create(
            model=self.model_name,
            messages=messages
        )
        return response['choices'][0]['message']['content'] 