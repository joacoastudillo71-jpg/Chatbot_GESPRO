from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    db_connection_string: str

    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    retell_api_key: Optional[str] = None
    
    # Providers
    llm_provider: str = "OPENAI"
    embeddings_provider: str = "OPENAI"
    
    # Optional LangSmith logic handled by environment variables directly usually, 
    # but we can add them if we want to explicitly access them.
    
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

settings = Settings()
