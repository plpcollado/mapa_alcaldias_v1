"""
Módulo de autenticación para el dashboard de Streamlit
Maneja login, sesiones y control de acceso
"""

import streamlit as st
import hashlib


def hash_password(password: str) -> str:
    """
    Convierte una contraseña en su hash SHA256
    
    Args:
        password: Contraseña en texto plano
        
    Returns:
        Hash SHA256 de la contraseña
    """
    return hashlib.sha256(password.encode()).hexdigest()


def verificar_credenciales(username: str, password: str, usuarios: dict) -> tuple:
    """
    Verifica si las credenciales son válidas
    
    Args:
        username: Nombre de usuario
        password: Contraseña en texto plano
        usuarios: Diccionario con usuarios y sus configuraciones
        
    Returns:
        tuple: (autenticado: bool, tipo_usuario: str, nombre_usuario: str)
    """
    if username in usuarios:
        password_hash = hash_password(password)
        if usuarios[username]["password_hash"] == password_hash:
            return True, usuarios[username]["tipo"], username
    return False, None, None


def inicializar_sesion():
    """
    Inicializa las variables de sesión necesarias
    """
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_type" not in st.session_state:
        st.session_state.user_type = None
    if "username" not in st.session_state:
        st.session_state.username = None


def login(username: str, password: str, usuarios: dict) -> bool:
    """
    Realiza el proceso de login
    
    Args:
        username: Nombre de usuario
        password: Contraseña
        usuarios: Diccionario de usuarios
        
    Returns:
        bool: True si el login fue exitoso
    """
    autenticado, tipo_usuario, nombre = verificar_credenciales(username, password, usuarios)
    
    if autenticado:
        st.session_state.authenticated = True
        st.session_state.user_type = tipo_usuario
        st.session_state.username = nombre
        return True
    return False


def login_invitado():
    """
    Realiza el login como usuario invitado (sin credenciales)
    """
    st.session_state.authenticated = True
    st.session_state.user_type = "general"
    st.session_state.username = "Invitado"


def logout():
    """
    Cierra la sesión del usuario
    """
    st.session_state.authenticated = False
    st.session_state.user_type = None
    st.session_state.username = None


def requiere_autenticacion(user_types: list = None):
    """
    Verifica que el usuario esté autenticado y tenga el tipo correcto
    Redirige a la página de login si no está autenticado
    
    Args:
        user_types: Lista de tipos de usuario permitidos (None = todos los autenticados)
    """
    if not st.session_state.get("authenticated", False):
        st.warning("⚠️ Debes iniciar sesión para acceder a esta página.")
        st.stop()
    
    if user_types and st.session_state.get("user_type") not in user_types:
        st.error("🚫 No tienes permisos para acceder a esta página.")
        st.stop()


def mostrar_info_usuario_sidebar():
    """
    Muestra el badge del usuario (Admin/Invitado).
    NOTA: Llamar a esta función AL PRINCIPIO del sidebar en el script principal.
    """
    if not st.session_state.get("authenticated", False):
        return

    # Definir etiqueta simplificada
    etiqueta = "Admin" if st.session_state.user_type == "privilegiado" else "Invitado"
    
    st.sidebar.markdown(
        f"""
        <div style="
            background-color: #9F2241; 
            padding: 0.5rem 1rem; 
            border-radius: 20px; 
            color: white; 
            margin-bottom: 1rem;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.9rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            <span style="font-size: 1.1rem;">👤</span>
            <span style="font-weight: 600;">{etiqueta}</span>
        </div>
        """,
        unsafe_allow_html=True
    )


def renderizar_logout_sidebar():
    """
    Renderiza SOLO el botón de logout al final del sidebar (llamar al final de cada página)
    """
    # Spacer visual
    st.sidebar.markdown("---")
    
    # Botón de cerrar sesión
    if st.sidebar.button("Cerrar Sesión", use_container_width=True):
        logout()
        st.rerun()


def pagina_login(usuarios: dict):
    """
    Renderiza la página de login
    
    Args:
        usuarios: Diccionario con las credenciales de usuarios
    """
    
    # CSS personalizado (Mantenemos tu estilo de Tabs y Botones)
    st.markdown(
        """
        <style>
            /* Ocultar sidebar en login */
            [data-testid="stSidebar"] {
                display: none;
            }
            
            /* --- PERSONALIZACIÓN DE TABS (Pestañas) --- */
            
            /* 1. ELIMINAR LA BARRA ROJA NATIVA */
            div[data-baseweb="tab-highlight"] {
                visibility: hidden !important;
            }
            
            /* 2. ESTADO ACTIVO (Pestaña seleccionada) */
            /* Texto: Rojo #9F2241 */
            div[data-testid="stTabs"] button[aria-selected="true"] p {
                color: #9F2241 !important;
            }
            /* Borde inferior (Rayita Activa): Rojo #9F2241 */
            div[data-testid="stTabs"] button[aria-selected="true"] {
                border-bottom: 4px solid #9F2241 !important;
                border-radius: 0px !important; 
            }
            
            /* 3. ESTADO HOVER (Pasar el mouse) */
            /* Texto: Verde #10312B */
            div[data-testid="stTabs"] button:hover p {
                color: #10312B !important; 
            }
            /* Borde inferior Hover: Verde #10312B */
            div[data-testid="stTabs"] button:hover {
                border-bottom: 4px solid #10312B !important;
                border-radius: 0px !important;
            }

            /* --- FIN PERSONALIZACIÓN TABS --- */

            /* Personalización del BOTÓN PRIMARIO (Acceder como invitado) */
            button[kind="primary"] {
                background-color: #9F2241 !important;
                border-color: #9F2241 !important;
                color: white !important;
            }
            button[kind="primary"]:hover {
                background-color: #7D1B33 !important;
                border-color: #7D1B33 !important;
            }
            button[kind="primary"]:focus:not(:active) {
                background-color: #9F2241 !important;
                border-color: #9F2241 !important;
                color: white !important;
                box-shadow: none !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Centrar el contenido
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown(
            """
            <div style="text-align: center; padding: 2rem 0;">
                <h1 style="color: #9F2241;">Dashboard Delitos CDMX</h1>
                <p style="font-size: 1.2rem; color: #666;">Sistema de Análisis de Criminalidad</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        st.markdown("---")
        
        # Tabs para login y acceso invitado
        tab1, tab2 = st.tabs(["🔑 Login Usuario", "👥 Acceso Invitado"])
        
        with tab1:
            st.markdown("### Iniciar Sesión")
            
            with st.form("login_form"):
                username = st.text_input("Usuario", placeholder="Ingresa tu usuario")
                password = st.text_input("Contraseña", type="password", placeholder="Ingresa tu contraseña")
                submit = st.form_submit_button("Iniciar Sesión", use_container_width=True)
                
                if submit:
                    if username and password:
                        if login(username, password, usuarios):
                            st.success("✅ Login exitoso! Redirigiendo...")
                            st.rerun()
                        else:
                            st.error("❌ Usuario o contraseña incorrectos")
                    else:
                        st.warning("⚠️ Por favor completa todos los campos")
        
        with tab2:
            st.markdown("### Acceso como Invitado")
            
            # CAMBIO: Usamos HTML personalizado en lugar de st.info
            st.markdown(
                """
                <div style="
                    background-color: #f8f9fa; 
                    padding: 1rem; 
                    border-radius: 0.5rem; 
                    color: #262730; 
                    margin-bottom: 1rem;
                    text-align: center;
                ">
                    Accede sin credenciales con permisos limitados
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # El botón usará el estilo CSS definido arriba
            if st.button("Acceder como Invitado", use_container_width=True, type="primary"):
                login_invitado()
                st.success("✅ Acceso como invitado concedido! Redirigiendo...")
                st.rerun()
        
        st.markdown("---")
        
        # Información de credenciales de prueba
        with st.expander("ℹ️ Credenciales de prueba"):
            st.markdown("""
            **Usuario Privilegiado:**
            - Usuario: `admin`
            - Contraseña: `thales123`
            """)