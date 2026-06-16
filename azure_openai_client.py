from typing import List
from openai import AzureOpenAI
from src.providers.config import get_settings

settings = get_settings()

class AzureOpenAiClient:
    def __init__(self):
        self.client = AzureOpenAI(
            api_version=settings.azure_api_version,
            azure_endpoint=settings.azure_endpoint,
            api_key=settings.azure_api_key,
        )

    def get_embedding(self, text: str) -> List[float]:
        response = self.client.embeddings.create(
            input=text,
            model=settings.azure_embedding_deployment,
        )
        return response.data[0].embedding

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=settings.azure_llm_deployment,
            messages=messages,
            max_completion_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
        )
        return response.choices[0].message.content
