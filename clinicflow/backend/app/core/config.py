import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./clinicflow.db"
    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "meta/llama-3.1-8b-instruct"

    class Config:
        env_file = (".env", "../.env", "../../.env")
        env_file_encoding = "utf-8"


settings = Settings()
