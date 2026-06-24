import os
from pydantic_settings import BaseSettings


from typing import Optional

class Settings(BaseSettings):
    database_url: str = "sqlite:///./clinicflow.db"
    
    # Generic LLM settings
    llm_provider: str = "openai"
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_model: Optional[str] = None
    
    # Explicit OpenAI/Nvidia settings (fallback)
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "meta/llama-3.1-8b-instruct"

    class Config:
        env_file = (".env", "../.env", "../../.env")
        env_file_encoding = "utf-8"


settings = Settings()
