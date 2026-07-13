from abc import ABC, abstractmethod

# pyrefly: ignore [missing-import]
from src.domain.models import CodeChunk, DocSection, VerificationResult


class LlmGateway(ABC):
    @abstractmethod
    def verify_accuracy(self, old_code: CodeChunk, new_code: CodeChunk, doc: DocSection) -> VerificationResult:
        """Determines if documentation remains accurate given changes from old to new code."""
        pass

    @abstractmethod
    def generate_correction(self, doc: DocSection, new_code: CodeChunk, reason: str) -> str:
        """Generates updated documentation content for a stale section."""
        pass

    @abstractmethod
    def check_semantic_link(self, code: CodeChunk, doc: DocSection) -> bool:
        """Asks the LLM to classify if the code and documentation section are semantically linked."""
        pass
