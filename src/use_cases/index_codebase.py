import os
from typing import Dict, List, Set

# pyrefly: ignore [missing-import]
from src.domain.models import CodeChunk, DocSection

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.code_parser import CodeParserGateway

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.doc_parser import DocParserGateway

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.llm import LlmGateway


class IndexCodebaseUseCase:
    def __init__(self, code_parser: CodeParserGateway, doc_parser: DocParserGateway, llm_client: LlmGateway):
        self._code_parser = code_parser
        self._doc_parser = doc_parser
        self._llm_client = llm_client

    def execute(self, root_dir: str) -> Dict[str, List[str]]:
        # 1. Discover and parse code files (.py)
        code_chunks: List[CodeChunk] = []
        for dirpath, _, filenames in os.walk(root_dir):
            if any(
                part in dirpath.split(os.sep)
                for part in [".venv", "venv", ".git", ".pytest_cache", ".ruff_cache", "build", "dist"]
            ):
                continue
            for fname in filenames:
                if fname.endswith(".py") and not fname.startswith("test_"):
                    filepath = os.path.join(dirpath, fname)
                    code_chunks.extend(self._code_parser.parse_file(filepath))

        # 2. Discover and parse markdown doc files (.md)
        doc_sections: List[DocSection] = []
        for dirpath, _, filenames in os.walk(root_dir):
            if any(part in dirpath.split(os.sep) for part in [".venv", "venv", ".git", ".pytest_cache"]):
                continue
            for fname in filenames:
                if fname.endswith(".md") and "README" not in fname:
                    filepath = os.path.join(dirpath, fname)
                    doc_sections.extend(self._doc_parser.parse_file(filepath))

        # 3. Perform linking
        link_graph: Dict[str, Set[str]] = {chunk.id: set() for chunk in code_chunks}

        for chunk in code_chunks:
            name_parts = chunk.name.split(".")
            name_candidates = {chunk.name} | set(name_parts)

            for sec in doc_sections:
                linked = False

                # A. Heuristic match: check if name candidates intersect with doc section references
                if any(cand in sec.references for cand in name_candidates):
                    link_graph[chunk.id].add(sec.heading_path)
                    linked = True

                # B. Claude Sonnet 4.6 semantic evaluation (fallback)
                if not linked and self._llm_client.check_semantic_link(chunk, sec):
                    link_graph[chunk.id].add(sec.heading_path)

        return {code_id: sorted(paths) for code_id, paths in link_graph.items() if paths}
