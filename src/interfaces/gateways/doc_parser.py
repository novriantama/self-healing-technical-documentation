from abc import ABC, abstractmethod
from typing import List
from src.domain.models import DocSection

class DocParserGateway(ABC):
    @abstractmethod
    def parse_file(self, filepath: str) -> List[DocSection]:
        """Parses a markdown document and extracts sections by heading path."""
        pass
