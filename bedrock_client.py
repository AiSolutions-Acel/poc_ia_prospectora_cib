import json
import boto3
from typing import List
from src.providers.config import get_settings

settings = get_settings()

class BedrockClient:
    def __init__(self):
        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=settings.bedrock_region,
        )

    def get_embedding(self, text: str) -> List[float]:
        response = self.client.invoke_model(
            modelId=settings.embedding_model_id,
            body=json.dumps({"inputText": text}),
        )
        return json.loads(response["body"].read())["embedding"]

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": settings.llm_max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": settings.llm_temperature,
        })
        response = self.client.invoke_model(
            modelId=settings.llm_model_id,
            body=body,
        )
        response_body = json.loads(response["body"].read())
        return response_body["content"][0]["text"]
