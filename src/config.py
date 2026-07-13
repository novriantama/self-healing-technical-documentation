from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    anthropic_api_key: str = Field(..., validation_alias="ANTHROPIC_API_KEY")
    openai_api_key: str = Field("", validation_alias="OPENAI_API_KEY")  # Optional: for OpenAI embeddings
    
    confidence_threshold: float = Field(0.8, validation_alias="CONFIDENCE_THRESHOLD")
    workspace_dir: str = Field(".", validation_alias="WORKSPACE_DIR")
    chroma_db_dir: str = Field("./.chroma_db", validation_alias="CHROMA_DB_DIR")
