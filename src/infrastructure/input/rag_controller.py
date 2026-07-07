import re

from fastapi import APIRouter, Depends
from src.application.dto.query_dto import QueryRequestDto, QueryResponseDto
from src.application.dto.chat_dto import ChatRequestDto, ChatResponseDto
from src.application.services.query_rag_bedrock import QueryRagBedrockUseCase
from src.application.services.query_rag_azure import QueryRagAzureUseCase
from src.application.services.chat_use_case import ChatUseCase

router = APIRouter(tags=["RAG"])

# Textos de reemplazo para las etiquetas internas del agente.
# Mantenerlos aquí garantiza que cualquier integración (Chattigo, API REST, etc.)
# reciba siempre texto plano legible, igual que el canal de WhatsApp.
_TAG_REPLACEMENTS = {
    "[REQUEST_TERMS]": (
        "¡Hola! 👋 Soy tu asesor virtual de Cibertec y estoy aquí para ayudarte con toda la información "
        "sobre tu carrera de interés, resolver tus dudas y acompañarte en tu camino hacia tus metas profesionales. 🚀\n"
        "Para continuar, por favor acepta nuestros términos y condiciones aquí 👉 "
        "https://www.cibertec.edu.pe/escuela-cibertec/transparencia/\n"
        "Responde *Sí, acepto* o *No acepto* para continuar."
    ),
    "[REQUEST_PERSONAL_DATA]": (
        "¡Perfecto! 🙌 Gracias por aceptar los términos.\n"
        "Para ayudarte mejor, por favor envíanos los siguientes datos en tu próximo mensaje:\n"
        "- DNI\n- Nombres\n- Apellidos"
    ),
    "[REQUEST_ALUMNO_STATUS]": (
        "¡Gracias por tus datos! Una última pregunta antes de continuar: "
        "¿Eres alumno o ex alumno de Cibertec?\n"
        "Responde *Soy alumno/exalumno* o *No, soy nuevo*."
    ),
}


def _resolve_agent_tags(answer: str) -> str:
    """
    Reemplaza las etiquetas internas del agente por su texto plano equivalente.
    También limpia la etiqueta [BOTONES:...] dejando solo el texto previo,
    y elimina [FORMULARIO_INGRESO] sustituyéndola por un texto de acción.
    """
    for tag, text in _TAG_REPLACEMENTS.items():
        if tag in answer:
            return text

    # Limpiar etiqueta de botones dinámicos: dejar solo el texto del mensaje
    answer = re.sub(r"\[BOTONES:.*?\]", "", answer).strip()

    # Limpiar etiqueta de formulario
    answer = answer.replace("[FORMULARIO_INGRESO]", "Por favor completa el formulario de ingreso.").strip()

    return answer


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
    """RAG agéntico con AWS Bedrock (Titan V2 + Claude 4.5 Haiku) + S3 Vectors."""
    return use_case.execute(request)

@router.post("/query-azure", response_model=QueryResponseDto, tags=["RAG — Azure OpenAI"])
async def query_rag_azure(
    request: QueryRequestDto,
    use_case: QueryRagAzureUseCase = Depends(get_azure_use_case)
):
    """RAG agéntico con Azure OpenAI (text-embedding-3-small + GPT-5.1) + S3 Vectors."""
    return use_case.execute(request)

@router.post("/chat", response_model=ChatResponseDto, tags=["Agente Comercial"])
async def chat_asesor_comercial(
    request: ChatRequestDto,
    use_case: ChatUseCase = Depends(get_chat_use_case)
):
    """
    Endpoint conversacional para integraciones externas (Chattigo, etc.).
    Mantiene contexto por session_id y devuelve siempre texto plano sin etiquetas internas.
    """
    response = use_case.execute(request)
    response.answer = _resolve_agent_tags(response.answer)
    return response
