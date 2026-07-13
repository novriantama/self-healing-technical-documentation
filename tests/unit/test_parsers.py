# pyrefly: ignore [missing-import]
import pytest
import tempfile
import os
# pyrefly: ignore [missing-import]
from src.infrastructure.parsers.ast_code_parser import AstCodeParser
# pyrefly: ignore [missing-import]
from src.domain.exceptions import ParserError

MOCK_SOURCE_CODE = """
import click
from pydantic import BaseModel
from dataclasses import dataclass

def standard_function(x: int, y: str = "default") -> bool:
    \"\"\"This is a standard function docstring.\"\"\"
    return True

@app.get("/items/{item_id}")
async def get_item(item_id: int) -> dict:
    \"\"\"Endpoint to get an item.\"\"\"
    return {"id": item_id}

@click.command()
@click.option("--count", default=1)
def process_data(count: int):
    \"\"\"CLI command process.\"\"\"
    pass

class RegularHelper:
    \"\"\"A regular utility class.\"\"\"
    def helper_method(self, data: list):
        pass

class UserSchema(BaseModel):
    \"\"\"A Pydantic database schema.\"\"\"
    username: str
    age: int

@dataclass
class EngineConfig:
    \"\"\"Dataclass config schema.\"\"\"
    port: int
"""

def test_ast_code_parser_classifications():
    parser = AstCodeParser()
    
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as temp_file:
        temp_file.write(MOCK_SOURCE_CODE)
        temp_filepath = temp_file.name

    try:
        chunks = parser.parse_file(temp_filepath)
        
        # We expect 7 chunks:
        # 1. standard_function (function)
        # 2. get_item (api_endpoint)
        # 3. process_data (cli_command)
        # 4. RegularHelper (class)
        # 5. RegularHelper.helper_method (function)
        # 6. UserSchema (configuration_schema)
        # 7. EngineConfig (configuration_schema)
        
        chunk_dict = {chunk.name: chunk for chunk in chunks}
        
        assert len(chunks) == 7
        
        # 1. standard_function
        assert "standard_function" in chunk_dict
        f_chunk = chunk_dict["standard_function"]
        assert f_chunk.type == "function"
        assert f_chunk.docstring == "This is a standard function docstring."
        assert f_chunk.signature == "def standard_function(x: int, y: str = 'default') -> bool"
        
        # 2. get_item
        assert "get_item" in chunk_dict
        api_chunk = chunk_dict["get_item"]
        assert api_chunk.type == "api_endpoint"
        assert api_chunk.signature == 'async def get_item(item_id: int) -> dict'
        
        # 3. process_data
        assert "process_data" in chunk_dict
        cli_chunk = chunk_dict["process_data"]
        assert cli_chunk.type == "cli_command"
        
        # 4. RegularHelper
        assert "RegularHelper" in chunk_dict
        class_chunk = chunk_dict["RegularHelper"]
        assert class_chunk.type == "class"
        
        # 5. helper_method
        assert "RegularHelper.helper_method" in chunk_dict
        method_chunk = chunk_dict["RegularHelper.helper_method"]
        assert method_chunk.type == "function"
        assert method_chunk.id == f"{temp_filepath}::RegularHelper.helper_method"
        
        # 6. UserSchema (BaseModel inheritance)
        assert "UserSchema" in chunk_dict
        schema_chunk = chunk_dict["UserSchema"]
        assert schema_chunk.type == "configuration_schema"
        assert schema_chunk.signature == "class UserSchema(BaseModel)"
        
        # 7. EngineConfig (dataclass / config name)
        assert "EngineConfig" in chunk_dict
        config_chunk = chunk_dict["EngineConfig"]
        assert config_chunk.type == "configuration_schema"
        
    finally:
        os.remove(temp_filepath)

def test_ast_code_parser_invalid_file():
    parser = AstCodeParser()
    with pytest.raises(ParserError):
        parser.parse_file("non_existent_file.py")


# pyrefly: ignore [missing-import]
from src.infrastructure.parsers.mistletoe_doc_parser import MistletoeDocParser

MOCK_DOC_CONTENT = """
# API Documentation

This is the main API section. We use `get_item` endpoint to fetch information.

## Configuration

Settings for the application:
* `PORT` - The port to listen on.
* `ANTHROPIC_API_KEY` - LLM service key.
* The settings are loaded into `EngineConfig` class.

### CLI Usage

You can launch using command `process_data(count)`.
We also reference calculate_tax function.
"""

def test_mistletoe_doc_parser_sections():
    parser = MistletoeDocParser()
    
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w", encoding="utf-8") as temp_file:
        temp_file.write(MOCK_DOC_CONTENT)
        temp_filepath = temp_file.name

    try:
        sections = parser.parse_file(temp_filepath)
        
        # We expect 3 sections under heading paths:
        # 1. API Documentation
        # 2. API Documentation > Configuration
        # 3. API Documentation > Configuration > CLI Usage
        
        assert len(sections) == 3
        
        sec_dict = {sec.heading_path: sec for sec in sections}
        
        assert "API Documentation" in sec_dict
        sec1 = sec_dict["API Documentation"]
        assert "get_item" in sec1.references
        
        assert "API Documentation > Configuration" in sec_dict
        sec2 = sec_dict["API Documentation > Configuration"]
        assert "PORT" in sec2.references
        assert "ANTHROPIC_API_KEY" in sec2.references
        assert "EngineConfig" in sec2.references
        
        assert "API Documentation > Configuration > CLI Usage" in sec_dict
        sec3 = sec_dict["API Documentation > Configuration > CLI Usage"]
        assert "process_data" in sec3.references
        assert "calculate_tax" in sec3.references
        
    finally:
        os.remove(temp_filepath)

def test_mistletoe_doc_parser_invalid_file():
    parser = MistletoeDocParser()
    with pytest.raises(ParserError):
        parser.parse_file("non_existent_doc.md")

