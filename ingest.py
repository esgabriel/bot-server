import os
import shutil
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

CHROMA_PATH = "./data/chroma"
FILE_PATH = "docs/conocimiento.pdf"
SITE_ID_ACTUAL = "sitio_demo" 

def main():
    if not os.path.exists(FILE_PATH):
        print(f"No encuentro el archivo {FILE_PATH}. Revisa la carpeta docs/")
        return

    print(f"Cargando {FILE_PATH} para el sitio: '{SITE_ID_ACTUAL}'...")
    loader = PyPDFLoader(FILE_PATH)
    docs = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = text_splitter.split_documents(docs)

    print("Etiquetando documentos...")
    for chunk in chunks:
        chunk.metadata["site_id"] = SITE_ID_ACTUAL
        
    print("Guardando en ChromaDB...")
    
    Chroma.from_documents(
        documents=chunks, 
        embedding=OpenAIEmbeddings(), 
        persist_directory=CHROMA_PATH
    )
    
    print(f"Se guardaron {len(chunks)} fragmentos etiquetados para '{SITE_ID_ACTUAL}'.")

if __name__ == "__main__":
    main()