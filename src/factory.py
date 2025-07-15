import os
from .openai_adapter import OpenAIAdapter
try:
    from .custom_adapter import CustomAdapter  # user's custom adapter file
except ImportError:
    CustomAdapter = None

def get_llm_client():
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "custom" and CustomAdapter is not None:
        return CustomAdapter()
    return OpenAIAdapter() 