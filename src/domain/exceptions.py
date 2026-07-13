class DomainError(Exception):
    """Base domain exception."""

    pass


class ParserError(DomainError):
    """Raised when parser fails to process code or docs."""

    pass


class VectorStoreError(DomainError):
    """Raised when vector store operations fail."""

    pass


class LlmClientError(DomainError):
    """Raised when communication with the LLM API fails."""

    pass


class GitError(DomainError):
    """Raised when git provider actions fail."""

    pass
