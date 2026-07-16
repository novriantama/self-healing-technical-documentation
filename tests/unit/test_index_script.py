# pyrefly: ignore [missing-import]
import os
import tempfile

# pyrefly: ignore [missing-import]
import index


def test_index_script_main(monkeypatch):
    # Mock environment variables
    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = os.path.join(tmpdir, "docs_index.json")
        monkeypatch.setenv("INPUT_LLM_API_KEY", "mock")
        monkeypatch.setenv("INPUT_WORKSPACE_DIR", tmpdir)
        monkeypatch.setenv("INPUT_INDEX_PATH", index_path)

        # Mock IndexCodebaseUseCase
        class MockIndexCodebaseUseCase:
            def __init__(self, *args, **kwargs):
                pass

            def execute(self, workspace_dir, *args, **kwargs):
                return {"test.py::func": ["Doc > Sec"]}

        # Mock JsonIndexStore
        class MockJsonIndexStore:
            def save(self, graph, path):
                with open(path, "w") as f:
                    f.write("saved")

        monkeypatch.setattr(index, "IndexCodebaseUseCase", MockIndexCodebaseUseCase)
        monkeypatch.setattr(index, "JsonIndexStore", MockJsonIndexStore)

        index.main()

        assert os.path.exists(index_path)
        with open(index_path, "r") as f:
            assert f.read() == "saved"
