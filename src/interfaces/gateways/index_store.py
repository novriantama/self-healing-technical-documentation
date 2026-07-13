from abc import ABC, abstractmethod
from typing import Dict, List

class IndexStoreGateway(ABC):
    @abstractmethod
    def save(self, graph: Dict[str, List[str]], filepath: str) -> None:
        """Persists the code-to-docs graph to a file path."""
        pass

    @abstractmethod
    def load(self, filepath: str) -> Dict[str, List[str]]:
        """Loads the code-to-docs graph from a file path."""
        pass
