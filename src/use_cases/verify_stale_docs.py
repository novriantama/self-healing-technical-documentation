import os
from typing import Dict, List, Tuple

# pyrefly: ignore [missing-import]
from src.domain.models import CodeChunk, VerificationResult

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.doc_parser import DocParserGateway

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.git_provider import GitProviderGateway

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.llm import LlmGateway


class VerifyStaleDocsUseCase:
    def __init__(
        self,
        git_provider: GitProviderGateway,
        doc_parser: DocParserGateway,
        llm_client: LlmGateway,
    ):
        self._git_provider = git_provider
        self._doc_parser = doc_parser
        self._llm_client = llm_client

    def execute(
        self, suspects: Dict[str, List[CodeChunk]], diff_text: str, workspace_dir: str
    ) -> Dict[str, List[Tuple[CodeChunk, VerificationResult]]]:
        """
        Loads documentation content for suspects headings, reconstructs the pre-image
        version of code chunks from diff text, calls verify_accuracy, and returns
        verified stale documentation sections.
        """
        # 1. Parse all doc sections from files to get content
        doc_sections = {}
        for dirpath, _, filenames in os.walk(workspace_dir):
            if any(part in dirpath.split(os.sep) for part in [".venv", "venv", ".git", ".pytest_cache"]):
                continue
            for fname in filenames:
                if fname.endswith(".md") and "README" not in fname:
                    filepath = os.path.join(dirpath, fname)
                    for sec in self._doc_parser.parse_file(filepath):
                        doc_sections[sec.heading_path] = sec

        # 2. Verify suspects
        verified_stale = {}
        for heading_path, chunks in suspects.items():
            if heading_path not in doc_sections:
                continue
            doc = doc_sections[heading_path]

            for chunk in chunks:
                filepath_relative = chunk.id.split("::")[0]
                chunk_diff = self._git_provider.get_chunk_diff(
                    diff_text, filepath_relative, chunk.start_line, chunk.end_line
                )

                # Reconstruct old chunk signature
                old_sig = chunk.signature
                for line in chunk_diff.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("- def ") or stripped.startswith("- class "):
                        old_sig = stripped[1:].strip()
                        break

                old_chunk = CodeChunk(
                    id=chunk.id,
                    name=chunk.name,
                    type=chunk.type,
                    signature=old_sig,
                    docstring=chunk.docstring,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                )

                # Ask LLM if it's stale
                res = self._llm_client.verify_accuracy(old_chunk, chunk, doc)
                if res.is_stale:
                    if heading_path not in verified_stale:
                        verified_stale[heading_path] = []
                    verified_stale[heading_path].append((chunk, res))

        return verified_stale
