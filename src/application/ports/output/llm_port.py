from abc import ABC, abstractmethod

class LlmPort(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        pass
