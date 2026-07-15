from abc import ABC, abstractmethod
from typing import Dict, Set


class GitProviderGateway(ABC):
    @abstractmethod
    def get_modified_lines(self, diff_text: str) -> Dict[str, Set[int]]:
        """Parses git diff into mapped changes of file paths to modified line numbers."""
        pass

    @abstractmethod
    def create_pull_request(
        self, repo_name: str, branch_name: str, file_path: str, updated_content: str, pr_title: str, pr_body: str
    ) -> str:
        """Pushes documentation updates and creates a Pull Request. Returns PR URL."""
        pass

    @abstractmethod
    def get_chunk_diff(self, diff_text: str, filepath: str, start_line: int, end_line: int) -> str:
        """Extracts unified diff edits related to a code chunk boundary range."""
        pass

    @abstractmethod
    def add_pr_comment(self, repo_name: str, pr_number: int, comment: str) -> None:
        """Adds a comment to a Pull Request on GitHub."""
        pass
