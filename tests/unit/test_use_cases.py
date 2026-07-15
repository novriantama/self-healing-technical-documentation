# pyrefly: ignore [missing-import]
import os
import tempfile
from typing import List

# pyrefly: ignore [missing-import]
from src.domain.models import CodeChunk, DocSection, VerificationResult

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.code_parser import CodeParserGateway

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.doc_parser import DocParserGateway

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.git_provider import GitProviderGateway

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.llm import LlmGateway

# pyrefly: ignore [missing-import]
from src.use_cases.get_changed_code_chunks import GetChangedCodeChunksUseCase

# pyrefly: ignore [missing-import]
from src.use_cases.index_codebase import IndexCodebaseUseCase


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
                id="src/math.py::unused_function",
                name="unused_function",
                type="function",
                signature="def unused_function()",
                docstring="Not referenced.",
                start_line=6,
                end_line=10,
            ),
        ]


class MockDocParser(DocParserGateway):
    def parse_file(self, filepath: str) -> List[DocSection]:
        return [
            DocSection(
                heading_path="Finance > Tax Calculation",
                content="Explain how to compute tax using the system.",
                references=["calculate_tax"],
            ),
            DocSection(
                heading_path="Finance > Semantic Section",
                content="This is closely related to tax computations.",
                references=[],
            ),
        ]


class MockLlmClient(LlmGateway):
    def verify_accuracy(self, old_code: CodeChunk, new_code: CodeChunk, doc: DocSection) -> VerificationResult:
        return VerificationResult(is_stale=False, confidence=1.0, explanation="")

    def generate_correction(self, doc: DocSection, new_code: CodeChunk, reason: str) -> str:
        return doc.content

    def check_semantic_link(self, code: CodeChunk, doc: DocSection) -> bool:
        return "tax" in code.name.lower() and "tax" in doc.content.lower()

    def is_change_meaningful(self, chunk_name: str, diff_text: str) -> bool:
        # Meaningful if there is at least one non-comment, non-whitespace change
        lines = [line.strip() for line in diff_text.splitlines() if line.startswith("+") or line.startswith("-")]
        if not lines:
            return False
        only_comments_or_whitespace = all(line[1:].strip().startswith("#") or not line[1:].strip() for line in lines)
        return not only_comments_or_whitespace

    def validate_correction(self, patch, new_code) -> VerificationResult:
        return VerificationResult(is_stale=False, confidence=1.0, explanation="")


class MockGitProvider(GitProviderGateway):
    def get_modified_lines(self, diff_text: str) -> dict:
        if diff_text == "test_file_diff":
            return {"tests/test_math.py": {3, 4}}
        return {"src/math.py": {3, 4}}

    def create_pull_request(
        self, repo_name: str, branch_name: str, file_path: str, updated_content: str, pr_title: str, pr_body: str
    ) -> str:
        return "http://localhost/mock-pr-url"

    def get_chunk_diff(self, diff_text: str, filepath: str, start_line: int, end_line: int) -> str:
        if diff_text == "comment_only":
            return "+ # This is a comment\n- # Old comment"
        if diff_text == "whitespace_only":
            return "+ \n-    "
        return "+ return price * 0.1\n- return price * 0.05"


def test_index_codebase_linking():
    use_case = IndexCodebaseUseCase(
        code_parser=MockCodeParser(), doc_parser=MockDocParser(), llm_client=MockLlmClient()
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "math.py"), "w") as f:
            f.write("# dummy")
        with open(os.path.join(tmpdir, "docs.md"), "w") as f:
            f.write("# dummy")

        links = use_case.execute(tmpdir)

        assert "src/math.py::calculate_tax" in links
        assert "src/math.py::unused_function" not in links

        tax_links = links["src/math.py::calculate_tax"]
        assert len(tax_links) == 2
        assert "Finance > Tax Calculation" in tax_links
        assert "Finance > Semantic Section" in tax_links


def test_get_changed_code_chunks():
    git_provider = MockGitProvider()
    code_parser = MockCodeParser()
    llm_client = MockLlmClient()
    use_case = GetChangedCodeChunksUseCase(git_provider, code_parser, llm_client)

    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "src"), exist_ok=True)
        with open(os.path.join(tmpdir, "src/math.py"), "w") as f:
            f.write("# dummy code")

        changed = use_case.execute("meaningful_diff", tmpdir)

        assert len(changed) == 1
        assert changed[0].name == "calculate_tax"
        assert changed[0].id == "src/math.py::calculate_tax"


def test_get_changed_code_chunks_filters_comments_and_whitespace():
    git_provider = MockGitProvider()
    code_parser = MockCodeParser()
    llm_client = MockLlmClient()
    use_case = GetChangedCodeChunksUseCase(git_provider, code_parser, llm_client)

    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "src"), exist_ok=True)
        with open(os.path.join(tmpdir, "src/math.py"), "w") as f:
            f.write("# dummy code")

        # Comment-only diff
        changed_comments = use_case.execute("comment_only", tmpdir)
        assert len(changed_comments) == 0

        # Whitespace-only diff
        changed_whitespace = use_case.execute("whitespace_only", tmpdir)
        assert len(changed_whitespace) == 0


def test_get_changed_code_chunks_filters_test_files():
    git_provider = MockGitProvider()
    code_parser = MockCodeParser()
    llm_client = MockLlmClient()
    use_case = GetChangedCodeChunksUseCase(git_provider, code_parser, llm_client)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test file
        test_file_dir = os.path.join(tmpdir, "tests")
        os.makedirs(test_file_dir, exist_ok=True)
        with open(os.path.join(test_file_dir, "test_math.py"), "w") as f:
            f.write("# dummy test code")

        changed = use_case.execute("test_file_diff", tmpdir)
        # Should skip test file changes entirely
        assert len(changed) == 0
