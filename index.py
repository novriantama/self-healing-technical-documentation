import os
import sys

# pyrefly: ignore [missing-import]
from src.infrastructure.llm.anthropic_client import AnthropicLlmClient

# pyrefly: ignore [missing-import]
from src.infrastructure.parsers.ast_code_parser import AstCodeParser

# pyrefly: ignore [missing-import]
from src.infrastructure.parsers.json_index_store import JsonIndexStore

# pyrefly: ignore [missing-import]
from src.infrastructure.parsers.mistletoe_doc_parser import MistletoeDocParser

# pyrefly: ignore [missing-import]
from src.use_cases.index_codebase import IndexCodebaseUseCase


def main():
    llm_api_key = os.environ.get("INPUT_LLM_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not llm_api_key:
        print("Error: ANTHROPIC_API_KEY environment variable is required to run the indexer.")
        sys.exit(1)

    workspace_dir = os.environ.get("INPUT_WORKSPACE_DIR") or "."
    index_path = os.environ.get("INPUT_INDEX_PATH") or "docs_index.json"

    print(f"Indexing codebase at: {workspace_dir}")
    print("Parsing files...")

    code_parser = AstCodeParser()
    doc_parser = MistletoeDocParser()
    llm_client = AnthropicLlmClient(api_key=llm_api_key)

    use_case = IndexCodebaseUseCase(code_parser, doc_parser, llm_client)
    graph = use_case.execute(workspace_dir)

    print(f"Index complete. Found mapping for {len(graph)} code definition(s).")
    print(f"Saving index graph to: {index_path}")

    index_store = JsonIndexStore()
    index_store.save(graph, index_path)
    print("Done!")


if __name__ == "__main__":
    main()
