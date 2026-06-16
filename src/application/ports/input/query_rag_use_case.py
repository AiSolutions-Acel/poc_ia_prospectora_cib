from abc import ABC, abstractmethod
from src.application.dto.query_dto import QueryRequestDto, QueryResponseDto

class QueryRagUseCase(ABC):
    @abstractmethod
    def execute(self, request: QueryRequestDto) -> QueryResponseDto:
        pass
