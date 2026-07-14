from typing import Dict, Set

import whatthepatch
from github import Github

# pyrefly: ignore [missing-import]
from src.domain.exceptions import GitError
# pyrefly: ignore [missing-import]
from src.interfaces.gateways.git_provider import GitProviderGateway


class GitHubProvider(GitProviderGateway):
    def __init__(self, token: str):
        self._token = token
        self._github = Github(token) if token else None

    def get_modified_lines(self, diff_text: str) -> Dict[str, Set[int]]:
        try:
            modified_files = {}
            for diff in whatthepatch.parse_patch(diff_text):
                if not diff.header or not diff.changes:
                    continue
                filepath = diff.header.new_path
                modified_lines = set()
                for change in diff.changes:
                    if change.new is not None:
                        modified_lines.add(change.new)
                modified_files[filepath] = modified_lines
            return modified_files
        except Exception as e:
            raise GitError(f"Failed to parse git diff: {e}") from e

    def create_pull_request(
        self, repo_name: str, branch_name: str, file_path: str, updated_content: str, pr_title: str, pr_body: str
    ) -> str:
        if not self._github or self._token == "mock":
            return "http://localhost/mock-pr-url"
        try:
            repo = self._github.get_repo(repo_name)
            main_branch = repo.get_branch("main")
            repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=main_branch.commit.sha)
            contents = repo.get_contents(file_path, ref=branch_name)
            repo.update_file(
                path=contents.path,
                message="docs: update stale documentation",
                content=updated_content,
                sha=contents.sha,
                branch=branch_name,
            )
            pr = repo.create_pull(title=pr_title, body=pr_body, head=branch_name, base="main")
            return pr.html_url
        except Exception as e:
            raise GitError(f"Failed to create pull request via GitHub API: {e}") from e

    def get_chunk_diff(self, diff_text: str, filepath: str, start_line: int, end_line: int) -> str:
        try:
            chunk_changes = []
            for diff in whatthepatch.parse_patch(diff_text):
                if not diff.header or not diff.changes:
                    continue
                if diff.header.new_path != filepath and diff.header.old_path != filepath:
                    continue

                current_new_line = 1
                for change in diff.changes:
                    if change.new is not None:
                        current_new_line = change.new

                    if change.new is not None and start_line <= change.new <= end_line:
                        if change.old is None:
                            chunk_changes.append(f"+ {change.line}")
                        else:
                            chunk_changes.append(f"  {change.line}")
                    elif change.new is None and change.old is not None and start_line <= current_new_line <= end_line:
                        chunk_changes.append(f"- {change.line}")
            return "\n".join(chunk_changes)
        except Exception as e:
            raise GitError(f"Failed to get chunk diff: {e}") from e
