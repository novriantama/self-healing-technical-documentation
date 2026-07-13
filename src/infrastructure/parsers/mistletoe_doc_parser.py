import re
from typing import List
# pyrefly: ignore [missing-import]
from src.interfaces.gateways.doc_parser import DocParserGateway
# pyrefly: ignore [missing-import]
from src.domain.models import DocSection
# pyrefly: ignore [missing-import]
from src.domain.exceptions import ParserError

def extract_references(text: str) -> List[str]:
    """
    Extracts code references (functions, classes, variables, configs) from text.
    Includes backticked strings, snake_case, PascalCase, and ALL_CAPS keys.
    """
    refs = set()
    
    # 1. Backticked inline code blocks (e.g. `calculate_tax()`, `RegularHelper.method`)
    backtick_matches = re.findall(r"`([^`\n]+)`", text)
    for match in backtick_matches:
        match = match.strip()
        # Clean function call trailing parenthesis
        clean = re.sub(r"\([^\)]*\)", "", match).strip()
        if clean:
            refs.add(clean)
            # If it is dot-separated class.method, extract sub-elements too
            if "." in clean:
                parts = clean.split(".")
                refs.update(parts)
                
    # 2. General word heuristics for code tokens (snake_case, PascalCase, ALL_CAPS)
    words = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", text)
    for word in words:
        # Ignore plain numeric values or extremely short words
        if len(word) < 3:
            continue
            
        # snake_case (e.g. env_file, calculate_tax)
        if "_" in word and not word.isupper():
            refs.add(word)
        # PascalCase (e.g. UserSchema, EngineConfig)
        elif re.match(r"^[A-Z][a-z0-9]+[A-Z][a-zA-Z0-9]*$", word):
            refs.add(word)
        # ALL_CAPS (e.g. PORT, ANTHROPIC_API_KEY)
        elif re.match(r"^[A-Z_]{3,}$", word):
            refs.add(word)
            
    return sorted(list(refs))


class MistletoeDocParser(DocParserGateway):
    def parse_file(self, filepath: str) -> List[DocSection]:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Split by markdown headers
            sections = re.split(r"^(#+ .+)$", content, flags=re.MULTILINE)
            chunks = []
            current_header_path = []
            
            for item in sections:
                item = item.strip()
                if not item:
                    continue
                
                if item.startswith("#"):
                    # Determine heading level from leading hash symbols
                    level = len(re.match(r"^#+", item).group(0))
                    header_title = item.lstrip("#").strip()
                    
                    # Update breadcrumb stack
                    while len(current_header_path) >= level:
                        current_header_path.pop()
                    current_header_path.append(header_title)
                else:
                    # Content block under current header
                    if current_header_path:
                        heading_path = " > ".join(current_header_path)
                        code_mentions = extract_references(item)
                        
                        chunks.append(DocSection(
                            heading_path=heading_path,
                            content=item,
                            references=code_mentions
                        ))
            return chunks
        except Exception as e:
            raise ParserError(f"Failed to parse markdown document {filepath}: {e}") from e
