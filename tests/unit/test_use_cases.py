# pyrefly: ignore [missing-import]
import pytest
from typing import List
# pyrefly: ignore [missing-import]
from src.domain.models import CodeChunk, DocSection, VerificationResult
# pyrefly: ignore [missing-import]
from src.interfaces.gateways.code_parser import CodeParserGateway
# pyrefly: ignore [missing-import]
from src.interfaces.gateways.doc_parser import DocParserGateway
# pyrefly: ignore [missing-import]
from src.interfaces.gateways.llm import LlmGateway
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
                end_line=5
            ),
            CodeChunk(
                id="src/math.py::unused_function",
                name="unused_function",
                type="function",
                signature="def unused_function()",
                docstring="Not referenced.",
                start_line=6,
                end_line=10
            )
        ]

class MockDocParser(DocParserGateway):
    def parse_file(self, filepath: str) -> List[DocSection]:
        return [
            DocSection(
                heading_path="Finance > Tax Calculation",
                content="Explain how to compute tax using the system.",
                references=["calculate_tax"]
            ),
            DocSection(
                heading_path="Finance > Semantic Section",
                content="This is closely related to tax computations.",
                references=[]
            )
        ]

class MockLlmClient(LlmGateway):
    def verify_accuracy(
        self, old_code: CodeChunk, new_code: CodeChunk, doc: DocSection
    ) -> VerificationResult:
        return VerificationResult(is_stale=False, confidence=1.0, explanation="")

    def generate_correction(
        self, doc: DocSection, new_code: CodeChunk, reason: str
    ) -> str:
        return doc.content

    def check_semantic_link(self, code: CodeChunk, doc: DocSection) -> bool:
        # Mock semantic linking: link if both talk about "tax"
        return "tax" in code.name.lower() and "tax" in doc.content.lower()

def test_index_codebase_linking():
    use_case = IndexCodebaseUseCase(
        code_parser=MockCodeParser(),
        doc_parser=MockDocParser(),
        llm_client=MockLlmClient()
    )
    
    import tempfile
    import os
    
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
