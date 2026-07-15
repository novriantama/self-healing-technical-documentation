# pyrefly: ignore [missing-import]
import os
import tempfile
from typing import List

# pyrefly: ignore [missing-import]
from src.domain.models import CodeChunk, VerificationResult

# pyrefly: ignore [missing-import]
from src.infrastructure.parsers.json_index_store import JsonIndexStore

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.code_parser import CodeParserGateway

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.git_provider import GitProviderGateway

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.llm import LlmGateway

# pyrefly: ignore [missing-import]
from src.use_cases.get_changed_code_chunks import GetChangedCodeChunksUseCase

# pyrefly: ignore [missing-import]
from src.use_cases.identify_stale_docs import IdentifyStaleDocsUseCase


class MockCodeParser(CodeParserGateway):
    def parse_file(self, filepath: str) -> List[CodeChunk]:
        return [
            CodeChunk(
                id="src/math.py::calculate_tax",
                name="calculate_tax",
                type="function",
                signature="def calculate_tax(price: float)",
                docstring="Computes price tax.",
                start_line=1,
                end_line=5,
            ),
            CodeChunk(
                id="src/math.py::calculate_interest",
                name="calculate_interest",
                type="function",
                signature="def calculate_interest(balance: float)",
                docstring="Computes interest.",
                start_line=6,
                end_line=10,
            ),
        ]


class MockGitProvider(GitProviderGateway):
    def get_modified_lines(self, diff_text: str) -> dict:
        return {"src/math.py": {3, 8}}

    def create_pull_request(self, *args, **kwargs) -> str:
        return "http://localhost/mock-pr-url"

    def get_chunk_diff(self, diff_text: str, filepath: str, start_line: int, end_line: int) -> str:
        if start_line == 1:
            return "+ return price * 0.1"
        return "+ return balance * 0.05"

    def add_pr_comment(self, repo_name: str, pr_number: int, comment: str) -> None:
        pass


class MockLlmClient(LlmGateway):
    def verify_accuracy(self, old_code, new_code, doc) -> VerificationResult:
        return VerificationResult(is_stale=False, confidence=1.0, explanation="")

    def generate_correction(self, doc, new_code, reason) -> str:
        return doc.content

    def check_semantic_link(self, code, doc) -> bool:
        return True

    def is_change_meaningful(self, chunk_name: str, diff_text: str) -> bool:
        return True

    def validate_correction(self, patch, new_code) -> VerificationResult:
        return VerificationResult(is_stale=False, confidence=1.0, explanation="")


def test_identify_stale_docs():
    git_provider = MockGitProvider()
    code_parser = MockCodeParser()
    llm_client = MockLlmClient()
    get_changed_chunks = GetChangedCodeChunksUseCase(git_provider, code_parser, llm_client)
    index_store = JsonIndexStore()

    use_case = IdentifyStaleDocsUseCase(get_changed_chunks, index_store)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create src/math.py
        os.makedirs(os.path.join(tmpdir, "src"), exist_ok=True)
        with open(os.path.join(tmpdir, "src/math.py"), "w") as f:
            f.write("# dummy")

        # Create mock index file
        mock_index_path = os.path.join(tmpdir, "index.json")
        mock_graph = {
            "src/math.py::calculate_tax": ["Finance > Tax Calculation", "Finance > Billing"],
            "src/math.py::calculate_interest": ["Finance > Banking"],
        }
        index_store.save(mock_graph, mock_index_path)

        # Execute stale docs identification
        suspects = use_case.execute("fake diff", tmpdir, mock_index_path)

        # We expect:
        # 1. "Finance > Tax Calculation" affected by calculate_tax
        # 2. "Finance > Billing" affected by calculate_tax
        # 3. "Finance > Banking" affected by calculate_interest

        assert "Finance > Tax Calculation" in suspects
        assert "Finance > Billing" in suspects
        assert "Finance > Banking" in suspects

        assert len(suspects["Finance > Tax Calculation"]) == 1
        assert suspects["Finance > Tax Calculation"][0].name == "calculate_tax"

        assert len(suspects["Finance > Banking"]) == 1
        assert suspects["Finance > Banking"][0].name == "calculate_interest"
