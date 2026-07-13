import json
import os
from typing import Dict, List

# pyrefly: ignore [missing-import]
from src.domain.exceptions import ParserError

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.index_store import IndexStoreGateway


class JsonIndexStore(IndexStoreGateway):
    def save(self, graph: Dict[str, List[str]], filepath: str) -> None:
        try:
            dir_path = os.path.dirname(filepath)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(graph, f, indent=2, sort_keys=True)
        except Exception as e:
            raise ParserError(f"Failed to save index graph to {filepath}: {e}") from e

    def load(self, filepath: str) -> Dict[str, List[str]]:
        if not os.path.exists(filepath):
            return {}
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise ParserError(f"Failed to load index graph from {filepath}: {e}") from e
