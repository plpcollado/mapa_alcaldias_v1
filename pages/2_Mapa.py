# Librerías necesarias para el funcionamiento de esta página
import streamlit as st
import numpy as np
from streamlit_folium import st_folium
import data_loader   # Módulo local de carga de datos
import map_utils     # Módulo local de utilidades de mapa
import plot_utils    # Módulo local de visualizaciones
import auth_utils    # Módulo local de carga de datos

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(
    page_title="Mapa Interactivo",
    page_icon="🗺️",
    layout="wide"
)

# Control de acceso de autenticación
auth_utils.requiere_autenticacion()

# 2. CARGA DE DATOS
URL_GEOJSON_ALCALDIAS = "https://datos.cdmx.gob.mx/dataset/alcaldias/resource/8648431b-4f34-4f1a-a4b1-19142f944300/download/limite-de-las-alcaldias.json"
delegaciones = map_utils.load_geojson(URL_GEOJSON_ALCALDIAS, local_backup="limite-de-las-alcaldias.json")

# CAMBIO 1: Intentando cargar el dataset completo
try:
    data = data_loader.load_data("hour_crimes_optimized.csv")
except Exception:
    st.warning("No se encontró 'hour_crimes_optimized.csv', cargando 'df_streamlit.csv' por defecto.")
    data = data_loader.load_data("df_streamlit.csv")

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
# Asumimos que data_loader crea la columna 'CATEGORIA'.
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
    
    # Selector de muestreo para evitar que el mapa se trabe con muchos datos
    # CAMBIO: Se agrega opción de 10%
    opciones_muestreo = {
        "10% (Muy Rápido)": 0.1,  # Nueva opción
        "20% (Rápido)": 0.2,
        "40% (Equilibrado)": 0.4,
        "60% (Detallado)": 0.6,
        "80% (Muy Detallado)": 0.8,
        "100% (Todos los datos)": 1.0
    }
    
    seleccion_muestreo_texto = st.selectbox(
        "Densidad de puntos (Rendimiento):",
        options=opciones_muestreo.keys(),
        index=0 # Por defecto 10% (Muy Rápido)
    )
    
    porcentaje_seleccionado = opciones_muestreo[seleccion_muestreo_texto]
    map_submit_button = st.form_submit_button(label="🔄 Actualizar Mapa")

# 5. Filtrado de Datos
df_filtrado = data.copy()

if alcaldia != "TODAS":
    df_filtrado = df_filtrado[df_filtrado["alcaldia_hecho"] == alcaldia]

if categoria != "TODAS":
    df_filtrado = df_filtrado[df_filtrado[columna_filtro] == categoria]

# 6. KPIs (Indicadores Clave)
st.markdown("### Indicadores Clave")
col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)

with col_kpi1:
    st.metric("Total de Incidentes", f"{len(df_filtrado):,}")

with col_kpi2:
    if len(df_filtrado) > 0:
        alcaldia_top = df_filtrado["alcaldia_hecho"].value_counts().index[0]
        st.metric("Alcaldía con Más Incidentes", alcaldia_top)
    else:
        st.metric("Alcaldía con Más Incidentes", "N/A")

with col_kpi3:
    if len(df_filtrado) > 0:
        delito_top = df_filtrado["delito"].value_counts().index[0]
        texto_delito = (delito_top[:25] + '...') if len(delito_top) > 25 else delito_top
        st.metric("Delito Más Común", texto_delito)
    else:
        st.metric("Delito Más Común", "N/A")

with col_kpi4:
    if 'Violento' in df_filtrado.columns and len(df_filtrado) > 0:
        pct_violento = (df_filtrado['Violento'] == 'Violento').mean()
        st.metric("% Violentos", f"{pct_violento:.1%}")
    else:
        st.metric("% Violentos", "N/A")

st.markdown("---")

# 7. VISUALIZACIÓN PRINCIPAL (MAPA) - FILA COMPLETA
st.subheader(f"📍 Mapa de Incidencias ({alcaldia})")

if df_filtrado.empty:
    st.warning("⚠️ No hay datos para mostrar con los filtros seleccionados.")
else:
    # Lógica de muestreo para rendimiento
    total_registros = len(df_filtrado)
    num_points = int(total_registros * porcentaje_seleccionado)
    
    if num_points < total_registros:
        df_mapa = df_filtrado.sample(n=num_points)
        st.info(f"Visualizando {num_points} eventos (Muestreo: {seleccion_muestreo_texto})")
    else:
        df_mapa = df_filtrado.copy()

    # Renderizado usando la función robusta
    m = map_utils.render_folium_map(
        df_mapa,
        delegaciones,
        show_points=("Puntos" in tipo_mapa),
        show_heatmap=("Heatmap" in tipo_mapa)
    )
    
    # CAMBIO 2: Mapa ocupa todo el ancho (sin columnas) y más altura
    st_folium(
        m, 
        height=600, 
        use_container_width=True, 
        returned_objects=[] 
    )

st.markdown("---")

# 8. GRÁFICAS ADICIONALES - FILA COMPLETA (DEBAJO DEL MAPA)
st.subheader("📈 Estadísticas Detalladas")

# Las pestañas ahora ocuparán todo el ancho de la página
tab1, tab2 = st.tabs(["Distribución por Alcaldía", "Top 10 Delitos"])

with tab1:
    # CAMBIO 3: Gráfico ocupa todo el ancho disponible
    chart_alcaldia = plot_utils.plot_delitos_por_alcaldia(df_filtrado)
    st.altair_chart(chart_alcaldia, use_container_width=True)
    
with tab2:
    # Intentamos usar la función plot_top_delitos
    try:
        chart_top = plot_utils.plot_top_delitos(df_filtrado, top_n=10)
        st.altair_chart(chart_top, use_container_width=True)
    except AttributeError:
        st.info("El gráfico de Top Delitos estará disponible próximamente.")

# 9. INFORMACIÓN ADICIONAL (EXPANDER)
st.markdown("---")
with st.expander("ℹ️ Información técnica de esta vista"):
    st.markdown(f"""
    **Resumen de Filtros Activos:**
    - **Alcaldía:** {alcaldia}
    - **Categoría:** {categoria}
    - **Registros Totales en Pantalla:** {len(df_filtrado):,}
    
    **Nota sobre el mapa:** Si notas lentitud, reduce el porcentaje de "Densidad de puntos" en la barra lateral.
    """)

# Botón de cerrar sesión al final del sidebar
auth_utils.renderizar_logout_sidebar()