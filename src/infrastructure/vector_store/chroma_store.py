import chromadb
from typing import List
from src.interfaces.gateways.vector_store import VectorStoreGateway
from src.domain.models import DocSection
from src.domain.exceptions import VectorStoreError

class ChromaVectorStore(VectorStoreGateway):
    def __init__(self, db_dir: str):
        self._db_dir = db_dir
        try:
            self._client = chromadb.PersistentClient(path=db_dir)
            self._collection = self._client.get_or_create_collection("docs_sections")
        except Exception as e:
            raise VectorStoreError(f"Failed to initialize ChromaDB at {db_dir}: {e}") from e

    def index_sections(self, sections: List[DocSection]) -> None:
        try:
            for i, section in enumerate(sections):
                self._collection.add(
                    documents=[section.content],
                    metadatas=[{"heading_path": section.heading_path, "references": ",".join(section.references)}],
                    ids=[f"sec_{i}"]
                )
        except Exception as e:
            raise VectorStoreError(f"Failed to add documents to ChromaDB: {e}") from e

    def search_similar_sections(self, code_query: str, limit: int = 3) -> List[DocSection]:
        try:
            results = self._collection.query(
                query_texts=[code_query],
                n_results=limit
            )
            sections = []
            if results and "documents" in results and results["documents"]:
                documents = results["documents"][0]
                metadatas = results["metadatas"][0]
                for doc, meta in zip(documents, metadatas):
                    refs = meta.get("references", "").split(",") if meta.get("references") else []
                    sections.append(DocSection(
                        heading_path=meta.get("heading_path", ""),
                        content=doc,
                        references=[r for r in refs if r]
                    ))
            return sections
        except Exception as e:
            raise VectorStoreError(f"Failed to query ChromaDB: {e}") from e
