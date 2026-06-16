from dataclasses import dataclass

@dataclass
class LatencyMetrics:
    embedding_latency_ms: float
    search_latency_ms: float
    llm_latency_ms: float
    e2e_latency_ms: float
