import re
from typing import List
from src.interfaces.gateways.doc_parser import DocParserGateway
from src.domain.models import DocSection
from src.domain.exceptions import ParserError

class MistletoeDocParser(DocParserGateway):
    def parse_file(self, filepath: str) -> List[DocSection]:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            sections = re.split(r"^(#+ .+)$", content, flags=re.MULTILINE)
            chunks = []
            current_header_path = []
            
            for item in sections:
                item = item.strip()
                if not item:
                    continue
                
                if item.startswith("#"):
                    level = len(re.match(r"^#+", item).group(0))
                    header_title = item.lstrip("#").strip()
                    
                    while len(current_header_path) >= level:
                        current_header_path.pop()
                    current_header_path.append(header_title)
                else:
                    if current_header_path:
                        heading_path = " > ".join(current_header_path)
                        code_mentions = re.findall(r"`([^`]+)`", item)
                        
                        chunks.append(DocSection(
                            heading_path=heading_path,
                            content=item,
                            references=list(set(code_mentions))
                        ))
            return chunks
        except Exception as e:
            raise ParserError(f"Failed to parse markdown document {filepath}: {e}") from e
