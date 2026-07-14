from typing import Dict, List

# pyrefly: ignore [missing-import]
from src.domain.models import CodeChunk, DocPatch

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.llm import LlmGateway


class ValidateCorrectionsUseCase:
    def __init__(self, llm_client: LlmGateway):
        self._llm_client = llm_client

    def execute(self, patches: List[DocPatch], chunk_map: Dict[str, CodeChunk]) -> List[DocPatch]:
        """
        Validates generated DocPatches against the new code chunks using a second LLM pass.
        Only returns patches that pass the validation quality gate.
        """
        valid_patches: List[DocPatch] = []
        for patch in patches:
            if patch.heading_path not in chunk_map:
                # If we don't have code chunk context, default pass
                valid_patches.append(patch)
                continue

            code_chunk = chunk_map[patch.heading_path]
            res = self._llm_client.validate_correction(patch, code_chunk)

            # If the validation pass indicates it is NOT stale (i.e. corrected doc matches code correctly), it passes!
            if not res.is_stale:
                patch.confidence = min(patch.confidence, res.confidence)
                valid_patches.append(patch)

        return valid_patches
