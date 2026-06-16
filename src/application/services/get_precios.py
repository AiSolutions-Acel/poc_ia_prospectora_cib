from typing import List, Optional
from src.domain.models.precio import Precio
from src.application.ports.output.precio_repository import PrecioRepository

class GetPreciosUseCase:
    def __init__(self, precio_repository: PrecioRepository):
        self.precio_repository = precio_repository

    def get_all(self) -> List[Precio]:
        return self.precio_repository.get_all()

    def get_by_id(self, precio_id: int) -> Optional[Precio]:
        return self.precio_repository.get_by_id(precio_id)
