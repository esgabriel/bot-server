from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

_vector_db_instance = None

def get_vector_db():
    global _vector_db_instance
    
    if _vector_db_instance is None:
        logger.info(f"Iniciando conexión a ChromaDB en: {settings.CHROMA_DB_DIR}")
        
        try:
            embedding_function = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY)
            
            _vector_db_instance = Chroma(
                persist_directory=settings.CHROMA_DB_DIR,
                embedding_function=embedding_function,
                collection_name="documentos_chatbot"
            )
            logger.info("Conexión a ChromaDB establecida correctamente.")
            
        except Exception as e:
            logger.critical(f"Error al conectar con ChromaDB: {e}", exc_info=True)
            raise e
        
    return _vector_db_instance