from fastapi import APIRouter, HTTPException, Security, Request, Depends
from fastapi.security import APIKeyHeader
from app.schemas.chat import PreguntaUsuario, RespuestaBot
from app.services.rag_service import generar_respuesta
from app.core.config import settings
from app.core.limiter import limiter
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# Autenticación por API Key
# El plugin de WordPress debe enviar el header: X-API-Key: <clave_secreta>
# La clave se define en API_SECRET_KEY dentro del .env
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(request: Request, api_key: str = Security(api_key_header)):
    # OPTIONS es el preflight de CORS — no lleva API Key, dejarlo pasar
    if request.method == "OPTIONS":
        return None
    if not api_key or api_key != settings.API_SECRET_KEY:
        logger.warning("Request rechazado: API Key inválida o ausente")
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado: API Key inválida o ausente"
        )
    return api_key


# Endpoint principal del chatbot
@router.post("/chat", response_model=RespuestaBot)
@limiter.limit("15/minute")
def chat_endpoint(
    request: Request,
    pregunta: PreguntaUsuario,
    api_key: str = Depends(verify_api_key)
):
    """
    Recibe una pregunta del usuario y retorna una respuesta generada por IA.

    Headers requeridos:
        X-API-Key: <clave definida en API_SECRET_KEY del .env>

    Body:
        texto:   Pregunta del usuario (máx. 1000 caracteres)
        site_id: ID del sitio WordPress (solo letras, números, - y _)
    """
    try:
        texto_respuesta = generar_respuesta(
            pregunta=pregunta.texto,
            site_id=pregunta.site_id
        )
        return RespuestaBot(respuesta=texto_respuesta)

    except ValueError as e:
        logger.warning(f"Parámetros inválidos: {e}")
        raise HTTPException(status_code=422, detail=str(e))

    except ConnectionError as e:
        logger.error(f"Error de conexión en /chat: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Servicio temporalmente no disponible")

    except Exception as e:
        logger.error(f"Error inesperado en /chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")