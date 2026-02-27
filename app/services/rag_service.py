"""
Servicio RAG (Retrieval-Augmented Generation)
Genera respuestas basadas en los documentos PDF de cada sitio.
"""

from langchain_openai import ChatOpenAI 
from langchain_core.prompts import ChatPromptTemplate
from app.db.chroma import get_vector_db
from app.core.config import settings
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

# PROMPT DEL SISTEMA

SYSTEM_PROMPT = """You are a top-tier customer service assistant.

## Core Rules

1. **Act as a Natural Human Agent (CRITICAL)**
   - NEVER mention "documents", "context", "database", "PDFs", or "system" in your response.
   - Never say things like "According to my documents...", "Based on the provided context...",
     or "I don't have that information in my documents."
   - Present information naturally, as if you are a knowledgeable human expert who simply knows the answers.

2. **Language detection (CRITICAL)**
   - Detect the language of the user's question automatically.
   - ALWAYS respond in the exact same language the user wrote in. No exceptions.
   - If the user writes in Spanish → respond completely in Spanish.
   - If the user writes in English → respond completely in English.
   - If the user writes in French, Portuguese, or any other language → respond in that language.
   - This rule overrides everything else. Never switch languages unless the user does first.

3. **Strict accuracy**
   - Only answer using information explicitly found in the retrieved context.
   - Never invent, assume, or supplement with outside knowledge.
   - If the context contains Q&A pairs, extract the relevant answer and present it naturally.
     Do not copy raw text mechanically — rephrase it in a conversational, human way.

4. **When the answer is not available (FALLBACK RULE)**
   - If the context does not contain enough information to answer, politely apologize.
   - English example: "I don't have information about that. Can I help you with something else?"
- Spanish example: "No tengo información sobre eso. ¿Puedo ayudarte con algo más?"

   - Always adapt the fallback message to the user's language.
   - Do NOT guess or make up an answer under any circumstance.

6. **Identity questions**
   - If asked "Are you a robot?", "Are you an AI?", or similar, respond naturally as a
     customer service assistant without confirming or denying being an AI.
   - Example: "I'm a virtual assistant here to help you with any questions. How can I help you today?"

7. **Tone and format**
   - Be friendly, concise, and professional.
   - Avoid unnecessary filler phrases like "Great question!", "Of course!", or "Certainly!".
   - Keep responses under 100 words whenever possible.
   - When answering about company overviews, services, or lists of features, always use short bullet points instead of long paragraphs.
   - Use bullet points only when the answer genuinely benefits from a list.
   - Never write walls of text. If the answer requires more than 3 sentences in a row, break it into bullets.
   - Keep responses focused — don't over-explain.
"""


def generar_respuesta(pregunta: str, site_id: str) -> str:
    """
    Genera una respuesta usando RAG (Retrieval-Augmented Generation).

    Flujo:
    1. Valida los parámetros de entrada.
    2. Busca documentos relevantes en ChromaDB filtrados por site_id.
    3. Filtra resultados por umbral de similitud para evitar contexto irrelevante.
    4. Construye un contexto con los documentos encontrados.
    5. Envía el contexto y la pregunta a GPT con un prompt multilingüe.
    6. Retorna la respuesta generada en el idioma del usuario.

    Args:
        pregunta: Pregunta del usuario.
        site_id:  ID del sitio WordPress al que pertenece el chatbot.

    Returns:
        str: Respuesta generada por el modelo.
    """

    if not pregunta or not site_id:
        logger.warning(f"Parámetros inválidos — pregunta: '{pregunta}', site_id: '{site_id}'")
        raise ValueError("Pregunta y site_id son requeridos")

    pregunta = pregunta.strip()
    site_id  = site_id.strip()

    # Conexión a la base de datos vectorial
    try:
        vector_db = get_vector_db()
    except Exception as e:
        logger.error(f"Error conectando a ChromaDB: {e}", exc_info=True)
        raise ConnectionError("No se pudo conectar a la base de datos")

    # Búsqueda semántica con umbral de relevancia
    #    - k=5: recupera hasta 5 chunks (útil para PDFs con Q&A)
    #    - score_threshold=0.3: descarta resultados poco relacionados
    #      para evitar que el modelo reciba contexto que lo confunda
    try:
        retriever = vector_db.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "k": 5,
                "score_threshold": 0.1,
                "filter": {"site_id": site_id}
            }
        )
        docs = retriever.invoke(pregunta)

    except Exception as e:
        logger.error(f"Error en búsqueda vectorial para site_id='{site_id}': {e}", exc_info=True)
        raise ConnectionError("Error al buscar en la base de datos")

    # Manejo del caso sin resultados relevantes
    if not docs:
        logger.info(
            f"Sin documentos relevantes — site_id='{site_id}', "
            f"pregunta='{pregunta[:60]}...'"
        )
        # Dejar que el modelo responda con el prompt de "no tengo información"
        # pasándole un contexto vacío — así responde en el idioma del usuario
        contexto_texto = "(No relevant documents found for this query.)"
    else:
        logger.debug(f"Documentos recuperados: {len(docs)} para site_id='{site_id}'")
        contexto_texto = "\n\n---\n\n".join([doc.page_content for doc in docs])

    # Inicializar el modelo de lenguaje
    try:
        llm = ChatOpenAI(
            model_name=settings.MODEL_NAME,
            temperature=settings.TEMPERATURE,
            api_key=settings.OPENAI_API_KEY
        )
    except Exception as e:
        logger.error(f"Error inicializando OpenAI: {e}", exc_info=True)
        raise ConnectionError("Error al conectar con el servicio de IA")

    # Construir el prompt y ejecutar la cadena
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user",
         "Context from official business documents:\n"
         "{contexto}\n\n"
         "---\n"
         "User question: {pregunta}")
    ])

    try:
        chain = prompt_template | llm
        respuesta_ai = chain.invoke({
            "contexto": contexto_texto,
            "pregunta": pregunta
        })

        logger.info(f"Respuesta generada exitosamente para site_id='{site_id}'")
        return respuesta_ai.content

    except Exception as e:
        logger.error(f"Error generando respuesta con OpenAI: {e}", exc_info=True)
        raise ConnectionError("Error al generar la respuesta")


# CACHÉ DE RESPUESTAS FRECUENTES
# Si se recarga un documento desde el dashboard, se llama a limpiar_cache()
# para que el modelo use el contenido actualizado.

@lru_cache(maxsize=100)
def generar_respuesta_cached(pregunta: str, site_id: str) -> str:
    return generar_respuesta(pregunta, site_id)


def limpiar_cache():
    """Limpia el caché de respuestas. Llamar después de recargar documentos."""
    generar_respuesta_cached.cache_clear()
    logger.info("Caché de respuestas limpiado")


def obtener_estadisticas_cache() -> dict:
    """Retorna métricas de uso del caché."""
    info = generar_respuesta_cached.cache_info()
    total = info.hits + info.misses
    return {
        "hits":     info.hits,
        "misses":   info.misses,
        "maxsize":  info.maxsize,
        "currsize": info.currsize,
        "hit_rate": f"{(info.hits / total * 100):.2f}%" if total > 0 else "0%"
    }