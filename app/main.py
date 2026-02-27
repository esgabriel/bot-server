from fastapi import FastAPI, Request
from app.core.config import settings
from app.core.logger import setup_logging
from app.core.limiter import limiter
from app.api.routes import router as chat_router
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import logging
import os
import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


setup_logging(log_level=settings.LOG_LEVEL)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION
)


# Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# CORS dinámico — lee los dominios permitidos desde data/cors_origins.json en cada petición
CORS_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cors_origins.json")

def get_dynamic_cors_origins() -> list:
    """Lee los dominios permitidos desde el archivo JSON en cada petición."""
    try:
        if os.path.exists(CORS_FILE_PATH):
            with open(CORS_FILE_PATH, "r") as f:
                origins = json.load(f)
                return origins if isinstance(origins, list) else []
    except Exception:
        pass
    return []

class DynamicCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        origin = request.headers.get("origin", "")
        allowed_origins = get_dynamic_cors_origins()

        # Manejar preflight OPTIONS
        if request.method == "OPTIONS":
            if origin in allowed_origins:
                response = Response(status_code=200)
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "*"
                return response
            return Response(status_code=400)

        response = await call_next(request)

        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"

        return response

app.add_middleware(DynamicCORSMiddleware)

@app.middleware("http")
async def log_origin(request: Request, call_next):
    logger.info(f"Origin recibido: {request.headers.get('origin', 'ninguno')}")
    return await call_next(request)
    
# Rutas
app.include_router(chat_router, prefix=settings.API_V1_PREFIX)

@app.on_event("startup")
async def startup_event():
    logger.info(f"Iniciando {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f"Log level: {settings.LOG_LEVEL}")
    logger.info(f"Modelo IA: {settings.MODEL_NAME}")
    cors_origins = get_dynamic_cors_origins()
    logger.info(f"CORS dinámico activo. Dominios permitidos: {cors_origins if cors_origins else 'ninguno aún'}")

    # Validar variables críticas al arrancar — falla rápido si falta algo
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY no está configurada en el .env")

    if not settings.API_SECRET_KEY:
        raise RuntimeError("API_SECRET_KEY no está configurada en el .env")

    # Pre-cargar ChromaDB para detectar errores al inicio, no en el primer request
    try:
        from app.db.chroma import get_vector_db
        get_vector_db()
        logger.info("Conexión a ChromaDB verificada correctamente")
    except Exception as e:
        logger.critical(f"No se pudo conectar a ChromaDB al iniciar: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Cerrando {settings.PROJECT_NAME}")



@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/")
def root():
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs"
    }