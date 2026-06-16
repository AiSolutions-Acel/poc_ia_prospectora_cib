from typing import List, Optional
from src.domain.models.precio import Precio
from src.application.ports.output.precio_repository import PrecioRepository
from mock_db import MockPrecioDb

class MockPrecioAdapter(PrecioRepository):
    def __init__(self, db: MockPrecioDb):
        self.db = db

    def get_all(self) -> List[Precio]:
        return self.db.get_all()

    def get_by_id(self, precio_id: int) -> Optional[Precio]:
        return self.db.get_by_id(precio_id)
