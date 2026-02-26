"""
Sistema de autenticación para el panel de administración.
Maneja login, logout y persistencia de sesión mediante cookies encriptadas con JWT.
"""
import os
import streamlit as st
import streamlit_authenticator as stauth
from dotenv import load_dotenv
from config import USERS

load_dotenv()

def get_authenticator():
    """
    Instancia el autenticador en st.session_state para no usar variables globales.
    """
    if "authenticator" not in st.session_state:
        cookie_key = os.getenv("DASHBOARD_COOKIE_KEY", "default-insecure-key")
        st.session_state["authenticator"] = stauth.Authenticate(
            USERS,
            "dashboard_cookie",
            cookie_key,
            cookie_expiry_days=7
        )
    return st.session_state["authenticator"]

def check_password():
    """
    Verifica las credenciales del usuario y maneja el estado de autenticación.
    Soporta autenticación por cookie (sesión persistente) usando JWT firmadas.
    Retorna True si el usuario está autenticado, False en caso contrario.
    """
    authenticator = get_authenticator()
    
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