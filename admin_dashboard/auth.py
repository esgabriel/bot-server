"""
Sistema de autenticación para el panel de administración.
Maneja login, logout y persistencia de sesión mediante cookies encriptadas.
"""
import os
import time
import streamlit as st
import bcrypt
from dotenv import load_dotenv
from streamlit_cookies_controller import CookieController
from datetime import datetime, timedelta
from config import USERS

load_dotenv()

# Controlador de cookies para persistir la sesión entre recargas del navegador
cookie_controller = CookieController()

def check_password():
    """
    Verifica las credenciales del usuario y maneja el estado de autenticación.
    Soporta autenticación por cookie (sesión persistente) y por formulario.
    Retorna True si el usuario está autenticado, False en caso contrario.
    """
    # Si existe una cookie válida, autenticar sin mostrar el formulario
    cookie_username = cookie_controller.get("dashboard_user")
    if cookie_username and cookie_username in USERS:
        st.session_state["authenticated"] = True
        st.session_state["username"] = cookie_username
        return True

    # Si ya se autenticó en esta sesión del navegador, no volver a pedir credenciales
    if st.session_state.get("authenticated", False):
        return True

    # Formulario de inicio de sesión para usuarios no autenticados
    st.title("Inicio de Sesión")
    st.markdown("---")

    with st.form("login_form"):
        username = st.text_input("Usuario", key="username_input")
        password = st.text_input("Contraseña", type="password", key="password_input")
        remember_me = st.checkbox("Mantener sesión iniciada")
        submit = st.form_submit_button("Iniciar Sesión")

        if submit:
            # Validar usuario y contraseña con bcrypt
            if username in USERS:
                stored_hash = USERS[username].encode('utf-8')
                password_bytes = password.encode('utf-8')
                
                if bcrypt.checkpw(password_bytes, stored_hash):
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username

                    # Si el usuario marcó "recordarme", guardar cookie con expiración de 7 días
                    if remember_me:
                        expires = datetime.now() + timedelta(days=7)
                        cookie_controller.set("dashboard_user", username, expires=expires)

                    time.sleep(0.5)
                    st.success("Inicio de sesión exitoso")
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos")
            else:
                st.error("Usuario o contraseña incorrectos")
                return False

    return False


def logout():
    """
    Cierra la sesión del usuario actual.
    Elimina la cookie persistente y limpia el estado de sesión.
    """
    cookie_controller.remove("dashboard_user")

    st.session_state["authenticated"] = False
    st.session_state["username"] = None
    st.rerun()


def get_current_user():
    """
    Retorna el nombre del usuario actualmente autenticado, o None si no hay sesión activa.
    """
    return st.session_state.get("username", None)


def init_session_state():
    """
    Inicializa las variables de sesión con valores por defecto.
    Debe llamarse al inicio de cada página para evitar errores de clave inexistente.
    """
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if "username" not in st.session_state:
        st.session_state["username"] = None