from src.domain.models import CodeChunk, VerificationResult


def test_code_chunk_initialization():
    chunk = CodeChunk(
        id="src/math.py::foo",
        name="foo",
        type="function",
        signature="foo()",
        docstring="a function",
        start_line=10,
        end_line=15,
    )
    assert chunk.name == "foo"
    assert chunk.start_line == 10


def test_verification_result():
    res = VerificationResult(is_stale=True, confidence=0.9, explanation="Stale parameters")
    assert res.is_stale is True
    assert res.confidence == 0.9
