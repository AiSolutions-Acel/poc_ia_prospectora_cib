from abc import ABC, abstractmethod
from typing import Tuple, List, Dict, Any

class VectorStorePort(ABC):
    @abstractmethod
    def retrieve(self, vector: List[float], top_k: int = 5, index_name: str = None) -> Tuple[List[Dict[str, Any]], float]:
        """Returns retrieved documents and the latency in ms."""
        pass
