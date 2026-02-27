"""
Sistema de autenticación para el panel de administración.
Maneja login, logout y persistencia de sesión mediante cookies encriptadas con JWT.
"""
import os
from datetime import datetime
import jwt as pyjwt
import streamlit as st
import streamlit_authenticator as stauth
from dotenv import load_dotenv
from config import USERS

load_dotenv()

COOKIE_NAME = "dashboard_cookie"
COOKIE_KEY = os.getenv("DASHBOARD_COOKIE_KEY", "default-insecure-key")

def get_authenticator():
    """
    Instancia el autenticador en st.session_state para reutilizarlo durante
    el mismo run de Streamlit (evita duplicar el CookieManager).
    """
    if "authenticator" not in st.session_state:
        st.session_state["authenticator"] = stauth.Authenticate(
            USERS,
            COOKIE_NAME,
            COOKIE_KEY,
            cookie_expiry_days=7
        )
    return st.session_state["authenticator"]

def _restore_session_from_cookie():
    """
    Lee la cookie JWT directamente desde st.context.cookies (headers HTTP)
    y restaura el session_state si la cookie es válida.

    Esto corrige un bug conocido en streamlit-authenticator 0.3.3 donde
    extra_streamlit_components.CookieManager no devuelve la cookie en el
    primer run después de un hard-refresh del navegador.
    """
    # Si ya está autenticado, no hacer nada
    if st.session_state.get("authentication_status"):
        return

    # Si el usuario acaba de cerrar sesión, no restaurar desde la cookie
    if st.session_state.get("logout"):
        return

    try:
        token = st.context.cookies.get(COOKIE_NAME)
        if not token:
            return

        # Decodificar el JWT con la misma clave que usa streamlit-authenticator
        payload = pyjwt.decode(token, COOKIE_KEY, algorithms=["HS256"])

        # Validar que no haya expirado
        exp_date = payload.get("exp_date", 0)
        if exp_date <= datetime.now().timestamp():
            return

        # Validar que el username exista en USERS
        username = payload.get("username", "")
        if username not in USERS.get("usernames", {}):
            return

        # Restaurar session_state — el usuario queda autenticado
        st.session_state["authentication_status"] = True
        st.session_state["username"] = username
        st.session_state["name"] = USERS["usernames"][username].get("name", username)
        st.session_state["logout"] = False
    except Exception:
        # Cookie inválida o corrupta — ignorar, se mostrará el login normal
        pass

def check_password():
    """
    Verifica las credenciales del usuario y maneja el estado de autenticación.
    Soporta autenticación por cookie (sesión persistente) usando JWT firmadas.
    Retorna True si el usuario está autenticado, False en caso contrario.
    """
    # Intentar restaurar sesión desde la cookie JWT (workaround para stauth 0.3.3)
    _restore_session_from_cookie()

    authenticator = get_authenticator()
    
    # Si ya restauramos la sesión desde la cookie, no mostrar el formulario de login
    if st.session_state.get("authentication_status"):
        return True

    # El método login maneja el formulario y la actualización de sesión
    try:
        authenticator.login()
    except Exception as e:
        st.error(str(e))
    
    if st.session_state.get("authentication_status"):
        return True
    elif st.session_state.get("authentication_status") is False:
        st.error("Usuario o contraseña incorrectos")
        return False
    elif st.session_state.get("authentication_status") is None:
        return False
        
    return False

def init_session_state():
    """
    Inicializa las variables de sesión con valores por defecto si es necesario.
    """
    pass

def get_current_user():
    """
    Retorna el nombre del usuario (username) actualmente autenticado, o None si no hay sesión activa.
    """
    return st.session_state.get("username", None)