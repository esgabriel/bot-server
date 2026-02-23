from pydantic_settings import BaseSettings
from typing import Optional
import json

class Settings(BaseSettings):
    PROJECT_NAME: str = "Chatbot RAG Multi-Sitio"
    VERSION: str = "2.0.0"

    # OpenAI
    OPENAI_API_KEY: str
    MODEL_NAME: str = "gpt-3.5-turbo"
    TEMPERATURE: float = 0.0

    # RAG
    CHROMA_DB_DIR: str = "./data/chroma"
    COLLECTION_NAME: str = "documentos_chatbot"
    TOP_K_RESULTS: int = 5
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # API
    API_V1_PREFIX: str = "/api"

    # Seguridad — definir los orígenes permitidos en el .env como JSON:
    # CORS_ORIGINS=["https://tu-sitio.com","https://otro-sitio.com"]
    # Para desarrollo local se puede usar: CORS_ORIGINS=["http://localhost:3000"]
    CORS_ORIGINS: list[str] = []

    # Clave secreta para autenticar el plugin de WordPress.
    # El plugin debe enviar este valor en el header: X-API-Key: <clave>
    # Genera una clave segura con: openssl rand -hex 32
    API_SECRET_KEY: str

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()