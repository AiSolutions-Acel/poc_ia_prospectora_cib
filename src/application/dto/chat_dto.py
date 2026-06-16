from pydantic import BaseModel, Field
from typing import Optional

class ChatRequestDto(BaseModel):
    session_id: str = Field(..., description="ID único para mantener el historial de la conversación")
    message: str = Field(..., min_length=1, description="Mensaje del usuario")

class ChatResponseDto(BaseModel):
    answer: str = Field(..., description="Respuesta del Asesor Comercial")
    session_id: str = Field(..., description="ID de la sesión")
