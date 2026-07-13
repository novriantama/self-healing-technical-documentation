from typing import List

from pydantic import BaseModel, Field


class CodeChunk(BaseModel):
    id: str = Field(..., description="Unique path-based identifier (e.g. src/math_helper.py::calculate_tax)")
    name: str = Field(..., description="Function or class name")
    type: str = Field(..., description="Type of chunk (e.g., function, class)")
    signature: str = Field(..., description="Code signature structure")
    docstring: str = Field("", description="Extracted docstring if present")
    start_line: int = Field(..., description="Starting line in code file")
    end_line: int = Field(..., description="Ending line in code file")


class DocSection(BaseModel):
    heading_path: str = Field(..., description="Breadcrumb heading path (e.g. Setup > Installation)")
    content: str = Field(..., description="Raw text content of section")
    references: List[str] = Field(default_factory=list, description="Extracted code symbols mentioned")


class VerificationResult(BaseModel):
    is_stale: bool = Field(..., description="True if code modification makes the doc section outdated")
    confidence: float = Field(..., description="Model confidence score between 0.0 and 1.0")
    explanation: str = Field(..., description="Reason for staleness if is_stale is True")


class DocPatch(BaseModel):
    filepath: str = Field(..., description="Target file path of documentation")
    heading_path: str = Field(..., description="Target heading path to modify")
    original_content: str = Field(..., description="Current doc section content")
    repaired_content: str = Field(..., description="Repaired doc section content")
    confidence: float = Field(..., description="Confidence rating from generator")
