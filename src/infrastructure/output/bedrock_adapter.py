import time
from typing import Tuple, List
from src.application.ports.output.llm_port import LlmPort
from src.application.ports.output.embedding_port import EmbeddingPort
from bedrock_client import BedrockClient

class BedrockAdapter(LlmPort, EmbeddingPort):
    def __init__(self, bedrock_client: BedrockClient):
        self.bedrock_client = bedrock_client

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return self.bedrock_client.generate(prompt, system_prompt)

    def get_embedding(self, text: str) -> Tuple[List[float], float]:
        t0 = time.perf_counter()
        vector = self.bedrock_client.get_embedding(text)
        t1 = time.perf_counter()
        return vector, (t1 - t0) * 1000
