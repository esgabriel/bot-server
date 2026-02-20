from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.db.chroma import get_vector_db
from app.core.config import settings
from typing import Optional
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

def generar_respuesta(pregunta: str, site_id: str) -> str:
    """
    Genera una respuesta usando RAG (Retrieval-Augmented Generation).
    
    Flujo:
    1. Valida los parámetros de entrada
    2. Busca documentos relevantes en ChromaDB (filtrados por site_id)
    3. Construye un contexto con los documentos encontrados
    4. Envía el contexto y la pregunta a GPT
    5. Retorna la respuesta generada

    """
    
    # Validación de parámetros
    if not pregunta or not site_id:
        logger.warning(f"Parámetros inválidos - pregunta: '{pregunta}', site_id: '{site_id}'")
        raise ValueError("Pregunta y site_id son requeridos")
    
    # Sanitizar entrada (eliminar espacios en blanco)
    pregunta = pregunta.strip()
    site_id = site_id.strip()
    
    # Conectar a la base de datos vectorial
    try:
        vector_db = get_vector_db()
    except Exception as e:
        logger.error(f"Error conectando a ChromaDB: {e}", exc_info=True)
        raise ConnectionError("No se pudo conectar a la base de datos")

    # Búsqueda semántica con filtro de sitio (Multi-Sitio)
    try:
        docs = vector_db.similarity_search(
            query=pregunta,
            k=3,  # Número de documentos a recuperar (configurable en settings)
            filter={"site_id": site_id}
        )
    except Exception as e:
        logger.error(f"Error en búsqueda vectorial para site_id='{site_id}': {e}", exc_info=True)
        raise ConnectionError("Error al buscar en la base de datos")

    # Manejo de caso sin resultados
    if not docs:
        logger.info(f"No se encontraron documentos para site_id='{site_id}' y pregunta='{pregunta[:50]}...'")
        return "Lo siento, no tengo información sobre eso en mis documentos."

    # Log de documentos encontrados (para debugging)
    logger.debug(f"Encontrados {len(docs)} documentos para site_id='{site_id}'")

    # Construir el contexto a partir de los documentos encontrados
    contexto_texto = "\n\n---\n\n".join([doc.page_content for doc in docs])

    # Configurar el modelo de lenguaje (GPT)
    try:
        llm = ChatOpenAI(
            model_name=settings.MODEL_NAME,
            temperature=settings.TEMPERATURE,
            api_key=settings.OPENAI_API_KEY
        )
    except Exception as e:
        logger.error(f"Error inicializando OpenAI: {e}", exc_info=True)
        raise ConnectionError("Error al conectar con el servicio de IA")

    # Crear el prompt con instrucciones claras
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "Eres un asistente útil de la empresa. Responde basándote SOLO en el siguiente contexto. Si no sabes la respuesta, di que no tienes esa información."),
        ("user", "Contexto:\n{contexto}\n\nPregunta: {pregunta}")
    ])
    
    # Ejecutar la cadena (Prompt + LLM)
    try:
        chain = prompt_template | llm
        respuesta_ai = chain.invoke({"contexto": contexto_texto, "pregunta": pregunta})
        
        logger.info(f"Respuesta generada exitosamente para site_id='{site_id}'")
        return respuesta_ai.content
        
    except Exception as e:
        logger.error(f"Error generando respuesta con OpenAI: {e}", exc_info=True)
        raise ConnectionError("Error al generar la respuesta")


# Importar en routes.py para usar caché en respuestas frecuentes
@lru_cache(maxsize=100)
def generar_respuesta_cached(pregunta: str, site_id: str) -> str:
    return generar_respuesta(pregunta, site_id)


# Limpiar caché

def limpiar_cache():
    generar_respuesta_cached.cache_clear()
    logger.info("Caché de respuestas limpiado")


def obtener_estadisticas_cache() -> dict:
    """
    Obtiene estadísticas del caché.
    
    Returns:
        dict: Información sobre el uso del caché
            - hits: Veces que se usó el caché
            - misses: Veces que se generó respuesta nueva
            - maxsize: Tamaño máximo del caché
            - currsize: Tamaño actual del caché
    """
    info = generar_respuesta_cached.cache_info()
    return {
        "hits": info.hits,
        "misses": info.misses,
        "maxsize": info.maxsize,
        "currsize": info.currsize,
        "hit_rate": f"{(info.hits / (info.hits + info.misses) * 100):.2f}%" if (info.hits + info.misses) > 0 else "0%"
    }