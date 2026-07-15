# pyrefly: ignore [missing-import]
import json
import os
import tempfile

# pyrefly: ignore [missing-import]
import main

# pyrefly: ignore [missing-import]
from src.infrastructure.parsers.json_index_store import JsonIndexStore


def test_action_integration_flow(monkeypatch):
    # Create temp directory workspace
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Setup mock codebase file math.py
        code_file = os.path.join(tmpdir, "math.py")
        with open(code_file, "w") as f:
            f.write('def calculate_tax(new_price: float):\n    """Compute tax value."""\n    return new_price * 0.1\n')

        # 2. Setup mock documentation file docs.md
        doc_file = os.path.join(tmpdir, "docs.md")
        with open(doc_file, "w") as f:
            f.write("# Finance\n## Tax Calculation\nExplain how to compute tax using the system.\n")

        # 3. Setup mock codebase-to-docs link graph index json file
        index_path = os.path.join(tmpdir, "docs_index.json")
        graph = {"math.py::calculate_tax": ["Finance > Tax Calculation"]}
        index_store = JsonIndexStore()
        index_store.save(graph, index_path)

        # 4. Mock git diff output (renaming old_price to new_price)
        diff_content = (
            "diff --git a/math.py b/math.py\n"
            "index 123456..789012 100644\n"
            "--- a/math.py\n"
            "+++ b/math.py\n"
            "@@ -1,3 +1,3 @@\n"
            "-def calculate_tax(old_price: float):\n"
            "+def calculate_tax(new_price: float):\n"
            '     """Compute tax value."""\n'
            "     return new_price * 0.1\n"
        )
        monkeypatch.setattr(main, "get_git_diff", lambda: diff_content)

        # 5. Configure GitHub Action environment variables
        monkeypatch.setenv("INPUT_LLM_API_KEY", "mock")
        monkeypatch.setenv("INPUT_CONFIDENCE_THRESHOLD", "0.8")
        monkeypatch.setenv("INPUT_AUTO_MERGE", "true")
        monkeypatch.setenv("INPUT_INDEX_PATH", index_path)
        monkeypatch.setenv("INPUT_WORKSPACE_DIR", tmpdir)

        # Mock GITHUB_OUTPUT file
        output_file = os.path.join(tmpdir, "github_output.txt")
        monkeypatch.setenv("GITHUB_OUTPUT", output_file)

        # Mock GITHUB_EVENT_PATH and repository details
        event_file = os.path.join(tmpdir, "event.json")
        with open(event_file, "w") as f:
            json.dump({"pull_request": {"number": 42}}, f)
        monkeypatch.setenv("GITHUB_EVENT_PATH", event_file)
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")

        # 6. Run action entrypoint main()
        main.main()

        # 7. Assert doc file was auto-repaired successfully!
        with open(doc_file, "r") as f:
            repaired_doc_content = f.read()

        assert "compute tax with new signature using" in repaired_doc_content
        assert "Repaired by Claude Sonnet 4.6 (Mock)" in repaired_doc_content

        # 8. Assert GITHUB_OUTPUT variables were written
        assert os.path.exists(output_file)
        with open(output_file, "r") as f:
            output_lines = f.readlines()

        assert any("stale_sections=" in line for line in output_lines)
        assert any("corrections=" in line for line in output_lines)
