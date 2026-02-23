from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logger import setup_logging
from app.core.limiter import limiter
from app.api.routes import router as chat_router
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import logging


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


# CORS — solo permite los dominios definidos en CORS_ORIGINS del .env
# En producción NUNCA usar "*". Define los dominios de tus sitios WordPress.
if not settings.CORS_ORIGINS:
    logger.warning(
        "CORS_ORIGINS está vacío. No se aceptarán requests desde ningún origen. "
        "Define los dominios permitidos en el .env."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    logger.info(f"CORS permitido para: {settings.CORS_ORIGINS}")

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