from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Chatbot RAG Multi-Sitio"
    VERSION: str = "2.0.0"
    
    # OpenAI
    OPENAI_API_KEY: str
    MODEL_NAME: str = "gpt-3.5-turbo"
    TEMPERATURE: float = 0.0
    
    # RAG
    CHROMA_DB_DIR: str = "./data/chroma"
    TOP_K_RESULTS: int = 3  # Número de documentos a recuperar
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    # API
    API_V1_PREFIX: str = "/api"
    CORS_ORIGINS: list[str] = ["*"]  # Cambiar en producción
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()