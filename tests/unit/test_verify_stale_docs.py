# pyrefly: ignore [missing-import]
import os
import tempfile
from typing import List

# pyrefly: ignore [missing-import]
from src.domain.models import CodeChunk, DocSection

# pyrefly: ignore [missing-import]
from src.infrastructure.llm.anthropic_client import AnthropicLlmClient

# pyrefly: ignore [missing-import]
# pyrefly: ignore [missing-import]
from src.interfaces.gateways.doc_parser import DocParserGateway

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.git_provider import GitProviderGateway

# pyrefly: ignore [missing-import]
# pyrefly: ignore [missing-import]
from src.use_cases.verify_stale_docs import VerifyStaleDocsUseCase


class MockDocParser(DocParserGateway):
    def parse_file(self, filepath: str) -> List[DocSection]:
        return [
            DocSection(
                heading_path="Finance > Tax Calculation",
                content="Explain how to compute tax using the system.",
                references=["calculate_tax"],
            )
        ]


class MockGitProvider(GitProviderGateway):
    def get_modified_lines(self, diff_text: str) -> dict:
        return {"math.py": {3}}

    def create_pull_request(self, *args, **kwargs) -> str:
        return "mock"

    def get_chunk_diff(self, diff_text: str, filepath: str, start_line: int, end_line: int) -> str:
        if diff_text == "stale_diff":
            return "- def calculate_tax(old_price: float)\n+ def calculate_tax(new_price: float)"
        return "- return price * 0.1\n+ return price * 0.15"

    def add_pr_comment(self, repo_name: str, pr_number: int, comment: str) -> None:
        pass


def test_verify_stale_docs_use_case():
    git_provider = MockGitProvider()
    doc_parser = MockDocParser()
    llm_client = AnthropicLlmClient(api_key="mock")

    use_case = VerifyStaleDocsUseCase(git_provider, doc_parser, llm_client)

    # 1. calculate_tax has modified logic (signature remains identical) -> Not stale (false positive filter)
    chunk_non_stale = CodeChunk(
        id="math.py::calculate_tax",
        name="calculate_tax",
        type="function",
        signature="def calculate_tax(price: float)",
        docstring="",
        start_line=1,
        end_line=5,
    )
    suspects_non_stale = {"Finance > Tax Calculation": [chunk_non_stale]}

    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "docs.md"), "w") as f:
            f.write("# dummy")

        verified_non_stale = use_case.execute(suspects_non_stale, "non_stale_diff", tmpdir)
        assert len(verified_non_stale) == 0

    # 2. calculate_tax has modified signature -> verified stale
    chunk_stale = CodeChunk(
        id="math.py::calculate_tax",
        name="calculate_tax",
        type="function",
        signature="def calculate_tax(new_price: float)",
        docstring="",
        start_line=1,
        end_line=5,
    )
    suspects_stale = {"Finance > Tax Calculation": [chunk_stale]}

    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "docs.md"), "w") as f:
            f.write("# dummy")

        verified_stale = use_case.execute(suspects_stale, "stale_diff", tmpdir)
        assert len(verified_stale) == 1
        assert "Finance > Tax Calculation" in verified_stale

        chunk_res_list = verified_stale["Finance > Tax Calculation"]
        assert len(chunk_res_list) == 1
        assert chunk_res_list[0][0].name == "calculate_tax"
        assert chunk_res_list[0][1].is_stale is True
        assert "Signature changed" in chunk_res_list[0][1].explanation
