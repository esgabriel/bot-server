"""
Script de ingesta manual de documentos PDF a ChromaDB.

Importante: La colección usada aquí DEBE coincidir con la definida
en app/db/chroma.py (COLLECTION_NAME = "documentos_chatbot").
"""

import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

# CONFIGURACIÓN — ajustar estas variables antes de ejecutar
CHROMA_PATH      = "./data/chroma"
COLLECTION_NAME  = "documentos_chatbot"   # ← Debe coincidir con app/db/chroma.py
FILE_PATH        = "docs/conocimiento.pdf"
SITE_ID_ACTUAL   = "sitio_demo"


def main():
    # Verificar que existe el archivo
    if not os.path.exists(FILE_PATH):
        print(f"No se encontró el archivo: {FILE_PATH}")
        print("Verifica que el PDF esté en la carpeta docs/")
        return

    # Verificar que existe la API key
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY no está configurada en el archivo .env")
        return

    print(f"Cargando: {FILE_PATH}")
    print(f"Site ID:  {SITE_ID_ACTUAL}")
    print(f"Colección: {COLLECTION_NAME}")
    print()

    # Cargar PDF
    loader = PyPDFLoader(FILE_PATH)
    docs   = loader.load()
    print(f"Páginas cargadas: {len(docs)}")

    # Dividir en chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = text_splitter.split_documents(docs)
    print(f"Chunks generados: {len(chunks)}")

    # Etiquetar con el site_id
    for chunk in chunks:
        chunk.metadata["site_id"]     = SITE_ID_ACTUAL
        chunk.metadata["source_file"] = os.path.basename(FILE_PATH)

    # Guardar en ChromaDB
    print("\nGuardando en ChromaDB...")
    Chroma.from_documents(
        documents=chunks,
        embedding=OpenAIEmbeddings(),
        persist_directory=CHROMA_PATH,
        collection_name=COLLECTION_NAME,
    )

    print(f"\nListo. {len(chunks)} chunks guardados para el sitio '{SITE_ID_ACTUAL}'.")
    print(f"Directorio: {CHROMA_PATH}")


if __name__ == "__main__":
    main()