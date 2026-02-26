"""
Funciones auxiliares para el panel de administración
"""

from dotenv import load_dotenv
import os
from pathlib import Path
from typing import List, Dict
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
import streamlit as st

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

from config import (
    DOCS_DIR,
    CHROMA_DIR,
    COLLECTION_NAME,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    MAX_FILE_SIZE_MB,
    ALLOWED_EXTENSIONS
)


# Importación del caché de rag_service para invalidarlo tras recargar docs.
# El caché del API se limpiará en el próximo reinicio del contenedor.
def _try_limpiar_cache():
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from app.services.rag_service import limpiar_cache
        limpiar_cache()
    except Exception:
        pass


def validate_pdf(uploaded_file) -> tuple[bool, str]:
    """
    Valida que el archivo sea un PDF válido y no exceda el tamaño máximo.
    """
    file_extension = os.path.splitext(uploaded_file.name)[1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        return False, f"Solo se permiten archivos PDF. Extensión recibida: {file_extension}"

    file_size_mb = uploaded_file.size / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        return False, f"El archivo es demasiado grande ({file_size_mb:.2f} MB). Máximo: {MAX_FILE_SIZE_MB} MB"

    if uploaded_file.size == 0:
        return False, "El archivo está vacío"

    return True, ""


def save_uploaded_file(uploaded_file, site_id: str) -> str:
    """
    Guarda el archivo subido en el directorio de documentos.
    Retorna la ruta completa del archivo guardado.
    """
    docs_path = Path(DOCS_DIR)
    docs_path.mkdir(parents=True, exist_ok=True)

    filename  = f"{site_id}_{uploaded_file.name}"
    file_path = docs_path / filename

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return str(file_path)


def process_pdf(file_path: str, site_id: str) -> int:
    """
    Procesa un PDF y lo agrega a ChromaDB.
    Retorna el número de chunks procesados.
    """
    filename = os.path.basename(file_path)
    
    # Eliminar chunks actuales de ChromaDB
    collection = get_collection()
    if collection:
        results = collection.get(
            where={"$and": [{"source_file": filename}, {"site_id": site_id}]}
        )
        if results and results.get("ids"):
            collection.delete(ids=results["ids"])

    loader    = PyPDFLoader(file_path)
    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len
    )
    chunks = text_splitter.split_documents(documents)

    for chunk in chunks:
        chunk.metadata["site_id"]     = site_id
        chunk.metadata["source_file"] = filename

    embeddings  = OpenAIEmbeddings()
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR
    )
    vectorstore.add_documents(chunks)

    return len(chunks)


def get_chromadb_client():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client


def get_collection():
    client = get_chromadb_client()
    try:
        return client.get_collection(name=COLLECTION_NAME)
    except Exception:
        return None


def get_documents_by_site(site_id: str = None) -> List[Dict]:
    """
    Retorna la lista de documentos únicos, opcionalmente filtrados por site_id.
    """
    collection = get_collection()
    if not collection:
        return []

    try:
        results = collection.get(include=["metadatas"])

        if not results or not results.get("metadatas"):
            return []

        documents    = []
        seen_sources = set()

        for metadata in results["metadatas"]:
            source      = metadata.get("source_file", "")
            doc_site_id = metadata.get("site_id", "")

            if source == "__placeholder__":
                continue

            if site_id and doc_site_id != site_id:
                continue

            key = f"{source}_{doc_site_id}"
            if key in seen_sources:
                continue

            seen_sources.add(key)
            documents.append({"filename": source, "site_id": doc_site_id})

        return documents

    except Exception as e:
        st.error(f"Error al obtener documentos: {str(e)}")
        return []


def delete_document(filename: str, site_id: str) -> bool:
    """
    Elimina un documento de ChromaDB y del filesystem.
    """
    try:
        collection = get_collection()
        if not collection:
            return False

        results = collection.get(
            where={"$and": [{"source_file": filename}, {"site_id": site_id}]}
        )

        if results and results.get("ids"):
            collection.delete(ids=results["ids"])

        file_path = Path(DOCS_DIR) / filename
        if file_path.exists():
            file_path.unlink()

        return True

    except Exception as e:
        st.error(f"Error al eliminar documento: {str(e)}")
        return False


def get_statistics() -> Dict:
    """
    Retorna estadísticas de documentos y chunks cargados en ChromaDB.
    """
    collection = get_collection()
    if not collection:
        return {"total_documents": 0, "total_chunks": 0, "documents_by_site": {}}

    try:
        results = collection.get(include=["metadatas"])

        if not results or not results.get("metadatas"):
            return {"total_documents": 0, "total_chunks": 0, "documents_by_site": {}}

        unique_docs  = set()
        docs_by_site = {}

        # Ajuste para contabilizar solo chunks reales (no placeholders)
        real_chunks_count = 0

        for metadata in results["metadatas"]:
            source  = metadata.get("source_file", "")
            site_id = metadata.get("site_id", "")

            if source == "__placeholder__":
                continue

            real_chunks_count += 1
            unique_docs.add((source, site_id))

            if site_id not in docs_by_site:
                docs_by_site[site_id] = set()
            docs_by_site[site_id].add(source)

        return {
            "total_documents":  len(unique_docs),
            "total_chunks":     real_chunks_count,
            "documents_by_site": {k: len(v) for k, v in docs_by_site.items()}
        }

    except Exception as e:
        st.error(f"Error al obtener estadísticas: {str(e)}")
        return {"total_documents": 0, "total_chunks": 0, "documents_by_site": {}}


def reload_document(filename: str, site_id: str) -> tuple[bool, str]:
    """
    Recarga un documento: lo elimina de ChromaDB y lo vuelve a procesar.
    Invalida el caché de respuestas de rag_service al finalizar.
    """
    if filename == "__placeholder__":
        return False, "No se puede recargar un placeholder"
        
    try:
        file_path = Path(DOCS_DIR) / filename

        if not file_path.exists():
            return False, "El archivo no existe en el sistema de archivos"

        # Eliminar chunks actuales de ChromaDB
        collection = get_collection()
        if collection:
            results = collection.get(
                where={"$and": [{"source_file": filename}, {"site_id": site_id}]}
            )
            if results and results.get("ids"):
                collection.delete(ids=results["ids"])

        # Reprocesar el documento
        chunks = process_pdf(str(file_path), site_id)

        # Invalidar el caché de respuestas para que el API use el contenido nuevo.
        # Sin esto, las preguntas cacheadas seguirían devolviendo respuestas viejas
        _try_limpiar_cache()

        return True, f"Documento recargado exitosamente ({chunks} chunks procesados)"

    except Exception as e:
        return False, f"Error al recargar documento: {str(e)}"


def get_all_site_ids() -> List[str]:
    """
    Retorna la lista de todos los site_ids únicos registrados en ChromaDB,
    incluyendo aquellos creados vacíos (sin documentos).
    """
    collection = get_collection()
    if not collection:
        return []

    try:
        results = collection.get(include=["metadatas"])
        if not results or not results.get("metadatas"):
            return []

        site_ids = set()
        for metadata in results["metadatas"]:
            site_id = metadata.get("site_id")
            if site_id:
                site_ids.add(site_id)
        
        return sorted(list(site_ids))
    except Exception as e:
        st.error(f"Error al obtener site_ids: {str(e)}")
        return []


def add_site_id(site_id: str) -> bool:
    """
    Registra un site_id nuevo en ChromaDB insertando un documento dummy.
    Retorna True si se creó, False si ya existía.
    """
    existing_site_ids = get_all_site_ids()
    if site_id in existing_site_ids:
        return False
        
    try:
        from langchain_core.documents import Document
        
        # Insertar placeholder
        placeholder_id = f"placeholder_{site_id}"
        chunks = [Document(page_content="", metadata={"site_id": site_id, "source_file": "__placeholder__"})]
        
        embeddings = OpenAIEmbeddings()
        vectorstore = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=CHROMA_DIR
        )
        
        vectorstore.add_documents(chunks, ids=[placeholder_id])
        return True
    except Exception as e:
        st.error(f"Error al crear site_id: {str(e)}")
        return False


def delete_site_id(site_id: str) -> tuple[bool, str]:
    """
    Elimina todos los chunks asociados a ese site_id en ChromaDB (incluyendo el placeholder). 
    También elimina los archivos físicos del directorio DOCS_DIR que empiecen con {site_id}_.
    Retorna (True, mensaje) o (False, mensaje_error).
    """
    collection = get_collection()
    if not collection:
        return False, "No se pudo conectar a ChromaDB"

    try:
        # Eliminar de ChromaDB
        results = collection.get(where={"site_id": site_id})
        if results and results.get("ids"):
            collection.delete(ids=results["ids"])

        # Eliminar archivos físicos
        docs_path = Path(DOCS_DIR)
        if docs_path.exists():
            for file_path in docs_path.glob(f"{site_id}_*"):
                if file_path.is_file():
                    try:
                        file_path.unlink()
                    except Exception as e:
                        pass

        return True, f"Sitio {site_id} y sus documentos fueron eliminados correctamente."
    except Exception as e:
        return False, f"Error al eliminar site_id: {str(e)}"


def site_id_has_documents(site_id: str) -> bool:
    """
    Retorna True si el site_id tiene chunks reales (excluyendo el placeholder __placeholder__).
    """
    collection = get_collection()
    if not collection:
        return False

    try:
        results = collection.get(
            where={"$and": [{"site_id": site_id}, {"source_file": {"$ne": "__placeholder__"}}]}
        )
        if results and results.get("ids") and len(results["ids"]) > 0:
            return True
        return False
    except Exception:
        return False