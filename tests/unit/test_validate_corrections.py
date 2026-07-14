# pyrefly: ignore [missing-import]
from src.domain.models import CodeChunk, DocPatch

# pyrefly: ignore [missing-import]
from src.infrastructure.llm.anthropic_client import AnthropicLlmClient

# pyrefly: ignore [missing-import]
from src.use_cases.validate_corrections import ValidateCorrectionsUseCase


def test_validate_corrections_use_case():
    llm_client = AnthropicLlmClient(api_key="mock")
    use_case = ValidateCorrectionsUseCase(llm_client)

    chunk = CodeChunk(
        id="math.py::calculate_tax",
        name="calculate_tax",
        type="function",
        signature="def calculate_tax(new_price: float)",
        docstring="",
        start_line=1,
        end_line=5,
    )

    # 1. Valid patch -> should pass quality gate
    patch_valid = DocPatch(
        filepath="docs.md",
        heading_path="Finance > Tax Calculation",
        original_content="Explain how to compute tax using the system.",
        repaired_content="Explain how to compute tax with new signature using the system.\n# Repaired by Claude Sonnet 4.6 (Mock)",
        confidence=0.95,
    )

    # 2. Invalid patch (contains RejectMe) -> should be rejected by quality gate
    patch_invalid = DocPatch(
        filepath="docs.md",
        heading_path="Finance > Tax Calculation",
        original_content="Explain how to compute tax using the system.",
        repaired_content="Explain how to compute tax with new signature using the system.\n# Repaired by Claude Sonnet 4.6 (Mock) - RejectMe",
        confidence=0.95,
    )

    chunk_map = {"Finance > Tax Calculation": chunk}
    patches = [patch_valid, patch_invalid]

    valid_patches = use_case.execute(patches, chunk_map)

    # We expect only patch_valid to pass the gate
    assert len(valid_patches) == 1
    assert valid_patches[0].repaired_content == patch_valid.repaired_content
    assert "RejectMe" not in valid_patches[0].repaired_content
