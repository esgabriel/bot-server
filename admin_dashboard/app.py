"""
Panel de Administración - Chatbot Quaxar IA
Aplicación Streamlit para gestionar documentos PDF
"""

import streamlit as st
import os
from pathlib import Path
import base64

import re

# Importar módulos locales
from auth import check_password, get_authenticator, get_current_user, init_session_state
from config import APP_TITLE, APP_DESCRIPTION, DOCS_DIR
from utils import (
    validate_pdf,
    save_uploaded_file,
    process_pdf,
    get_documents_by_site,
    delete_document,
    get_statistics,
    get_all_site_ids,
    add_site_id,
    delete_site_id,
    site_id_has_documents,
    get_cors_origins,
    add_cors_origin,
    delete_cors_origin
)

# Configuración de la página
st.set_page_config(
    page_title="Admin Panel - Chatbot Quaxar",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar estado de sesión
init_session_state()

st.markdown("""
    <style>
        #MainMenu {display: none;}
        .stDeployButton {display: none;}
        footer {display: none;}
    </style>
""", unsafe_allow_html=True)

def show_pdf_preview(pdf_file):
    """
    Muestra un preview del PDF
    """
    base64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)
    pdf_file.seek(0)  # Reset file pointer


def dashboard_page():
    """
    Página de dashboard con estadísticas
    """
    st.title("Dashboard")
    st.markdown("---")
    
    # Obtener estadísticas
    stats = get_statistics()
    
    # Mostrar métricas principales
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Total de Documentos",
            value=stats["total_documents"]
        )
    
    with col2:
        st.metric(
            label="Total de Chunks",
            value=stats["total_chunks"],
            help="Un 'chunk' es un fragmento de texto en el que se dividen tus documentos PDF. Mientras más chunks, más detallada es la base de conocimiento para el modelo de IA."
        )
    
    with col3:
        st.metric(
            label="Sitios Activos",
            value=len(stats["documents_by_site"])
        )
    
    # Mostrar documentos por sitio
    if stats["documents_by_site"]:
        st.markdown("### Documentos por Sitio")
        
        for site_id, count in sorted(stats["documents_by_site"].items()):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{site_id}**")
            with col2:
                st.write(f"{count} documento(s)")
    else:
        st.info("No hay documentos cargados aún. Ve a 'Subir Documentos' para comenzar.")


def upload_single_page():
    """
    Página para subir un solo documento (Con estado de éxito controlado)
    """
    st.title("Subir Documento")
    st.markdown("---")
    
    # Gestión del estado de la vista
    if "upload_success" not in st.session_state:
        st.session_state["upload_success"] = False

    # Vista de éxito (Se muestra después de subir un PDF)
    if st.session_state["upload_success"]:
        st.success("¡Documento procesado y guardado exitosamente!")
        st.balloons()
        
        st.info("El archivo ha sido añadido a la base de conocimiento del chatbot.")
        
        st.markdown("### ¿Qué deseas hacer ahora?")
        
        # Botón para subir otro documento
        if st.button("Subir otro documento", type="primary"):
            st.session_state["upload_success"] = False
            st.rerun()
            
    # Vista de formulario para subir documento
    else:
        # Selector de Site ID
        st.subheader("Selecciona el Site ID")
        
        site_id_option = st.selectbox(
            "Site ID",
            options=["Seleccionar..."] + get_all_site_ids(),
            key="site_id_selector"
        )
        
        if site_id_option != "Seleccionar...":
            site_id = site_id_option
        else:
            site_id = None
        
        # Subir archivo
        st.subheader("Selecciona el archivo PDF")
        
        uploaded_file = st.file_uploader(
            "Selecciona un archivo PDF",
            type=["pdf"],
            key="single_file_uploader"
        )
        
        # Preview
        if uploaded_file is not None:
            st.subheader("Preview del documento")
            with st.expander("Ver preview del PDF", expanded=False):
                show_pdf_preview(uploaded_file)
        
        # Botón para procesar
        st.markdown("---")
        
        if st.button("Subir y Procesar", type="primary", use_container_width=True):
            if not site_id:
                st.error("Debes seleccionar o escribir un Site ID")
                return
            
            if not uploaded_file:
                st.error("Debes seleccionar un archivo")
                return
            
            # Validar archivo
            is_valid, error_msg = validate_pdf(uploaded_file)
            if not is_valid:
                st.error(f"{error_msg}")
                return
            
            # Procesar archivo
            with st.spinner("Procesando documento..."):
                try:
                    # Guardar archivo
                    file_path = save_uploaded_file(uploaded_file, site_id)
                    
                    # Procesar con barra de progreso
                    progress_bar = st.progress(0, text="Guardando archivo...")
                    progress_bar.progress(25, text="Cargando PDF...")
                    
                    # Procesar
                    chunks = process_pdf(file_path, site_id)
                    
                    progress_bar.progress(100, text="¡Completado!")
                    
                    # Actualizar estado de éxito para mostrar la vista de éxito
                    st.session_state["upload_success"] = True
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error al procesar documento: {str(e)}")


def upload_multiple_page():
    """
    Página para subir múltiples documentos
    """
    st.title("Subir Múltiples Documentos")
    st.markdown("---")
    
    # Selector de Site ID
    st.subheader("Selecciona el Site ID")
    
    site_id_option = st.selectbox(
        "Site ID",
        options=["Seleccionar..."] + get_all_site_ids(),
        key="multi_site_id_selector"
    )
    
    if site_id_option != "Seleccionar...":
        site_id = site_id_option
    else:
        site_id = None
    
    # Subir archivos
    st.subheader("Selecciona los archivos PDF")
    
    uploaded_files = st.file_uploader(
        "Selecciona uno o más archivos PDF",
        type=["pdf"],
        accept_multiple_files=True,
        key="multiple_files_uploader"
    )
    
    if uploaded_files:
        st.info(f"{len(uploaded_files)} archivo(s) seleccionado(s)")
    
    # Botón para procesar
    st.markdown("---")
    
    if st.button("Subir y Procesar Todos", type="primary", use_container_width=True):
        if not site_id:
            st.error("Debes seleccionar o escribir un Site ID")
            return
        
        if not uploaded_files:
            st.error("Debes seleccionar al menos un archivo")
            return
        
        # Procesar archivos
        total_files = len(uploaded_files)
        success_count = 0
        error_count = 0
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"Procesando {idx + 1}/{total_files}: {uploaded_file.name}")
            
            # Validar
            is_valid, error_msg = validate_pdf(uploaded_file)
            if not is_valid:
                st.warning(f" {uploaded_file.name}: {error_msg}")
                error_count += 1
                progress_bar.progress((idx + 1) / total_files)
                continue
            
            try:
                # Guardar y procesar
                file_path = save_uploaded_file(uploaded_file, site_id)
                chunks = process_pdf(file_path, site_id)
                
                st.success(f" {uploaded_file.name}: {chunks} chunks procesados")
                success_count += 1
                
            except Exception as e:
                st.error(f" {uploaded_file.name}: {str(e)}")
                error_count += 1
            
            progress_bar.progress((idx + 1) / total_files)
        
        # Resumen
        st.markdown("---")
        st.subheader("Resumen")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total", total_files)
        with col2:
            st.metric("Exitosos", success_count)
        with col3:
            st.metric("Errores", error_count)
        
        if success_count > 0:
            st.balloons()


def documents_list_page():
    """
    Página para ver, filtrar y gestionar documentos
    """
    st.title("Lista de Documentos")
    st.markdown("---")
    
    # Filtros
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_term = st.text_input(
            "Buscar por nombre de archivo",
            key="search_documents"
        )
    
    with col2:
        filter_site = st.selectbox(
            "Filtrar por Site ID",
            options=["Todos"] + get_all_site_ids(),
            key="filter_site_id"
        )
    
    # Obtener documentos
    if filter_site == "Todos":
        documents = get_documents_by_site()
    else:
        documents = get_documents_by_site(filter_site)
    
    # Aplicar búsqueda
    if search_term:
        documents = [
            doc for doc in documents 
            if search_term.lower() in doc["filename"].lower()
        ]
    
    # Mostrar documentos
    if not documents:
        st.info("No se encontraron documentos")
        return
    
    st.markdown(f"**Total: {len(documents)} documento(s)**")
    st.markdown("---")
    
    # Tabla de documentos
    for idx, doc in enumerate(documents):
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 1, 1])
            
            with col1:
                st.write(f"**{doc['filename']}**")
            
            with col2:
                st.write(f"`{doc['site_id']}`")
                
            file_path = Path(DOCS_DIR) / doc['filename']
            show_preview = False
            
            with col3:
                if st.button("Visualizar", key=f"view_{idx}"):
                    if file_path.exists():
                        show_preview = True
                    else:
                        st.warning("Archivo no disponible para visualizar")
            
            with col4:
                if file_path.exists():
                    with open(file_path, "rb") as f:
                        st.download_button(
                            label="Descargar",
                            data=f,
                            file_name=doc['filename'],
                            mime="application/pdf",
                            key=f"download_{idx}"
                        )
                else:
                    st.warning("Archivo no disponible para descarga")
            
            with col5:
                if st.button("Eliminar", key=f"delete_{idx}"):
                    if delete_document(doc['filename'], doc['site_id']):
                        st.success("Documento eliminado")
                        st.rerun()
                    else:
                        st.error("Error al eliminar")
                        
            if show_preview:
                with st.expander("Preview del PDF", expanded=True):
                    with open(file_path, "rb") as f:
                        show_pdf_preview(f)
            
            st.markdown("---")


def gestionar_site_ids_page():
    """
    Página para gestionar los Site IDs.
    """
    st.title("Gestionar Site IDs")
    st.markdown("---")
    
    # Sección 1: Agregar nuevo Site ID
    st.subheader("Agregar nuevo Site ID")
    
    # Manejar estado en session_state para que 'Enter' lance el callback
    def on_add_site_id():
        sid = st.session_state.get("new_site_id_input", "").strip()
        if not sid:
            st.toast("Debes escribir un nombre.", icon="⚠️")
        elif not re.match(r"^[a-zA-Z0-9_-]+$", sid):
            st.toast("El nombre solo puede contener letras, números, guiones y guiones bajos.", icon="⚠️")
        else:
            success = add_site_id(sid)
            if success:
                st.toast(f"Site ID '{sid}' agregado exitosamente.", icon="✅")
                st.session_state["new_site_id_input"] = "" # Limpiar input
            else:
                st.toast(f"El Site ID '{sid}' ya existe.", icon="⚠️")

    col_input, col_btn = st.columns([3, 1])
    
    with col_input:
        st.text_input(
            "Nombre del nuevo Site ID", 
            key="new_site_id_input", 
            help="Solo letras, números, guiones y guiones bajos (presiona Enter para agregar)",
            on_change=on_add_site_id
        )
        
    with col_btn:
        st.write("") # Espaciado
        st.write("")
        st.button("Agregar", use_container_width=True, on_click=on_add_site_id)
        
    st.markdown("---")
    
    # Sección 2: Site IDs activos
    st.subheader("Site IDs activos")
    
    site_ids = get_all_site_ids()
    if not site_ids:
        st.info("No hay Site IDs registrados.")
        return
        
    for site_id in site_ids:
        with st.container():
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.write(f"**{site_id}**")
            
            docs = get_documents_by_site(site_id)
            doc_count = len([d for d in docs if d["filename"] != "__placeholder__"])
            has_docs = site_id_has_documents(site_id)
            
            with col2:
                st.write(f"{doc_count} documento(s)")
            
            with col3:
                # Si no tiene documentos, eliminamos directo sin confirmación
                if not has_docs:
                    if st.button("Eliminar", key=f"del_{site_id}"):
                        success, msg = delete_site_id(site_id)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                else:
                    # Mostrar botón que triggeréa la confirmación
                    if st.button("Eliminar", key=f"del_request_{site_id}"):
                        st.session_state[f"confirm_del_{site_id}"] = True
            
            # Mostrar UI de confirmación si fue solicitada
            if has_docs and st.session_state.get(f"confirm_del_{site_id}", False):
                st.warning(f"Este site ID tiene {doc_count} documentos. Se eliminarán todos. ¿Confirmas?")
                c1, c2, c3 = st.columns([1, 1, 2])
                with c1:
                    if st.button("Confirmar", key=f"confirm_{site_id}"):
                        success, msg = delete_site_id(site_id)
                        st.session_state[f"confirm_del_{site_id}"] = False
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                with c2:
                    if st.button("Cancelar", key=f"cancel_{site_id}"):
                        st.session_state[f"confirm_del_{site_id}"] = False
                        st.rerun()
                        
            st.markdown("---")


def gestionar_cors_page():
    """
    Página para gestionar los dominios permitidos en CORS.
    """
    st.title("Dominios Permitidos")
    st.markdown("---")

    st.info(
        "Agrega aquí los dominios de los sitios WordPress que consumirán la API del chatbot. "
        "Los cambios se aplican de inmediato sin necesidad de reiniciar el servidor."
    )

    # Sección: Agregar nuevo dominio
    st.subheader("Agregar dominio")

    def on_add_origin():
        origin = st.session_state.get("new_cors_origin_input", "").strip()
        if not origin:
            st.toast("Debes escribir un dominio.", icon="⚠️")
            return
        success, msg = add_cors_origin(origin)
        if success:
            st.toast(msg, icon="✅")
            st.session_state["new_cors_origin_input"] = ""
        else:
            st.toast(msg, icon="⚠️")

    col_input, col_btn = st.columns([3, 1])

    with col_input:
        st.text_input(
            "Dominio",
            key="new_cors_origin_input",
            placeholder="https://mi-sitio-wordpress.com",
            help="Incluye el protocolo (https:// o http://) y sin barra al final.",
            on_change=on_add_origin
        )

    with col_btn:
        st.write("")
        st.write("")
        st.button("Agregar", use_container_width=True, on_click=on_add_origin)

    st.markdown("---")

    # Sección: Dominios activos
    st.subheader("Dominios permitidos")

    origins = get_cors_origins()

    if not origins:
        st.warning("No hay dominios configurados. El chatbot no funcionará en ningún sitio hasta que agregues al menos uno.")
        return

    for origin in origins:
        col1, col2 = st.columns([4, 1])

        with col1:
            st.code(origin)

        with col2:
            if st.button("Eliminar", key=f"del_cors_{origin}"):
                success, msg = delete_cors_origin(origin)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)


def main():
    """
    Función principal de la aplicación
    """
    # Verificar autenticación
    if not check_password():
        st.stop()
    
    # Sidebar con navegación
    with st.sidebar:
        st.title("Admin Panel")
        st.markdown(f"**Usuario:** {get_current_user()}")
        st.markdown("---")
        
        # Menú de navegación
        page = st.radio(
            "Navegación",
            options=[
                "Dashboard",
                "Subir Documento",
                "Subir Múltiples",
                "Lista de Documentos",
                "Gestionar Site IDs",
                "Dominios Permitidos"
            ],
            key="navigation"
        )
        
        st.markdown("---")
        
        # Botón de cerrar sesión
        authenticator = get_authenticator()
        authenticator.logout("Cerrar Sesión", "sidebar")
    
    # Mostrar página seleccionada
    if page == "Dashboard":
        dashboard_page()
    elif page == "Subir Documento":
        upload_single_page()
    elif page == "Subir Múltiples":
        upload_multiple_page()
    elif page == "Lista de Documentos":
        documents_list_page()
    elif page == "Gestionar Site IDs":
        gestionar_site_ids_page()
    elif page == "Dominios Permitidos":
        gestionar_cors_page()


if __name__ == "__main__":
    main()
