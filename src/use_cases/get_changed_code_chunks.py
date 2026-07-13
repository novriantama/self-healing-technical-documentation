import os
from typing import List

# pyrefly: ignore [missing-import]
from src.domain.models import CodeChunk

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.code_parser import CodeParserGateway

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.git_provider import GitProviderGateway


class GetChangedCodeChunksUseCase:
    def __init__(self, git_provider: GitProviderGateway, code_parser: CodeParserGateway):
        self._git_provider = git_provider
        self._code_parser = code_parser

    def execute(self, diff_text: str, workspace_dir: str) -> List[CodeChunk]:
        """
        Parses a git diff to get modified files and lines, parses the files,
        and identifies which CodeChunks are affected by those modified lines.
        """
        modified_lines_map = self._git_provider.get_modified_lines(diff_text)

        changed_chunks: List[CodeChunk] = []
        for filepath, modified_lines in modified_lines_map.items():
            if not filepath.endswith(".py"):
                continue

            full_path = os.path.join(workspace_dir, filepath)
            if not os.path.exists(full_path):
                continue

            all_chunks = self._code_parser.parse_file(full_path)

            for chunk in all_chunks:
                chunk_range = set(range(chunk.start_line, chunk.end_line + 1))
                if chunk_range.intersection(modified_lines):
                    changed_chunks.append(chunk)

        return changed_chunks
