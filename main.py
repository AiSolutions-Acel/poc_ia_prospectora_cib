from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.providers.config import get_settings
from bedrock_client import BedrockClient
from azure_openai_client import AzureOpenAiClient
from s3_client import S3VectorsClient
from mock_db import MockPrecioDb
from src.infrastructure.output.bedrock_adapter import BedrockAdapter
from src.infrastructure.output.azure_adapter import AzureAdapter
from src.infrastructure.output.s3_vector_adapter import S3VectorAdapter
from src.infrastructure.output.mock_precio_adapter import MockPrecioAdapter
from bedrock_rag_orchestrator import BedrockRagOrchestrator
from azure_rag_orchestrator import AzureRagOrchestrator
from src.application.services.query_rag_bedrock import QueryRagBedrockUseCase
from src.application.services.query_rag_azure import QueryRagAzureUseCase
from src.application.services.get_precios import GetPreciosUseCase
from src.application.services.supervisor_agent import SupervisorAgentOrchestrator
from src.application.services.chat_use_case import ChatUseCase

# ──────────────────────────────────────────────
# Dependency Injection / Wiring
# ──────────────────────────────────────────────
settings = get_settings()

# Clients
s3_client = S3VectorsClient()
bedrock_client = BedrockClient()
azure_client = AzureOpenAiClient()
mock_db = MockPrecioDb()

# Adapters
bedrock_adapter = BedrockAdapter(bedrock_client)
azure_adapter = AzureAdapter(azure_client)
s3_vector_adapter_bedrock = S3VectorAdapter(s3_client, settings.s3vectors_bucket_name, settings.s3vectors_index_name)
s3_vector_adapter_azure = S3VectorAdapter(s3_client, settings.s3vectors_azure_bucket_name, settings.s3vectors_azure_index_name)
mock_precio_adapter = MockPrecioAdapter(mock_db)

# Orchestrators
bedrock_orchestrator = BedrockRagOrchestrator(bedrock_adapter, bedrock_adapter, s3_vector_adapter_bedrock)
azure_orchestrator = AzureRagOrchestrator(azure_adapter, azure_adapter, s3_vector_adapter_azure)
supervisor_orchestrator = SupervisorAgentOrchestrator(azure_adapter, s3_vector_adapter_azure, mock_db)

# Global variables for Use Cases
query_rag_bedrock_use_case = None
query_rag_azure_use_case = None
chat_use_case = None
get_precios_use_case = GetPreciosUseCase(mock_precio_adapter)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global query_rag_bedrock_use_case, query_rag_azure_use_case, chat_use_case
    
    # Compile graphs
    rag_app_bedrock = bedrock_orchestrator.build()
    print("✅ RAG Agent Bedrock (LangGraph) compilado.")
    
    rag_app_azure = azure_orchestrator.build()
    print("✅ RAG Agent Azure OpenAI (LangGraph) compilado.")

    supervisor_agent = supervisor_orchestrator.build()
    print("✅ Supervisor Agent (LangGraph + Tools) compilado.")
    
    query_rag_bedrock_use_case = QueryRagBedrockUseCase(rag_app_bedrock)
    query_rag_azure_use_case = QueryRagAzureUseCase(rag_app_azure)
    chat_use_case = ChatUseCase(supervisor_agent)
    
    yield
    print("🛑 Shutting down...")

# ──────────────────────────────────────────────
# FastAPI App
# ──────────────────────────────────────────────
app = FastAPI(
    title="RAG API — Cibertec Prospecto",
    description=(
        "API REST con pipelines RAG Agénticos (Self-RAG) usando LangGraph y Arquitectura Limpia.\n\n"
        "- **POST /query** — Bedrock (Titan V2 + Claude Haiku) + S3 Vectors\n"
        "- **POST /query-azure** — Azure OpenAI (text-embedding-3-small + GPT-5.1) + S3 Vectors"
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# ──────────────────────────────────────────────
# Routers
# ──────────────────────────────────────────────
from src.infrastructure.input.health_controller import router as health_router
from src.infrastructure.input.rag_controller import router as rag_router
from src.infrastructure.input.precio_controller import router as precio_router
from src.infrastructure.input.whatsapp_controller import router as whatsapp_router

app.include_router(health_router)
app.include_router(rag_router)
app.include_router(precio_router)
app.include_router(whatsapp_router)
