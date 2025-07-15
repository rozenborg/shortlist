import os
from .openai_adapter import OpenAIAdapter
try:
    from .jpm_adapter import JPMAdapter  # your internal file
except ImportError:
    JPMAdapter = None

def get_llm_client():
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "jpm" and JPMAdapter is not None:
        return JPMAdapter()
    return OpenAIAdapter() 