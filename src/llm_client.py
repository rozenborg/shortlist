import abc

class BaseLLMClient(abc.ABC):
    @abc.abstractmethod
    def chat(self, prompt: str, **kwargs) -> str:
        pass 