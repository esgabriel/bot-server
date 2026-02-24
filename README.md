# Quaxar Chatbot Server

API Backend y Panel de Administración para el Chatbot RAG Multi-Sitio de Quaxar. Este proyecto utiliza FastAPI para procesar la lógica del chatbot y servir las peticiones, junto con un Dashboard en Streamlit para gestionar el conocimiento (información de los sitios) en formato PDF.

## 🛠 Pila Tecnológica y Requisitos Previos

El proyecto está diseñado para funcionar de manera unificada mediante **Docker** y **Docker Compose**.

### Tecnologías Principales:
- **Backend API**: Python 3.11, FastAPI, Uvicorn, Pydantic, SlowAPI (Rate Limiting).
- **Dashboard de Administración**: Streamlit.
- **Inteligencia Artificial y RAG**: OpenAI (Modelos GPT y Embeddings), LangChain, ChromaDB (Base de datos vectorial), Tiktoken, PyPDF.
- **Infraestructura**: Docker, Docker Compose.

### Requisitos Previos:
- Docker y Docker Compose instalados en el sistema.
- Una clave de API de OpenAI (API Key).

---

## 🚀 Instalación y Levantamiento del Entorno Local

Instrucciones para inicializar el entorno utilizando Docker Compose:

1. **Clonar el repositorio**.
   Abrir una terminal y ejecutar el siguiente comando para clonar el proyecto desde GitHub:
   ```bash
   git clone https://github.com/quaxar-mexico/quaxar-chatbot-server.git
   ```
   Posteriormente, acceder a la raíz del directorio del proyecto:
   ```bash
   cd quaxar-chatbot-server
   ```

2. **Configurar las Variables de Entorno**.
   Copiar el archivo de ejemplo para crear el archivo `.env`:
   ```bash
   cp env.example .env
   ```
   *En Windows (CMD/PowerShell) es posible utilizar `copy env.example .env`.*

3. **Generar la clave secreta de la API**.
   Abrir el archivo `.env` en un editor de texto e ingresar la `OPENAI_API_KEY`.
   Para mayor seguridad, generar un valor seguro para la clave `API_SECRET_KEY` ejecutando el siguiente comando:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   Copiar el valor generado y pegarlo en los siguientes lugares:
   *   En el archivo `.env` del servidor (asignado a `API_SECRET_KEY`).
   *   En la configuración del plugin de WordPress correspondiente, para que ambos sistemas puedan autenticarse.

4. **Levantar los contenedores con Docker Compose**.
   Ejecutar el siguiente comando para construir y arrancar los servicios en segundo plano:
   ```bash
   docker-compose up -d --build
   ```

5. **Acceder a los Servicios**.
   - **API FastAPI**: [http://localhost:8000](http://localhost:8000) (Documentación Swagger disponible en `/docs`).
   - **Dashboard (Streamlit)**: [http://localhost:8501](http://localhost:8501).

---

## ⚙️ Variables de Entorno

A continuación, se describen las variables de entorno utilizadas en el proyecto basándose en el archivo `env.example` y la lógica de la aplicación:

| Variable | Descripción | Valor por Defecto |
|---|---|---|
| `OPENAI_API_KEY` | Clave de API proporcionada por OpenAI. **(Requerido)** | *Ninguno* |
| `MODEL_NAME` | Modelo de OpenAI que utilizará el Chatbot (ej. `gpt-4` o `gpt-3.5-turbo`). | `gpt-3.5-turbo` |
| `TEMPERATURE` | Temperatura de las respuestas. `0.0` se recomienda para atención al cliente por su determinismo. | `0.0` |
| `API_SECRET_KEY` | Clave secreta enviada en el header `X-API-Key` por los clientes (e.g. plugin WordPress) para autenticarse. **(Requerido)** | *Ninguno* |
| `CORS_ORIGINS` | Lista JSON que define los dominios permitidos para consumir la API. Ej. `["https://sitio-ejemplo.com"]`. | `["https://tu-sitio-wordpress.com"]` |
| `CHROMA_DB_DIR` | Ruta del directorio donde ChromaDB persiste la base de datos de vectores. | `./data/chroma` |
| `COLLECTION_NAME` | Nombre de la colección en ChromaDB. Debe concordar en API, Dashboard y script local. | `documentos_chatbot` |
| `TOP_K_RESULTS` | Número máximo de fragmentos (chunks) recuperados por consulta RAG. | `5` |
| `CHUNK_SIZE` | Tamaño en caracteres de cada fragmento al procesar los archivos PDF. | `1000` |
| `CHUNK_OVERLAP` | Superposición en caracteres entre un fragmento y otro, para no perder contexto. | `200` |
| `LOG_LEVEL` | Nivel de logs de la aplicación. Usar `DEBUG` para desarrollo, `INFO` para producción. | `INFO` |

---

## 🏛 Resumen de la Arquitectura

### Estructura de Directorios Clave
- **`app/`**: Contiene la lógica principal del Backend API (FastAPI). Gestiona rutas (`app/api`), conexión a bases de datos vectoriales (`app/db`), lógica de negocio (`app/services`), esquemas Pydantic y configuración.
- **`admin_dashboard/`**: Contiene la lógica del Dashboard construido en Streamlit para la gestión visual e interactiva de los PDFs por sitio.
- **`data/`**: Volumen compartido y persistente usado por ambos contenedores para guardar subidas de archivos temporales y almacenar nativamente la base de datos de persistencia vectorial (`ChromaDB`).
- **`docs/`** y **`logs/`**: Directorios utilizados para monturas persistentes de documentos estáticos/manuales y los registros de actividad, respectivamente.
- **`ingest.py`**: Script de utilidad para la ingesta manual de documentos (`docs/conocimiento.pdf`) a la base de datos por consola, si no se desea utilizar el Dashboard.

### Flujo de Datos y Procesamiento
1. **Peticiones HTTP (API)**:
   - El contenedor **API** atiende peticiones en el puerto `8000`. 
   - Las solicitudes entrantes primero pasan por una capa de seguridad donde se evalúan las reglas de **CORS** (`CORS_ORIGINS`) y la protección de abusos (Rate Limiting mediado por `SlowAPI`).
   - Las conexiones también corroboran el secreto `API_SECRET_KEY` antes de poder interactuar con los *endpoints* del RAG.
   - FastAPI utiliza dependencias instanciando la base ChromaDB al arrancar. Si el servicio de base de vectores no pudiese inicializarse, la API detendrá su inicio emitiendo fallos tempranos críticos.

2. **Administración de Conocimiento (Dashboard)**:
   - Los moderadores o administradores acceden al contenedor **Dashboard** a través del puerto `8501`.
   - Tras autenticarse en la plataforma, es posible subir documentos PDF indicando un identificador de sitio (`Site ID`).
   - Los documentos pasan por una validación estricta y se procesan automáticamente dividiendo el texto mediante `RecursiveCharacterTextSplitter`. El tamaño y cruce de la división dependen de `CHUNK_SIZE` y `CHUNK_OVERLAP`.
   - Se calculan los embeddings consumiendo `OpenAIEmbeddings` y se almacenan en ChromaDB categorizados lógicamente por el atributo de metadata `site_id`, lo que facilita la administración de un chatbot de "Múltiples Sitios" de forma transparente en la colección única dictada por `COLLECTION_NAME`.

3. **Inferencia (RAG Flow)**:
   - Cuando la API recibe una consulta para un determinado `Site ID`, genera el embedding de la pregunta mediante OpenAI y posteriormente realiza una recuperación semántica (`Similarity Search` o `Maximal Marginal Relevance`), devolviendo desde ChromaDB únicamente hasta los `TOP_K_RESULTS` fragmentos pertinentes vinculados a dicho metadata `site_id`.
   - Los fragmentos extraídos se ensamblan junto con el Prompt primario y se inyectan como contexto amplificado al LLM (`MODEL_NAME`) instanciado también bajo LangChain, permitiendo redactar una respuesta congruente basada puramente en la fuente técnica de los documentos cargados previamente.
