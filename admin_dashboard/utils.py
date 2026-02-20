"""
Funciones auxiliares para el panel de administración
"""

from dotenv import load_dotenv
import os
import sys
from pathlib import Path
from typing import List, Dict
import chromadb
from chromadb.config import Settings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
import streamlit as st

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Importar configuración
from config import (
    DOCS_DIR, 
    CHROMA_DIR, 
    COLLECTION_NAME, 
    CHUNK_SIZE, 
    CHUNK_OVERLAP,
    MAX_FILE_SIZE_MB,
    ALLOWED_EXTENSIONS
)


def validate_pdf(uploaded_file) -> tuple[bool, str]:
    """
    Valida que el archivo sea un PDF válido
    
    Args:
        uploaded_file: Archivo subido desde Streamlit
        
    Returns:
        tuple: (es_valido, mensaje_error)
    """
    # Verificar extensión
    file_extension = os.path.splitext(uploaded_file.name)[1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        return False, f"Solo se permiten archivos PDF. Extensión recibida: {file_extension}"
    
    # Verificar tamaño
    file_size_mb = uploaded_file.size / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        return False, f"El archivo es demasiado grande ({file_size_mb:.2f} MB). Máximo permitido: {MAX_FILE_SIZE_MB} MB"
    
    # Verificar que no esté vacío
    if uploaded_file.size == 0:
        return False, "El archivo está vacío"
    
    return True, ""


def save_uploaded_file(uploaded_file, site_id: str) -> str:
    """
    Guarda el archivo subido en el directorio de documentos
    
    Args:
        uploaded_file: Archivo subido desde Streamlit
        site_id: ID del sitio al que pertenece el documento
        
    Returns:
        str: Ruta completa del archivo guardado
    """
    # Crear directorio si no existe
    docs_path = Path(DOCS_DIR)
    docs_path.mkdir(parents=True, exist_ok=True)
    
    # Generar nombre de archivo
    filename = f"{site_id}_{uploaded_file.name}"
    file_path = docs_path / filename
    
    # Guardar archivo
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return str(file_path)


def process_pdf(file_path: str, site_id: str) -> int:
    """
    Procesa un PDF y lo agrega a ChromaDB
    
    Args:
        file_path: Ruta del archivo PDF
        site_id: ID del sitio al que pertenece
        
    Returns:
        int: Número de chunks procesados
    """
    # Cargar PDF
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    
    # Dividir en chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len
    )
    chunks = text_splitter.split_documents(documents)
    
    # Agregar metadatos
    for chunk in chunks:
        chunk.metadata["site_id"] = site_id
        chunk.metadata["source_file"] = os.path.basename(file_path)
    
    # Obtener embeddings
    embeddings = OpenAIEmbeddings()
    
    # Agregar a ChromaDB
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR
    )
    
    vectorstore.add_documents(chunks)

    print("Colección:", COLLECTION_NAME)
    print("Directorio:", CHROMA_DIR)
    print("Total documentos en colección:", vectorstore._collection.count())

    
    return len(chunks)


def get_chromadb_client():
    """
    Obtiene el cliente de ChromaDB
    
    Returns:
        chromadb.Client: Cliente de ChromaDB
    """
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client


def get_collection():
    """
    Obtiene la colección de ChromaDB
    
    Returns:
        chromadb.Collection: Colección de documentos
    """
    client = get_chromadb_client()
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
        return collection
    except:
        return None


def get_documents_by_site(site_id: str = None) -> List[Dict]:
    """
    Obtiene la lista de documentos, opcionalmente filtrados por site_id
    
    Args:
        site_id: ID del sitio para filtrar (opcional)
        
    Returns:
        List[Dict]: Lista de documentos con sus metadatos
    """
    collection = get_collection()
    if not collection:
        return []
    
    try:
        # Obtener todos los documentos
        results = collection.get(include=["metadatas"])
        
        if not results or not results.get("metadatas"):
            return []
        
        # Procesar resultados
        documents = []
        seen_sources = set()
        
        for metadata in results["metadatas"]:
            source = metadata.get("source_file", "")
            doc_site_id = metadata.get("site_id", "")
            
            # Filtrar por site_id si se especifica
            if site_id and doc_site_id != site_id:
                continue
            
            # Evitar duplicados
            key = f"{source}_{doc_site_id}"
            if key in seen_sources:
                continue
            
            seen_sources.add(key)
            documents.append({
                "filename": source,
                "site_id": doc_site_id
            })
        
        return documents
    except Exception as e:
        st.error(f"Error al obtener documentos: {str(e)}")
        return []


def delete_document(filename: str, site_id: str) -> bool:
    """
    Elimina un documento de ChromaDB y del filesystem
    
    Args:
        filename: Nombre del archivo
        site_id: ID del sitio
    """
    try:
        collection = get_collection()
        if not collection:
            return False
        
        # Obtener IDs de chunks del documento
        results = collection.get(
            where={
                "$and": [
                    {"source_file": filename},
                    {"site_id": site_id}
                ]
            }
        )
        
        if results and results.get("ids"):
            # Eliminar de ChromaDB
            collection.delete(ids=results["ids"])
        
        # Eliminar archivo físico
        file_path = Path(DOCS_DIR) / filename

        if file_path.exists():
            file_path.unlink()
        
        return True
    except Exception as e:
        st.error(f"Error al eliminar documento: {str(e)}")
        return False


def get_statistics() -> Dict:
    """
    Obtiene estadísticas de los documentos cargados
    
    Returns:
        Dict: Diccionario con estadísticas
    """
    collection = get_collection()
    if not collection:
        return {
            "total_documents": 0,
            "total_chunks": 0,
            "documents_by_site": {}
        }
    
    try:
        results = collection.get(include=["metadatas"])
        
        if not results or not results.get("metadatas"):
            return {
                "total_documents": 0,
                "total_chunks": 0,
                "documents_by_site": {}
            }
        
        # Contar documentos únicos
        unique_docs = set()
        docs_by_site = {}
        
        for metadata in results["metadatas"]:
            source = metadata.get("source_file", "")
            site_id = metadata.get("site_id", "")
            
            unique_docs.add((source, site_id))
            
            if site_id not in docs_by_site:
                docs_by_site[site_id] = set()
            docs_by_site[site_id].add(source)
        
        # Convertir sets a conteos
        docs_by_site_count = {k: len(v) for k, v in docs_by_site.items()}
        
        return {
            "total_documents": len(unique_docs),
            "total_chunks": len(results["metadatas"]),
            "documents_by_site": docs_by_site_count
        }
    except Exception as e:
        st.error(f"Error al obtener estadísticas: {str(e)}")
        return {
            "total_documents": 0,
            "total_chunks": 0,
            "documents_by_site": {}
        }


def reload_document(filename: str, site_id: str) -> tuple[bool, str]:
    """
    Recarga un documento (lo elimina y lo vuelve a procesar)
    
    Args:
        filename: Nombre del archivo
        site_id: ID del sitio
    """
    try:
        # Verificar que existe el archivo físico
        file_path = Path(DOCS_DIR) / filename

        if not file_path.exists():
            return False, "El archivo no existe en el sistema"
        
        # Eliminar de ChromaDB
        collection = get_collection()
        if collection:
            results = collection.get(
                where={
                    "$and": [
                        {"source_file": filename},
                        {"site_id": site_id}
                    ]
                }
            )
            
            if results and results.get("ids"):
                collection.delete(ids=results["ids"])
        
        # Reprocesar
        chunks = process_pdf(str(file_path), site_id)
        
        return True, f"Documento recargado exitosamente ({chunks} chunks procesados)"
    except Exception as e:
        return False, f"Error al recargar documento: {str(e)}"
