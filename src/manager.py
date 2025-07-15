from .llm_client import BaseLLMClient

class LLMService:
    def __init__(self, client: BaseLLMClient):
        self.client = client

    def chat(self, prompt: str) -> str:
        return self.client.chat(prompt) 