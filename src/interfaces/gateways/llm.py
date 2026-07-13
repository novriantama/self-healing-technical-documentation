from abc import ABC, abstractmethod
from src.domain.models import CodeChunk, DocSection, VerificationResult

class LlmGateway(ABC):
    @abstractmethod
    def verify_accuracy(
        self, old_code: CodeChunk, new_code: CodeChunk, doc: DocSection
    ) -> VerificationResult:
        """Determines if documentation remains accurate given changes from old to new code."""
        pass

    @abstractmethod
    def generate_correction(
        self, doc: DocSection, new_code: CodeChunk, reason: str
    ) -> str:
        """Generates updated documentation content for a stale section."""
        pass
