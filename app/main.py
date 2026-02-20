from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logger import setup_logging
from app.api.routes import router as chat_router
import logging


setup_logging(log_level=settings.LOG_LEVEL) 

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION
)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix=settings.API_V1_PREFIX)

# Inicio
@app.on_event("startup")
async def startup_event():
    logger.info(f"Iniciando {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f"Entorno: {settings.LOG_LEVEL}")
    logger.info(f"Modelo IA: {settings.MODEL_NAME}")

# Cierre
@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Cerrando {settings.PROJECT_NAME}")

@app.get("/")
def root():
    logger.debug("Health check endpoint accessed")
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs"
    }