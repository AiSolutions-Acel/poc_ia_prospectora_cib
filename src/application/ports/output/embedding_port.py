from abc import ABC, abstractmethod
from typing import Tuple, List

class EmbeddingPort(ABC):
    @abstractmethod
    def get_embedding(self, text: str) -> Tuple[List[float], float]:
        """Returns the vector embedding and the latency in ms."""
        pass
