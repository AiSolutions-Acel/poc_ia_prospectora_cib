from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["System"])

class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "rag-api"
    version: str = "2.0.0"

@router.get("/", response_model=HealthResponse)
async def health_check():
    """Health check del servicio."""
    return HealthResponse()
