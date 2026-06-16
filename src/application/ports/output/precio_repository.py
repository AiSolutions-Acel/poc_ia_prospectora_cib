from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.models.precio import Precio

class PrecioRepository(ABC):
    @abstractmethod
    def get_all(self) -> List[Precio]:
        pass

    @abstractmethod
    def get_by_id(self, precio_id: int) -> Optional[Precio]:
        pass
