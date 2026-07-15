import hashlib
import os
from typing import Dict, List, Tuple

# pyrefly: ignore [missing-import]
from src.domain.models import CodeChunk, DocPatch, VerificationResult

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.git_provider import GitProviderGateway


class RunPrWorkflowUseCase:
    def __init__(self, git_provider: GitProviderGateway):
        self._git_provider = git_provider

    def execute(
        self,
        valid_patches: List[DocPatch],
        verified_stale: Dict[str, List[Tuple[CodeChunk, VerificationResult]]],
        repo_name: str,
        pr_number: int,
    ) -> List[str]:
        """
        Runs the PR workflow:
        1. High-confidence fixes: creates branches and opens PRs.
        2. Low-confidence flags: adds a review comment to the original PR.
        Returns a list of URLs created (PR URLs).
        """
        pr_urls: List[str] = []

        # 1. Group patches by mode
        auto_fixes = [p for p in valid_patches if p.mode == "auto_fix"]
        drafts = [p for p in valid_patches if p.mode == "draft"]

        # 2. Process high-confidence auto_fixes
        for patch in auto_fixes:
            # Generate unique branch name
            heading_hash = hashlib.md5(patch.heading_path.encode()).hexdigest()[:8]
            branch_name = f"self-healing-docs/fix-{heading_hash}"

            # Since auto_merge has written it to local file, read the whole content
            if os.path.exists(patch.filepath):
                with open(patch.filepath, "r") as f:
                    whole_content = f.read()
            else:
                whole_content = patch.repaired_content

            pr_title = f"docs: auto-repair stale section '{patch.heading_path}'"
            pr_body = (
                f"This pull request was automatically opened by the Self-Healing Documentation tool "
                f"to repair the stale technical documentation section:\n"
                f"- **Heading**: `{patch.heading_path}`\n"
                f"- **File**: `{patch.filepath}`\n\n"
                f"### Change Details\n"
                f"The parameter signatures or method structures were updated in the codebase, "
                f"making the old descriptions outdated. The LLM validated the correction with high confidence."
            )

            pr_url = self._git_provider.create_pull_request(
                repo_name=repo_name,
                branch_name=branch_name,
                file_path=patch.filepath,
                updated_content=whole_content,
                pr_title=pr_title,
                pr_body=pr_body,
            )
            pr_urls.append(pr_url)

        # 3. Process low-confidence drafts
        if drafts and pr_number > 0:
            comment_lines = [
                "### ⚠️ Self-Healing Docs: Human Review Required",
                "",
                "The following documentation sections have been flagged as potentially stale based on recent codebase changes. "
                "The LLM confidence level was low, so please review them manually:",
                "",
            ]
            for patch in drafts:
                # Find matching staleness diagnosis
                explanation = "Documentation references outdated codebase elements."
                for heading, issues in verified_stale.items():
                    if heading == patch.heading_path:
                        if issues:
                            explanation = issues[0][1].explanation
                        break

                doc_link = f"https://github.com/{repo_name}/blob/main/{patch.filepath}"
                comment_lines.append(f"- [ ] **{patch.heading_path}** ([link]({doc_link}))\n  *Reason*: {explanation}")

            comment_body = "\n".join(comment_lines)
            self._git_provider.add_pr_comment(repo_name=repo_name, pr_number=pr_number, comment=comment_body)

        return pr_urls
