# pyrefly: ignore [missing-import]
import os
import tempfile
from typing import List

# pyrefly: ignore [missing-import]
from src.domain.models import CodeChunk, DocSection, VerificationResult

# pyrefly: ignore [missing-import]
from src.infrastructure.llm.anthropic_client import AnthropicLlmClient

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.doc_parser import DocParserGateway

# pyrefly: ignore [missing-import]
from src.use_cases.generate_corrections import GenerateCorrectionsUseCase


class MockDocParser(DocParserGateway):
    def parse_file(self, filepath: str) -> List[DocSection]:
        return [
            DocSection(
                heading_path="Finance > Tax Calculation",
                content="Explain how to compute tax using the system.",
                references=["calculate_tax"],
            )
        ]


def test_generate_corrections_use_case_auto_fix():
    doc_parser = MockDocParser()
    llm_client = AnthropicLlmClient(api_key="mock")

    use_case = GenerateCorrectionsUseCase(doc_parser, llm_client)

    chunk = CodeChunk(
        id="math.py::calculate_tax",
        name="calculate_tax",
        type="function",
        signature="def calculate_tax(new_price: float)",
        docstring="",
        start_line=1,
        end_line=5,
    )
    res = VerificationResult(is_stale=True, confidence=0.95, explanation="Signature changed.")
    verified_stale = {"Finance > Tax Calculation": [(chunk, res)]}

    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "docs.md"), "w") as f:
            f.write("# dummy")

        patches = use_case.execute(verified_stale, tmpdir)

        assert len(patches) == 1
        patch = patches[0]
        assert patch.heading_path == "Finance > Tax Calculation"
        assert patch.original_content == "Explain how to compute tax using the system."
        assert "compute tax with new signature using" in patch.repaired_content
        assert patch.confidence == 0.95
        assert patch.mode == "auto_fix"
        assert "TODO: HUMAN REVIEW REQUIRED" not in patch.repaired_content


def test_generate_corrections_use_case_draft():
    doc_parser = MockDocParser()
    llm_client = AnthropicLlmClient(api_key="mock")

    use_case = GenerateCorrectionsUseCase(doc_parser, llm_client, confidence_threshold=0.8)

    chunk = CodeChunk(
        id="math.py::calculate_tax",
        name="calculate_tax",
        type="function",
        signature="def calculate_tax(new_price: float)",
        docstring="",
        start_line=1,
        end_line=5,
    )
    res = VerificationResult(is_stale=True, confidence=0.5, explanation="Stale logic.")
    verified_stale = {"Finance > Tax Calculation": [(chunk, res)]}

    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "docs.md"), "w") as f:
            f.write("# dummy")

        patches = use_case.execute(verified_stale, tmpdir)

        assert len(patches) == 1
        patch = patches[0]
        assert patch.confidence == 0.5
        assert patch.mode == "draft"
        assert "TODO: HUMAN REVIEW REQUIRED" in patch.repaired_content
