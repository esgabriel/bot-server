"""
Archivo de configuración para el panel de administración
"""
import os
from pydantic_settings import BaseSettings

# AUTENTICACIÓN

# Usuarios y hashes de contraseñas (bcrypt)
USERS = {
    "usernames": {
        "quaxaradmin": {
            "name": "Admin",
            "email": "admin@quaxar.com",
            "password": "$2b$12$2Q4Zv.kQFyo3Z5oHkptkh.Ee/PCyQvhCywIsiuMEOgXh4MU56gIau"
        },
        "marketing": {
            "name": "Marketing",
            "email": "marketing@quaxar.com",
            "password": "$2b$12$dxi/UUv69lIv3nDit3hCT.uVwCotBJK42rMCd8J1F3B2vSJ7/vYpK"
        }
    }
}

# SITE IDS PREDEFINIDOS

# Lista de Site IDs disponibles en el dropdown
# Agregar o quitar según los sitios de WordPress
SITE_IDS = [
    "sitio_demo",
    "tienda_online",
    "portal_clientes",
]

# CONFIGURACIÓN DE ARCHIVOS

# Tamaño máximo de archivo (en MB)
MAX_FILE_SIZE_MB = 50

# Extensiones permitidas
ALLOWED_EXTENSIONS = [".pdf"]

# Directorio donde se guardan los documentos
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DOCS_DIR = os.path.join(BASE_DIR, "docs")
CHROMA_DIR = os.path.join(BASE_DIR, "data", "chroma")

# CONFIGURACIÓN DE LA INTERFAZ

# Título de la aplicación
APP_TITLE = "Panel de Administración - Chatbot Quaxar IA"

# Descripción
APP_DESCRIPTION = "Gestiona los documentos PDF que alimentan el conocimiento del chatbot"

# Página de inicio después del login
DEFAULT_PAGE = "Dashboard"

# CONFIGURACIÓN DE CHROMADB

# Nombre de la colección en ChromaDB
COLLECTION_NAME = "documentos_chatbot"

# Chunk size para procesar documentos
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
