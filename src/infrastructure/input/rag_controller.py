from fastapi import APIRouter, Depends
from src.application.dto.query_dto import QueryRequestDto, QueryResponseDto
from src.application.dto.chat_dto import ChatRequestDto, ChatResponseDto
from src.application.services.query_rag_bedrock import QueryRagBedrockUseCase
from src.application.services.query_rag_azure import QueryRagAzureUseCase
from src.application.services.chat_use_case import ChatUseCase

router = APIRouter(tags=["RAG"])

def get_bedrock_use_case():
    from main import query_rag_bedrock_use_case
    return query_rag_bedrock_use_case

def get_azure_use_case():
    from main import query_rag_azure_use_case
    return query_rag_azure_use_case

def get_chat_use_case():
    from main import chat_use_case
    return chat_use_case

@router.post("/query", response_model=QueryResponseDto, tags=["RAG — Bedrock"])
async def query_rag_bedrock(
    request: QueryRequestDto,
    use_case: QueryRagBedrockUseCase = Depends(get_bedrock_use_case)
):
    """
    RAG agéntico con AWS Bedrock (Titan V2 + Claude 4.5 Haiku) + S3 Vectors.
    """
    return use_case.execute(request)

@router.post("/query-azure", response_model=QueryResponseDto, tags=["RAG — Azure OpenAI"])
async def query_rag_azure(
    request: QueryRequestDto,
    use_case: QueryRagAzureUseCase = Depends(get_azure_use_case)
):
    """
    RAG agéntico con Azure OpenAI (text-embedding-3-small + GPT-5.1) + S3 Vectors.
    """
    return use_case.execute(request)

@router.post("/chat", response_model=ChatResponseDto, tags=["Agente Comercial"])
async def chat_asesor_comercial(
    request: ChatRequestDto,
    use_case: ChatUseCase = Depends(get_chat_use_case)
):
    """
    Endpoint conversacional. El Asesor Comercial mantiene contexto por session_id,
    y decide dinámicamente si usar RAG o consultar precios.
    """
    return use_case.execute(request)
