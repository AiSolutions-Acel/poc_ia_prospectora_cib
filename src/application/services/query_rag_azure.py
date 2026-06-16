import time
from typing import Any
from src.application.ports.input.query_rag_use_case import QueryRagUseCase
from src.application.dto.query_dto import QueryRequestDto, QueryResponseDto, LatencyMetricsDto

class QueryRagAzureUseCase(QueryRagUseCase):
    def __init__(self, rag_app: Any):
        self.rag_app = rag_app

    def execute(self, request: QueryRequestDto) -> QueryResponseDto:
        t_start = time.perf_counter()

        initial_state = {
            "question": request.question,
            "query": request.question,
            "documents": [],
            "generation": "",
            "retries": 0,
            "logs": [],
            "embedding_latency_ms": 0.0,
            "search_latency_ms": 0.0,
            "llm_latency_ms": 0.0,
            "query_vector": [],
        }

        output = self.rag_app.invoke(initial_state)

        t_end = time.perf_counter()
        e2e_latency = (t_end - t_start) * 1000

        metrics = LatencyMetricsDto(
            embedding_latency_ms=round(output.get("embedding_latency_ms", 0.0), 2),
            search_latency_ms=round(output.get("search_latency_ms", 0.0), 2),
            llm_latency_ms=round(output.get("llm_latency_ms", 0.0), 2),
            e2e_latency_ms=round(e2e_latency, 2),
        )

        return QueryResponseDto(
            answer=output.get("generation", ""),
            metrics=metrics,
            documents_retrieved=len(output.get("documents", [])),
            retries=output.get("retries", 0),
            logs=output.get("logs", []),
        )
