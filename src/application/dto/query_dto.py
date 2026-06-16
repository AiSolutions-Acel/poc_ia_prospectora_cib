from pydantic import BaseModel, Field
from typing import List

class LatencyMetricsDto(BaseModel):
    embedding_latency_ms: float
    search_latency_ms: float
    llm_latency_ms: float
    e2e_latency_ms: float

class QueryRequestDto(BaseModel):
    question: str = Field(..., min_length=3)

class QueryResponseDto(BaseModel):
    answer: str
    metrics: LatencyMetricsDto
    documents_retrieved: int
    retries: int
    logs: List[str] = Field(default_factory=list)
