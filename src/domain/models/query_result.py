from dataclasses import dataclass, field
from typing import List
from src.domain.models.latency_metrics import LatencyMetrics

@dataclass
class QueryResult:
    answer: str
    metrics: LatencyMetrics
    documents_retrieved: int
    retries: int
    logs: List[str] = field(default_factory=list)
