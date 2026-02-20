from fastapi import APIRouter, HTTPException
from app.schemas.chat import PreguntaUsuario, RespuestaBot
from app.services.rag_service import generar_respuesta
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/chat", response_model=RespuestaBot)
def chat_endpoint(pregunta: PreguntaUsuario):
    try:
        texto_respuesta = generar_respuesta(
            pregunta=pregunta.texto, 
            site_id=pregunta.site_id
        )
        
        return RespuestaBot(respuesta=texto_respuesta)
        
    except Exception as e:
        logger.error(f"Error en endpoint /chat: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno")