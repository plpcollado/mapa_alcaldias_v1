# Librerías necesarias para el funcionamiento de esta página
import streamlit as st
import numpy as np
from streamlit_folium import st_folium
import data_loader   # Módulo local de carga de datos
import map_utils     # Módulo local de utilidades de mapa
import plot_utils    # Módulo local de visualizaciones
import auth_utils    # Módulo local de autenticación
import os            # Para verificar rutas

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(
    page_title="Mapa Interactivo",
    page_icon="🗺️",
    layout="wide"
)

# --- FUNCIÓN PARA CARGAR CSS EXTERNO (KPIs) ---
def cargar_css(nombre_archivo):
    """Lee el archivo CSS y lo inyecta en la app."""
    try:
        with open(nombre_archivo, encoding='utf-8') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        pass
    except Exception as e:
        st.error(f"Error cargando CSS: {e}")

# Cargar los estilos de KPIs
cargar_css("kpi_styles.css")

# --- INYECCIÓN DE CSS PERSONALIZADO ---
st.markdown(
    """
    <style>
    /* 1. SELECTBOX (FILTROS Y DENSIDAD): Borde color vino al enfocar */
    div[data-baseweb="select"] > div:focus-within {
        border-color: #9F2241 !important;
    }

    /* 2. MULTISELECT (CAPAS) - LÓGICA DE COLOR */
    div[data-testid="stMultiSelect"]:not(:has(input:disabled)) span[data-baseweb="tag"] {
        background-color: #9F2241 !important;
    }
    div[data-testid="stMultiSelect"]:not(:has(input:disabled)) span[data-baseweb="tag"] span {
        color: white !important;
    }
    div[data-testid="stMultiSelect"]:not(:has(input:disabled)) span[data-baseweb="tag"] svg {
        fill: white !important;
        color: white !important;
    }

    /* 3. ESTILO UNIFICADO PARA CAJAS DE ALERTA/INFO */
    .custom-alert-box {
        padding: 1rem;
        border-radius: 0.25rem;
        margin-bottom: 1rem;
        background-color: #f8f9fa; /* Fondo gris muy claro */
        border-left: 6px solid #6c757d; /* CAMBIO: Borde gris oscuro (no vino) */
        color: #262730;
        font-size: 0.95rem;
    }
    
    .warning-icon {
        font-size: 1.2rem;
        margin-right: 0.5rem;
        vertical-align: middle;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Control de acceso de autenticación
auth_utils.requiere_autenticacion()

# 2. CARGA DE DATOS
URL_GEOJSON_ALCALDIAS = "https://datos.cdmx.gob.mx/dataset/alcaldias/resource/8648431b-4f34-4f1a-a4b1-19142f944300/download/limite-de-las-alcaldias.json"
delegaciones = map_utils.load_geojson(URL_GEOJSON_ALCALDIAS, local_backup="limite-de-las-alcaldias.json")

# Carga del dataset optimizado
try:
    data = data_loader.load_data()
except Exception as e:
    st.error(f"Error crítico al cargar datos: {e}")
    st.stop()

if data.empty:
    st.error("No se pudieron cargar los datos.")
    st.stop()

# TÍTULO DE PÁGINA
st.title("Mapa Interactivo de Incidencia - CDMX")

# 3. SIDEBAR DE FILTROS PRINCIPALES
st.sidebar.header("Filtros Principales")

# a. Filtro Alcaldía
alcaldia = st.sidebar.selectbox(
    "Selecciona Alcaldía:",
    ["TODAS"] + sorted(data["alcaldia_hecho"].dropna().unique())
)

# b. Filtro Categoría
if "CATEGORIA" in data.columns:
    lista_categorias = ["TODAS"] + sorted(data["CATEGORIA"].dropna().unique())
    columna_filtro = "CATEGORIA"
else:
    lista_categorias = ["TODAS"] + sorted(data["delito"].dropna().unique())
    columna_filtro = "delito"

categoria = st.sidebar.selectbox(
    "Selecciona Categoría:",
    lista_categorias
)

# 4. SIDEBAR DE FILTROS DE MAPA
st.sidebar.markdown("---")
st.sidebar.header("Configuración del Mapa")

with st.sidebar.form(key="map_config_form"):
    tipo_mapa = st.multiselect(
        "Capas a mostrar:",
        ["Puntos", "Heatmap"],
        default=["Heatmap"]
    )
    
    # Selector de muestreo
    opciones_muestreo = {
        "10% (Muy Rápido)": 0.1,
        "20% (Rápido)": 0.2,
        "40% (Equilibrado)": 0.4,
        "60% (Detallado)": 0.6,
        "80% (Muy Detallado)": 0.8,
        "100% (Todos los datos)": 1.0
    }
    
    seleccion_muestreo_texto = st.selectbox(
        "Densidad de puntos (Rendimiento):",
        options=opciones_muestreo.keys(),
        index=0 
    )
    
    porcentaje_seleccionado = opciones_muestreo[seleccion_muestreo_texto]
    map_submit_button = st.form_submit_button(label="🔄 Actualizar Mapa")

# 5. FILTRADO DE DATOS
df_filtrado = data.copy()

if alcaldia != "TODAS":
    df_filtrado = df_filtrado[df_filtrado["alcaldia_hecho"] == alcaldia]

if categoria != "TODAS":
    df_filtrado = df_filtrado[df_filtrado[columna_filtro] == categoria]

# 6. KPIs
st.markdown("### Indicadores Clave")
col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)

# Cálculo de valores
total = f"{len(df_filtrado):,}"
alcaldia_val = df_filtrado["alcaldia_hecho"].value_counts().index[0] if len(df_filtrado) > 0 else "N/A"
delito_val = df_filtrado["delito"].value_counts().index[0] if len(df_filtrado) > 0 else "N/A"
delito_val_display = (delito_val[:50] + '...') if len(delito_val) > 50 else delito_val

violento_val = "N/A"
if 'Violento' in df_filtrado.columns and len(df_filtrado) > 0:
    pct = (df_filtrado['Violento'] == 'Violento').mean()
    violento_val = f"{pct:.1%}"

with col_kpi1:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">Total de Incidentes</div><div class="kpi-value text-lg">{total}</div></div>""", unsafe_allow_html=True)
with col_kpi2:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">Alcaldía con Más Incidentes</div><div class="kpi-value text-md">{alcaldia_val}</div></div>""", unsafe_allow_html=True)
with col_kpi3:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">Delito Más Común</div><div class="kpi-value text-sm">{delito_val_display}</div></div>""", unsafe_allow_html=True)
with col_kpi4:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">% Violentos</div><div class="kpi-value text-lg">{violento_val}</div></div>""", unsafe_allow_html=True)

st.markdown("---")

# 7. DISCLAIMER Y ADVERTENCIAS

# Disclaimer desplegable
with st.expander("Disclaimer"):
    st.markdown("""
    El dataset mediante el que se basan las visualizaciones es un muestreo del 35% del dataframe original debido a las limitaciones de Streamlit en cuanto a eficiencia, ya que se encontró que esta cantidad de datos era lo suficientemente representativa pero lo suficientemente recortada para permitir un funcionamiento óptimo y eficaz.
    """)

# Advertencia de Rendimiento (Borde Gris)
st.markdown(
    """
    <div class="custom-alert-box">
        <span class="warning-icon">⚠️</span>
        <span>
            <strong>Precaución de Rendimiento:</strong> 
            Selecciones de más de <strong>10,000 datos</strong> mostrarán problemas de rendimiento independientemente del porcentaje de muestreo seleccionado. 
            La "Densidad de puntos" afecta principalmente a la carga visual del Heatmap. 
            Por favor, revise con cuidado el número de registros totales en los KPIs o en el cuadro inferior antes de hacer clic en "Actualizar Mapa".
        </span>
    </div>
    """,
    unsafe_allow_html=True
)

# 8. VISUALIZACIÓN PRINCIPAL (MAPA)
st.subheader(f"Mapa de Incidencias ({alcaldia})")

if df_filtrado.empty:
    st.warning("⚠️ No hay datos para mostrar con los filtros seleccionados.")
else:
    total_registros = len(df_filtrado)
    num_points = int(total_registros * porcentaje_seleccionado)
    
    # Cuadro de información previo al mapa (Borde Gris, SIN emoji)
    st.markdown(
        f"""
        <div class="custom-alert-box">
            <span>
                Visualizando muestra de <strong>{num_points:,}</strong> eventos ({seleccion_muestreo_texto})
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    if num_points < total_registros:
        df_mapa = df_filtrado.sample(n=num_points)
    else:
        df_mapa = df_filtrado.copy()

    m = map_utils.render_folium_map(
        df_mapa,
        delegaciones,
        show_points=("Puntos" in tipo_mapa),
        show_heatmap=("Heatmap" in tipo_mapa)
    )
    
    st_folium(
        m, 
        height=600, 
        use_container_width=True, 
        returned_objects=[] 
    )

auth_utils.renderizar_logout_sidebar()