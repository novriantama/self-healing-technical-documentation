# pyrefly: ignore [missing-import]
import os
import tempfile
from typing import Dict, Set

# pyrefly: ignore [missing-import]
from src.domain.models import CodeChunk, DocPatch, VerificationResult

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.git_provider import GitProviderGateway

# pyrefly: ignore [missing-import]
from src.use_cases.run_pr_workflow import RunPrWorkflowUseCase


class MockGitProvider(GitProviderGateway):
    def __init__(self):
        self.prs_created = []
        self.comments_added = []

    def get_modified_lines(self, diff_text: str) -> Dict[str, Set[int]]:
        return {}

    def get_chunk_diff(self, diff_text: str, filepath: str, start_line: int, end_line: int) -> str:
        return ""

    def create_pull_request(
        self, repo_name: str, branch_name: str, file_path: str, updated_content: str, pr_title: str, pr_body: str
    ) -> str:
        self.prs_created.append((repo_name, branch_name, file_path, updated_content))
        return f"https://github.com/{repo_name}/pull/999"

    def add_pr_comment(self, repo_name: str, pr_number: int, comment: str) -> None:
        self.comments_added.append((repo_name, pr_number, comment))


def test_run_pr_workflow_use_case():
    git_provider = MockGitProvider()
    use_case = RunPrWorkflowUseCase(git_provider)

    chunk_stale = CodeChunk(
        id="math.py::calculate_tax",
        name="calculate_tax",
        type="function",
        signature="def calculate_tax(new_price: float)",
        docstring="",
        start_line=1,
        end_line=5,
    )
    res_stale = VerificationResult(is_stale=True, confidence=0.95, explanation="Stale signature.")
    verified_stale = {"Finance > Tax Calculation": [(chunk_stale, res_stale)]}

    # 1. High confidence auto-fix patch
    patch_auto = DocPatch(
        filepath="docs.md",
        heading_path="Finance > Tax Calculation",
        original_content="Explain how to compute tax using the system.",
        repaired_content="Explain how to compute tax with new signature using the system.",
        confidence=0.95,
        mode="auto_fix",
    )

    # 2. Low confidence draft patch
    patch_draft = DocPatch(
        filepath="docs.md",
        heading_path="Finance > Billing Details",
        original_content="Explain billing.",
        repaired_content="Explain billing draft.",
        confidence=0.5,
        mode="draft",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create doc file
        doc_filepath = os.path.join(tmpdir, "docs.md")
        with open(doc_filepath, "w") as f:
            f.write("Explain how to compute tax using the system.")

        patch_auto.filepath = doc_filepath
        patch_draft.filepath = doc_filepath

        pr_urls = use_case.execute(
            valid_patches=[patch_auto, patch_draft],
            verified_stale=verified_stale,
            repo_name="owner/repo",
            pr_number=123,
        )

        # High confidence fix should create a PR
        assert len(pr_urls) == 1
        assert pr_urls[0] == "https://github.com/owner/repo/pull/999"
        assert len(git_provider.prs_created) == 1
        assert git_provider.prs_created[0][0] == "owner/repo"
        assert "fix-" in git_provider.prs_created[0][1]
        assert git_provider.prs_created[0][2] == doc_filepath
        assert "Explain how to compute tax using the system." in git_provider.prs_created[0][3]

        # Low confidence draft should post a comment
        assert len(git_provider.comments_added) == 1
        assert git_provider.comments_added[0][0] == "owner/repo"
        assert git_provider.comments_added[0][1] == 123
        assert "⚠️ Self-Healing Docs: Human Review Required" in git_provider.comments_added[0][2]
        assert "Finance > Billing Details" in git_provider.comments_added[0][2]
