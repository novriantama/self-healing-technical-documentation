import os
from typing import Dict, List, Tuple

# pyrefly: ignore [missing-import]
from src.domain.models import CodeChunk, DocPatch, DocSection, VerificationResult

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.doc_parser import DocParserGateway

# pyrefly: ignore [missing-import]
from src.interfaces.gateways.llm import LlmGateway


class GenerateCorrectionsUseCase:
    def __init__(self, doc_parser: DocParserGateway, llm_client: LlmGateway, confidence_threshold: float = 0.8):
        self._doc_parser = doc_parser
        self._llm_client = llm_client
        self._confidence_threshold = confidence_threshold

    def execute(
        self,
        verified_stale: Dict[str, List[Tuple[CodeChunk, VerificationResult]]],
        workspace_dir: str,
    ) -> List[DocPatch]:
        """
        Generates corrected markdown content for each verified stale section.
        Returns a list of DocPatch objects representing the suggested repairs.
        """
        # 1. Resolve filepath and original DocSection for stale heading paths
        doc_sections: Dict[str, Tuple[str, DocSection]] = {}
        for dirpath, _, filenames in os.walk(workspace_dir):
            if any(part in dirpath.split(os.sep) for part in [".venv", "venv", ".git", ".pytest_cache"]):
                continue
            for fname in filenames:
                if fname.endswith(".md") and "README" not in fname:
                    filepath = os.path.join(dirpath, fname)
                    for sec in self._doc_parser.parse_file(filepath):
                        doc_sections[sec.heading_path] = (filepath, sec)

        patches: List[DocPatch] = []

        # 2. Iterate through each verified stale doc section and generate corrections
        for heading_path, issues in verified_stale.items():
            if heading_path not in doc_sections:
                continue
            filepath, original_doc = doc_sections[heading_path]

            repaired_content = original_doc.content
            total_confidence = 1.0

            # Apply corrections sequentially for all changed code chunks linked to this doc section
            for chunk, res in issues:
                temp_doc = DocSection(
                    heading_path=heading_path,
                    content=repaired_content,
                    references=original_doc.references,
                )
                repaired_content = self._llm_client.generate_correction(temp_doc, chunk, res.explanation)
                total_confidence = min(total_confidence, res.confidence)

            if repaired_content != original_doc.content:
                # Mode selection based on LLM confidence level
                mode = "auto_fix"
                if total_confidence < self._confidence_threshold:
                    mode = "draft"
                    todo_marker = (
                        "<!-- TODO: HUMAN REVIEW REQUIRED - Low confidence correction "
                        f"({total_confidence:.2f}). Please review the changes below. -->\n\n"
                    )
                    repaired_content = todo_marker + repaired_content

                patches.append(
                    DocPatch(
                        filepath=filepath,
                        heading_path=heading_path,
                        original_content=original_doc.content,
                        repaired_content=repaired_content,
                        confidence=total_confidence,
                        mode=mode,
                    )
                )

        return patches
