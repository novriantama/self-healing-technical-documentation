from abc import ABC, abstractmethod
from typing import List
from src.domain.models import CodeChunk

class CodeParserGateway(ABC):
    @abstractmethod
    def parse_file(self, filepath: str) -> List[CodeChunk]:
        """Parses a source code file and extracts code chunks."""
        pass
