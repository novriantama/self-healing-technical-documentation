import json
import os
import re

# pyrefly: ignore [missing-import]
from anthropic import Anthropic

# pyrefly: ignore [missing-import]
from src.domain.exceptions import LlmClientError

# pyrefly: ignore [missing-import]
from src.domain.models import CodeChunk, DocPatch, DocSection, VerificationResult

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.llm import LlmGateway


class AnthropicLlmClient(LlmGateway):
    def __init__(self, api_key: str):
        self._api_key = api_key
        # Check if openagentic.id should be used
        self._is_openagentic = (
            os.environ.get("OPENAGENTIC_API_KEY") is not None
            or "openagentic" in api_key.lower()
            or "sk-oa" in api_key.lower()
        )
        if self._is_openagentic:
            self._model = os.environ.get("OPENAGENTIC_MODEL", "claude-sonnet-4.6")
        else:
            self._model = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

        self._anthropic_client = None

        if api_key and api_key != "mock" and api_key != "mock-anthropic-key":
            base_url = None
            if self._is_openagentic:
                base_url = os.environ.get("OPENAGENTIC_BASE_URL", "https://openagentic.id/api/v1")
            self._anthropic_client = Anthropic(api_key=api_key, base_url=base_url)

    def _call_llm(self, prompt: str) -> str:
        if self._anthropic_client:
            response = self._anthropic_client.messages.create(
                model=self._model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            return response.content[0].text.strip()
        raise LlmClientError("LLM client not initialized properly.")

    def _parse_json(self, text: str) -> dict:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)
        try:
            return json.loads(text.strip())
        except Exception as e:
            raise LlmClientError(f"Failed to parse LLM response as JSON: {text}. Error: {e}") from e

    def verify_accuracy(self, old_code: CodeChunk, new_code: CodeChunk, doc: DocSection) -> VerificationResult:
        if not self._api_key or self._api_key == "mock" or self._api_key == "mock-anthropic-key":
            is_stale = old_code.signature != new_code.signature
            explanation = (
                f"Signature changed from '{old_code.signature}' to '{new_code.signature}'."
                if is_stale
                else "Signatures match; documentation remains accurate."
            )
            return VerificationResult(
                is_stale=is_stale,
                confidence=0.95 if is_stale else 1.0,
                explanation=explanation,
            )
        try:
            prompt = (
                "You are an expert technical writer. Compare the old code chunk and new code chunk with the technical documentation section to determine if the documentation has become stale or remains accurate.\n\n"
                f"Old Code:\n{old_code.signature}\n{old_code.docstring}\n\n"
                f"New Code:\n{new_code.signature}\n{new_code.docstring}\n\n"
                f"Documentation Section:\n{doc.content}\n\n"
                "Respond in JSON format with three keys:\n"
                '1. "is_stale": boolean (true if the documentation needs update, false otherwise)\n'
                '2. "confidence": float (between 0.0 and 1.0)\n'
                '3. "explanation": string (describe why it is stale or accurate)\n'
            )
            res_text = self._call_llm(prompt)
            data = self._parse_json(res_text)
            return VerificationResult(
                is_stale=data.get("is_stale", False),
                confidence=data.get("confidence", 1.0),
                explanation=data.get("explanation", ""),
            )
        except Exception as e:
            raise LlmClientError(f"LLM verification failed: {e}") from e

    def generate_correction(self, doc: DocSection, new_code: CodeChunk, reason: str) -> str:
        if not self._api_key or self._api_key == "mock" or self._api_key == "mock-anthropic-key":
            content = doc.content
            if new_code.name == "calculate_tax":
                content = content.replace("compute tax using", "compute tax with new signature using")
            return content + "\n# Repaired by Claude Sonnet 4.6 (Mock)"
        try:
            prompt = (
                "You are an expert technical writer. Rewrite ONLY the stale/inaccurate parts of the technical documentation section below to reflect the new code changes. Do not rewrite parts that are still accurate. Keep the exact style, tone, and structure of the original document.\n\n"
                f"New Code:\n{new_code.signature}\n{new_code.docstring}\n\n"
                f"Staleness Reason:\n{reason}\n\n"
                f"Original Documentation Section:\n{doc.content}\n\n"
                "Return ONLY the corrected documentation section content. Do not include any explanations, warnings, or code block markers."
            )
            return self._call_llm(prompt)
        except Exception as e:
            raise LlmClientError(f"LLM correction generation failed: {e}") from e

    def check_semantic_link(self, code: CodeChunk, doc: DocSection) -> bool:
        if not self._api_key or self._api_key == "mock" or self._api_key == "mock-anthropic-key":
            name_parts = code.name.lower().split(".")
            return any(part in doc.content.lower() or part in doc.heading_path.lower() for part in name_parts)
        try:
            prompt = (
                "Evaluate if there is a direct relationship or semantic link between the following code chunk and the technical documentation section.\n\n"
                f"Code Chunk:\nName: {code.name}\nSignature: {code.signature}\nDocstring: {code.docstring}\n\n"
                f"Documentation Section:\nHeading Path: {doc.heading_path}\nContent: {doc.content}\n\n"
                'Respond with exactly "yes" or "no".'
            )
            res_text = self._call_llm(prompt).lower().strip()
            return "yes" in res_text
        except Exception as e:
            raise LlmClientError(f"LLM semantic link check failed: {e}") from e

    def is_change_meaningful(self, chunk_name: str, diff_text: str) -> bool:
        if not self._api_key or self._api_key == "mock" or self._api_key == "mock-anthropic-key":
            lines = [line.strip() for line in diff_text.splitlines() if line.startswith("+") or line.startswith("-")]
            if not lines:
                return False
            only_comments_or_whitespace = all(
                line[1:].strip().startswith("#") or not line[1:].strip() for line in lines
            )
            return not only_comments_or_whitespace
        try:
            prompt = (
                "Determine if the following code change is meaningful for documentation.\n"
                "Meaningful changes include: API signature changes, configuration changes, new/removed features, and behavioral changes to functions.\n"
                "Non-meaningful changes (which you should skip) include: comments-only changes, whitespace changes, internal logic refactors that do not change external behavior, and test file changes.\n\n"
                f"Code diff for {chunk_name}:\n{diff_text}\n\n"
                'Respond with exactly "yes" or "no".'
            )
            res_text = self._call_llm(prompt).lower().strip()
            return "yes" in res_text
        except Exception as e:
            raise LlmClientError(f"LLM meaningful check failed: {e}") from e

    def validate_correction(self, patch: DocPatch, new_code: CodeChunk) -> VerificationResult:
        if not self._api_key or self._api_key == "mock" or self._api_key == "mock-anthropic-key":
            is_valid = (
                "Repaired by Claude Sonnet 4.6 (Mock)" in patch.repaired_content
                and "RejectMe" not in patch.repaired_content
            )
            return VerificationResult(
                is_stale=not is_valid,
                confidence=1.0,
                explanation=(
                    "Mock validation check passed successfully."
                    if is_valid
                    else "Rejected: Mock invalidation keyword 'RejectMe' triggered or repaired content missing."
                ),
            )
        try:
            prompt = (
                "You are a technical editor. Review the suggested documentation repair patch below and verify if:\n"
                "1. The corrected document accurately describes the new code.\n"
                "2. It preserved all parts that were already correct.\n"
                "3. The writing style remains consistent with the rest of the document.\n\n"
                f"New Code:\n{new_code.signature}\n{new_code.docstring}\n\n"
                f"Original Document:\n{patch.original_content}\n\n"
                f"Corrected Document:\n{patch.repaired_content}\n\n"
                "Respond in JSON format with three keys:\n"
                '1. "is_stale": boolean (true if the correction is invalid/stale/corrupt, false if it is valid and correct)\n'
                '2. "confidence": float (between 0.0 and 1.0)\n'
                '3. "explanation": string (describe your reasoning)\n'
            )
            res_text = self._call_llm(prompt)
            data = self._parse_json(res_text)
            return VerificationResult(
                is_stale=data.get("is_stale", True),
                confidence=data.get("confidence", 0.0),
                explanation=data.get("explanation", ""),
            )
        except Exception as e:
            raise LlmClientError(f"LLM validation failed: {e}") from e
