import json
import os
import subprocess
import sys

# pyrefly: ignore [missing-import]
from src.infrastructure.git.github_provider import GitHubProvider

# pyrefly: ignore [missing-import]
from src.infrastructure.llm.anthropic_client import AnthropicLlmClient

# pyrefly: ignore [missing-import]
from src.infrastructure.parsers.ast_code_parser import AstCodeParser

# pyrefly: ignore [missing-import]
from src.infrastructure.parsers.json_index_store import JsonIndexStore

# pyrefly: ignore [missing-import]
from src.infrastructure.parsers.mistletoe_doc_parser import MistletoeDocParser

# pyrefly: ignore [missing-import]
from src.use_cases.generate_corrections import GenerateCorrectionsUseCase

# pyrefly: ignore [missing-import]
from src.use_cases.get_changed_code_chunks import GetChangedCodeChunksUseCase

# pyrefly: ignore [missing-import]
from src.use_cases.identify_stale_docs import IdentifyStaleDocsUseCase

# pyrefly: ignore [missing-import]
from src.use_cases.run_pr_workflow import RunPrWorkflowUseCase

# pyrefly: ignore [missing-import]
from src.use_cases.validate_corrections import ValidateCorrectionsUseCase

# pyrefly: ignore [missing-import]
from src.use_cases.verify_stale_docs import VerifyStaleDocsUseCase


def get_git_diff() -> str:
    """Retrieves the unified git diff text for the changed files."""
    # Check GITHUB_BASE_REF for PR base branches
    base_ref = os.environ.get("GITHUB_BASE_REF")
    if base_ref:
        subprocess.run(["git", "fetch", "origin", base_ref], capture_output=True)
        res = subprocess.run(["git", "diff", f"origin/{base_ref}...HEAD"], capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout

    # Fallback to origin/main
    subprocess.run(["git", "fetch", "origin", "main"], capture_output=True)
    res = subprocess.run(["git", "diff", "origin/main...HEAD"], capture_output=True, text=True)
    if res.returncode == 0 and res.stdout.strip():
        return res.stdout

    # Local fallback
    res = subprocess.run(["git", "diff", "HEAD~1"], capture_output=True, text=True)
    if res.returncode == 0 and res.stdout.strip():
        return res.stdout

    return ""


def main():
    # 1. Retrieve inputs
    llm_api_key = os.environ.get("INPUT_LLM_API_KEY")
    if not llm_api_key:
        print("Error: INPUT_LLM_API_KEY environment variable is required.")
        sys.exit(1)

    threshold_str = os.environ.get("INPUT_CONFIDENCE_THRESHOLD", "0.8")
    try:
        confidence_threshold = float(threshold_str)
    except ValueError:
        confidence_threshold = 0.8

    auto_merge_str = os.environ.get("INPUT_AUTO_MERGE", "true").lower()
    auto_merge = auto_merge_str == "true"

    index_path = os.environ.get("INPUT_INDEX_PATH", "docs_index.json")
    workspace_dir = os.environ.get("INPUT_WORKSPACE_DIR", ".")

    # 2. Extract git diff
    diff_text = get_git_diff()
    if not diff_text.strip():
        print("No code changes detected. Exiting gracefully.")
        # Setup empty outputs
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a") as f:
                f.write("stale_sections=[]\n")
                f.write("corrections=[]\n")
        sys.exit(0)

    # 3. Instantiate domain dependencies
    git_provider = GitHubProvider("")
    code_parser = AstCodeParser()
    doc_parser = MistletoeDocParser()
    llm_client = AnthropicLlmClient(api_key=llm_api_key)
    index_store = JsonIndexStore()

    # 4. Instantiate Use Cases
    get_changed_chunks = GetChangedCodeChunksUseCase(git_provider, code_parser, llm_client)
    identify_stale_docs = IdentifyStaleDocsUseCase(get_changed_chunks, index_store)
    verify_stale_docs = VerifyStaleDocsUseCase(git_provider, doc_parser, llm_client)
    generate_corrections = GenerateCorrectionsUseCase(doc_parser, llm_client, confidence_threshold)
    validate_corrections = ValidateCorrectionsUseCase(llm_client)

    # 5. Execute flow
    print("Identifying suspect documentation headings...")
    suspects = identify_stale_docs.execute(diff_text, workspace_dir, index_path)

    print(f"Verifying staleness of {len(suspects)} suspect documentation headings...")
    verified_stale = verify_stale_docs.execute(suspects, diff_text, workspace_dir)

    print(f"Generating repairs for {len(verified_stale)} stale document sections...")
    patches = generate_corrections.execute(verified_stale, workspace_dir)

    print(f"Validating {len(patches)} suggested repairs against quality gate...")
    chunk_map = {heading: chunks[0] for heading, chunks in suspects.items() if chunks}
    valid_patches = validate_corrections.execute(patches, chunk_map)

    # 6. Apply corrections if auto_merge is enabled
    if auto_merge:
        for patch in valid_patches:
            if os.path.exists(patch.filepath):
                with open(patch.filepath, "r") as f:
                    content = f.read()
                if patch.original_content in content:
                    updated = content.replace(patch.original_content, patch.repaired_content)
                    with open(patch.filepath, "w") as f:
                        f.write(updated)
                    print(f"Auto-applied patch to {patch.filepath} ({patch.heading_path})")
                else:
                    print(f"Warning: original content mismatch in {patch.filepath}")

    # 7. Run PR workflow
    repo_name = os.environ.get("GITHUB_REPOSITORY", "owner/repo")
    pr_number = 0
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_path and os.path.exists(event_path):
        try:
            with open(event_path, "r") as f:
                event = json.load(f)
            pr_data = event.get("pull_request")
            if pr_data:
                pr_number = pr_data.get("number", 0)
        except Exception as e:
            print(f"Warning: Failed to parse GITHUB_EVENT_PATH: {e}")

    print("Running PR workflow...")
    run_pr_workflow = RunPrWorkflowUseCase(git_provider)
    run_pr_workflow.execute(suspects, valid_patches, verified_stale, repo_name, pr_number)

    # 7. Write outputs to environment
    github_output = os.environ.get("GITHUB_OUTPUT")
    stale_list = list(verified_stale.keys())
    corr_list = [p.model_dump() for p in valid_patches]

    print("--- RUN SUMMARY ---")
    print(f"Stale sections found: {stale_list}")
    print(f"Corrections successfully generated: {len(corr_list)}")

    if github_output:
        with open(github_output, "a") as f:
            f.write(f"stale_sections={json.dumps(stale_list)}\n")
            f.write(f"corrections={json.dumps(corr_list)}\n")


if __name__ == "__main__":
    main()
