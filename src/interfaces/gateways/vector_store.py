from abc import ABC, abstractmethod
from typing import List
from src.domain.models import DocSection

class VectorStoreGateway(ABC):
    @abstractmethod
    def index_sections(self, sections: List[DocSection]) -> None:
        """Stores documentation sections along with their embeddings."""
        pass

    @abstractmethod
    def search_similar_sections(self, code_query: str, limit: int = 3) -> List[DocSection]:
        """Queries vector database to find semantically matching doc sections."""
        pass
