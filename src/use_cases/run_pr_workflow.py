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
        suspects: Dict[str, List[CodeChunk]],
        valid_patches: List[DocPatch],
        verified_stale: Dict[str, List[Tuple[CodeChunk, VerificationResult]]],
        repo_name: str,
        pr_number: int,
    ) -> List[str]:
        """
        Runs the PR workflow:
        1. High-confidence fixes: creates branches and opens PRs.
        2. Posts a consolidated summary comment on the original PR.
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

        # 3. Post consolidated summary comment on the original PR
        if pr_number > 0:
            # Verified accurate are suspects that were not found verified stale
            num_accurate = len(suspects) - len(verified_stale)
            if num_accurate < 0:
                num_accurate = 0

            # Formulate the auto-fixed link indicators e.g., (see PR #42)
            auto_fixed_details = []
            for url in pr_urls:
                pr_id = url.split("/")[-1]
                auto_fixed_details.append(f"(see PR #{pr_id})")
            auto_fixed_str = " ".join(auto_fixed_details)
            if auto_fixed_str:
                auto_fixed_str = f" {auto_fixed_str}"

            # Build list of opened pull requests markdown section
            auto_fixed_links_lines = []
            for url in pr_urls:
                auto_fixed_links_lines.append(f"- [PR #{url.split('/')[-1]}]({url})")
            auto_fixed_links = "\n".join(auto_fixed_links_lines) if auto_fixed_links_lines else "None"

            # Build list of flagged sections markdown section
            flagged_links_lines = []
            for patch in drafts:
                explanation = "Documentation references outdated codebase elements."
                for heading, issues in verified_stale.items():
                    if heading == patch.heading_path:
                        if issues:
                            explanation = issues[0][1].explanation
                        break
                doc_link = f"https://github.com/{repo_name}/blob/main/{patch.filepath}"
                flagged_links_lines.append(
                    f"- **{patch.heading_path}** ([link]({doc_link}))\n  *Reason*: {explanation}"
                )
            flagged_links = "\n".join(flagged_links_lines) if flagged_links_lines else "None"

            # Consolidate comment body
            comment_body = (
                "### 📝 Self-Healing Docs: Check Results\n\n"
                f"**Doc Check Results**: {num_accurate} sections verified accurate, {len(auto_fixes)} auto-fixed{auto_fixed_str}, {len(drafts)} flagged for review.\n\n"
                "---\n\n"
                "#### 🔧 Auto-fixed Pull Requests:\n"
                f"{auto_fixed_links}\n\n"
                "#### ⚠️ Flagged for Manual Review:\n"
                f"{flagged_links}"
            )

            self._git_provider.add_pr_comment(repo_name=repo_name, pr_number=pr_number, comment=comment_body)

        return pr_urls
