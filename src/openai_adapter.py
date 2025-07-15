import os
from dotenv import load_dotenv
from openai import OpenAI
from .llm_client import BaseLLMClient

load_dotenv()

class OpenAIAdapter(BaseLLMClient):
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4")

    def chat(self, prompt, **kwargs):
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return resp.choices[0].message.content 