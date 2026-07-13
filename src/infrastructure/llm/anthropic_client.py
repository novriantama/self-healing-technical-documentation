# pyrefly: ignore [missing-import]
from anthropic import Anthropic
# pyrefly: ignore [missing-import]
from src.interfaces.gateways.llm import LlmGateway
# pyrefly: ignore [missing-import]
from src.domain.models import CodeChunk, DocSection, VerificationResult
# pyrefly: ignore [missing-import]
from src.domain.exceptions import LlmClientError

class AnthropicLlmClient(LlmGateway):
    def __init__(self, api_key: str):
        self._api_key = api_key
        # Initialize Anthropic client if api key is provided
        self._client = Anthropic(api_key=api_key) if api_key else None

    def verify_accuracy(
        self, old_code: CodeChunk, new_code: CodeChunk, doc: DocSection
    ) -> VerificationResult:
        if not self._api_key or self._api_key == "mock":
            return VerificationResult(
                is_stale=False,
                confidence=1.0,
                explanation="Anthropic API Key not configured or mock. Mock validation."
            )
        try:
            # Placeholder for Claude Sonnet 4.6 completion logic
            # Response validation will parse into VerificationResult
            return VerificationResult(
                is_stale=True,
                confidence=0.9,
                explanation="Mock change detection: doc references outdated function signature."
            )
        except Exception as e:
            raise LlmClientError(f"Anthropic API request failed: {e}") from e

    def generate_correction(
        self, doc: DocSection, new_code: CodeChunk, reason: str
    ) -> str:
        if not self._api_key or self._api_key == "mock" or self._api_key == "mock-anthropic-key":
            return doc.content + "\n\n# Updated by Claude Sonnet 4.6 (Mock)"
        try:
            # Placeholder for doc repair logic
            return doc.content
        except Exception as e:
            raise LlmClientError(f"Anthropic API request failed: {e}") from e

    def check_semantic_link(self, code: CodeChunk, doc: DocSection) -> bool:
        if not self._api_key or self._api_key == "mock" or self._api_key == "mock-anthropic-key":
            # Deterministic mock rule for testing semantic linkage
            name_parts = code.name.lower().split(".")
            # Link if any part of the name matches doc heading or body content keywords
            return any(part in doc.content.lower() or part in doc.heading_path.lower() for part in name_parts)
        try:
            # Claude Sonnet 4.6 classification logic placeholder
            return False
        except Exception as e:
            raise LlmClientError(f"Anthropic API request failed: {e}") from e
