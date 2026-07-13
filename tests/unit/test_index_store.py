# pyrefly: ignore [missing-import]
import pytest
import tempfile
import os
# pyrefly: ignore [missing-import]
from src.infrastructure.parsers.json_index_store import JsonIndexStore
# pyrefly: ignore [missing-import]
from src.use_cases.query_affected_docs import QueryAffectedDocsUseCase

MOCK_INDEX_DATA = {
    "src/math.py::calculate_tax": [
        "Finance > Tax Calculation",
        "Finance > Billing"
    ],
    "src/user.py::auth_user": [
        "Security > Authentication"
    ]
}

def test_json_index_store_save_load():
    store = JsonIndexStore()
    
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
        temp_filepath = temp_file.name

    try:
        # Test loading a non-existent file returns empty dict
        assert store.load("non_existent_graph.json") == {}
        
        # Test saving
        store.save(MOCK_INDEX_DATA, temp_filepath)
        
        # Test loading
        loaded = store.load(temp_filepath)
        assert loaded == MOCK_INDEX_DATA
        assert "src/math.py::calculate_tax" in loaded
    finally:
        os.remove(temp_filepath)

def test_query_affected_docs_use_case():
    store = JsonIndexStore()
    use_case = QueryAffectedDocsUseCase(store)
    
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
        temp_filepath = temp_file.name

    try:
        # Save mock index
        store.save(MOCK_INDEX_DATA, temp_filepath)
        
        # Query with changes that exist in index
        changes = ["src/math.py::calculate_tax", "src/user.py::auth_user"]
        affected = use_case.execute(changes, temp_filepath)
        assert len(affected) == 3
        assert "Finance > Tax Calculation" in affected
        assert "Security > Authentication" in affected
        
        # Query with changes that do not exist
        no_changes = ["src/config.py::EngineConfig"]
        affected_empty = use_case.execute(no_changes, temp_filepath)
        assert affected_empty == []
    finally:
        os.remove(temp_filepath)
