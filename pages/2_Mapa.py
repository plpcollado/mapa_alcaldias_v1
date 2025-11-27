# pages/2_Mapa.py
# Librerías necesarias para el funcionamiento de esta página
import streamlit as st
import numpy as np
from streamlit_folium import st_folium
import data_loader   # Módulo local de carga de datos
import map_utils     # Módulo local de utilidades de mapa
import plot_utils    # Módulo local de visualizaciones
import auth_utils    # Módulo local de carga de datos
import os            # Para verificar rutas

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(
    page_title="Mapa Interactivo",
    page_icon="🗺️",
    layout="wide"
)

# --- FUNCIÓN PARA CARGAR CSS EXTERNO ---
def cargar_css(nombre_archivo):
    """Lee el archivo CSS y lo inyecta en la app."""
    try:
        with open(nombre_archivo, encoding='utf-8') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"⚠️ No se encontró el archivo de estilos: {nombre_archivo}")
    except Exception as e:
        st.error(f"Error cargando CSS: {e}")

# Cargar los estilos desde el archivo externo
cargar_css("kpi_styles.css")

# Control de acceso de autenticación
auth_utils.requiere_autenticacion()

# 2. CARGA DE DATOS
URL_GEOJSON_ALCALDIAS = "https://datos.cdmx.gob.mx/dataset/alcaldias/resource/8648431b-4f34-4f1a-a4b1-19142f944300/download/limite-de-las-alcaldias.json"
delegaciones = map_utils.load_geojson(URL_GEOJSON_ALCALDIAS, local_backup="limite-de-las-alcaldias.json")

# Carga exclusiva del dataset optimizado
try:
    data = data_loader.load_data("hour_crimes_optimized.csv")
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
st.sidebar.header("🗺️ Configuración del Mapa")

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

# 6. KPIs (CONSTRUCCIÓN MANUAL HTML PARA CONTROL TOTAL)
st.markdown("### Indicadores Clave")
col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)

# Cálculo de valores
total = f"{len(df_filtrado):,}"
alcaldia_val = df_filtrado["alcaldia_hecho"].value_counts().index[0] if len(df_filtrado) > 0 else "N/A"
delito_val = df_filtrado["delito"].value_counts().index[0] if len(df_filtrado) > 0 else "N/A"
# Usamos un recorte suave solo por seguridad, el CSS manejará el ajuste
delito_val_display = (delito_val[:50] + '...') if len(delito_val) > 50 else delito_val

violento_val = "N/A"
if 'Violento' in df_filtrado.columns and len(df_filtrado) > 0:
    pct = (df_filtrado['Violento'] == 'Violento').mean()
    violento_val = f"{pct:.1%}"

# Renderizado HTML usando las clases del CSS externo
# Cada tarjeta usa la clase base 'kpi-card' y una clase de texto específica (text-lg, text-md, text-sm)
with col_kpi1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Total de Incidentes</div>
        <div class="kpi-value text-lg">{total}</div>
    </div>
    """, unsafe_allow_html=True)

with col_kpi2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Alcaldía con Más Incidentes</div>
        <div class="kpi-value text-md">{alcaldia_val}</div>
    </div>
    """, unsafe_allow_html=True)

with col_kpi3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Delito Más Común</div>
        <div class="kpi-value text-sm">{delito_val_display}</div>
    </div>
    """, unsafe_allow_html=True)

with col_kpi4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">% Violentos</div>
        <div class="kpi-value text-lg">{violento_val}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# 7. ADVERTENCIA DE RENDIMIENTO (Gris Sobrio)
st.markdown(
    """
    <div class="warning-box">
        <span class="warning-icon">⚠️</span>
        <span>
            <strong>Precaución de Rendimiento:</strong> 
            El uso de una alta "Densidad de puntos" (superior al 40%) puede ralentizar significativamente 
            la carga del mapa. Se recomienda usar configuraciones bajas (10% o 20%) para una exploración fluida.
        </span>
    </div>
    """,
    unsafe_allow_html=True
)

# 8. VISUALIZACIÓN PRINCIPAL (MAPA)
st.subheader(f"📍 Mapa de Incidencias ({alcaldia})")

if df_filtrado.empty:
    st.warning("⚠️ No hay datos para mostrar con los filtros seleccionados.")
else:
    total_registros = len(df_filtrado)
    num_points = int(total_registros * porcentaje_seleccionado)
    
    if num_points < total_registros:
        df_mapa = df_filtrado.sample(n=num_points)
        st.info(f"Visualizando muestra de {num_points:,} eventos ({seleccion_muestreo_texto})")
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

# 9. INFORMACIÓN ADICIONAL
st.markdown("---")
with st.expander("ℹ️ Resumen técnico"):
    st.markdown(f"""
    **Resumen de Filtros Activos:**
    - **Alcaldía:** {alcaldia}
    - **Categoría:** {categoria}
    - **Registros Totales en Pantalla:** {len(df_filtrado):,}
    """)

auth_utils.renderizar_logout_sidebar()