from typing import List, Dict, Set
# pyrefly: ignore [missing-import]
from src.interfaces.gateways.index_store import IndexStoreGateway

class QueryAffectedDocsUseCase:
    def __init__(self, index_store: IndexStoreGateway):
        self._index_store = index_store

    def execute(self, changed_chunk_ids: List[str], index_path: str) -> List[str]:
        """
        Loads the mapping index and queries it to find which documentation
        section headings might be affected by the list of changed codebase chunks.
        """
        graph = self._index_store.load(index_path)
        affected: Set[str] = set()
        for chunk_id in changed_chunk_ids:
            if chunk_id in graph:
                affected.update(graph[chunk_id])
        return sorted(list(affected))
