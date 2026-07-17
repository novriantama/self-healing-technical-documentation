from typing import Dict, List

# pyrefly: ignore [missing-import]
from src.domain.models import CodeChunk

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.index_store import IndexStoreGateway

# pyrefly: ignore [missing-import]
from src.use_cases.get_changed_code_chunks import GetChangedCodeChunksUseCase


class IdentifyStaleDocsUseCase:
    def __init__(
        self,
        get_changed_chunks_use_case: GetChangedCodeChunksUseCase,
        index_store: IndexStoreGateway,
    ):
        self._get_changed_chunks_use_case = get_changed_chunks_use_case
        self._index_store = index_store

    def execute(self, diff_text: str, workspace_dir: str, index_path: str) -> Dict[str, List[CodeChunk]]:
        """
        Identifies stale doc sections by finding code chunks affected by the diff,
        then looking up which doc sections are linked to those chunks in the index.

        Returns a dictionary mapping:
        doc_section_heading_path -> List[CodeChunk that affects it]
        """
        # 1. Get meaningful changed code chunks
        changed_chunks = self._get_changed_chunks_use_case.execute(diff_text, workspace_dir)
        print(f"DEBUG: changed_chunks = {[c.id for c in changed_chunks]}")

        # 2. Load codebase-to-docs link graph
        graph = self._index_store.load(index_path)
        print(f"DEBUG: loaded index graph keys = {list(graph.keys())}")

        # 3. Identify affected doc sections (suspects)
        suspects: Dict[str, List[CodeChunk]] = {}
        for chunk in changed_chunks:
            if chunk.id in graph:
                for heading_path in graph[chunk.id]:
                    if heading_path not in suspects:
                        suspects[heading_path] = []
                    suspects[heading_path].append(chunk)
            else:
                print(f"DEBUG: Chunk ID {chunk.id} NOT found in graph keys.")

        return suspects
