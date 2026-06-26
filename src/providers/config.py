import os
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache

class Settings(BaseSettings):
    """Configuración centralizada vía variables de entorno."""

    # AWS General
    aws_access_key_id: str = os.environ.get("AWS_ACCESS_KEY_ID", "")
    aws_secret_access_key: str = os.environ.get("AWS_SECRET_ACCESS_KEY", "")

    # AWS Bedrock (Embeddings + LLM)
    bedrock_region: str = "us-east-1"
    embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    llm_model_id: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    llm_max_tokens: int = 1000
    llm_temperature: float = 0.0

    # S3 Vectors (Bedrock/Pinecone)
    s3vectors_region: str = "us-east-2"
    s3vectors_bucket_name: str = "poc-ia-prospecter"
    s3vectors_index_name: str = "index-data-test"

    # Azure OpenAI
    azure_endpoint: str = "https://lau-prospectora-resource.cognitiveservices.azure.com/"
    azure_api_key: str = Field(default="", alias="AZURE_OPENAI_API_KEY")
    azure_api_version: str = "2024-12-01-preview"
    azure_embedding_deployment: str = "text-embedding-3-small-prospectora"
    azure_llm_deployment: str = "gpt-5.1-prospectora"

    # S3 Vectors (Azure OpenAI bucket)
    s3vectors_azure_bucket_name: str = "poc-chat-prospect-cib"
    s3vectors_azure_index_name: str = "chat-cib-poc"
    
    # S3 Vectors Multi-Índice
    s3vectors_idx_institucional: str = Field(default="idx-institucional", alias="S3VECTORS_IDX_INSTITUCIONAL")
    s3vectors_idx_argumentario: str = Field(default="idx-argumentario", alias="S3VECTORS_IDX_ARGUMENTARIO")
    s3vectors_idx_oferta_academica: str = Field(default="idx-oferta-academica", alias="S3VECTORS_IDX_OFERTA_ACADEMICA")
    s3vectors_idx_convenios: str = Field(default="idx-convenios", alias="S3VECTORS_IDX_CONVENIOS")

    # RAG
    retrieval_top_k: int = 5
    max_retries: int = 2

    # WhatsApp (Meta Cloud API)
    whatsapp_verify_token: str = os.environ.get("WHATSAPP_VERIFY_TOKEN", "cibertec-verify-token-2026")
    whatsapp_access_token: str = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
    whatsapp_phone_number_id: str = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")

    # Sub Agentes API
    api_prices_url: str = os.environ.get("API_PRICES_URL", "http://localhost:8001/api/v1/precios")

    class Config:
        env_file = ".env"
        extra = "allow"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
