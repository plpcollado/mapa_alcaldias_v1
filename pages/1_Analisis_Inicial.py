# Librerías necesarias para el funcionamiento de esta página
import streamlit as st
import data_loader  # Módulo local de carga de datos
import plot_utils   # Módulo local de visualizaciones
import auth_utils   # Módulo local de autenticación

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(
    page_title="Dashboard Interactivo - Delitos CDMX",
    page_icon="📋",
    layout="wide"
)

# --- INYECCIÓN DE CSS (CORREGIDO PARA ESTADOS ACTIVOS/INACTIVOS) ---
st.markdown(
    """
    <style>
    /* 1. SELECTBOX (ALCALDÍA): Borde color vino al enfocar */
    div[data-baseweb="select"] > div:focus-within {
        border-color: #9F2241 !important;
    }

    /* 2. MULTISELECT (AÑOS) - LÓGICA INTELIGENTE */
    
    /* Solo aplicamos el color VINO si el contenedor NO tiene un input deshabilitado */
    div[data-testid="stMultiSelect"]:not(:has(input:disabled)) span[data-baseweb="tag"] {
        background-color: #9F2241 !important;
    }
    
    /* Texto blanco solo si está activo */
    div[data-testid="stMultiSelect"]:not(:has(input:disabled)) span[data-baseweb="tag"] span {
        color: white !important;
    }
    
    /* Icono 'x' blanco solo si está activo */
    div[data-testid="stMultiSelect"]:not(:has(input:disabled)) span[data-baseweb="tag"] svg {
        fill: white !important;
        color: white !important;
    }

    /* NOTA: Cuando se bloquea (input:disabled), estas reglas no aplican 
       y el componente regresa a su color gris por defecto automáticamente. */
    </style>
    """,
    unsafe_allow_html=True
)
# --------------------------------------------------------

# Control de acceso: requiere autenticación (todos los tipos de usuario)
auth_utils.requiere_autenticacion()

# 2. CARGA DE DATOS
data = data_loader.load_data("df_streamlit.csv") 
data_completo = data_loader.load_data("hour_crimes_optimized.csv")

# Aviso de carga incorrecta de datos
if data.empty:
    st.error("No se pudieron cargar los datos.")
    st.stop()

# 3. TÍTULO
st.title("Dashboard Interactivo - Delitos CDMX")
st.subheader("Análisis Exploratorio de los Datos")

# disclaimer de cantidad de datos usada
st.markdown(
    """
    <div style="
        padding: 1rem;
        border-radius: 0.25rem;
        margin-bottom: 1rem;
        background-color: #f8f9fa; /* Fondo gris muy claro */
        border-left: 6px solid #9F2241; /* La 'ranura' lateral en color vino */
        color: #262730;
    ">
        <strong>Disclaimer:</strong> El dataset mediante el que se basan las visualizaciones es un muestreo del 35% del dataframe original debido a las limitaciones de Streamlit en cuanto a eficiencia, ya que se encontró que esta cantidad de datos era lo suficientemente representativa pero lo suficientemente recortada para permitir un funcionamiento óptimo y eficaz.
    </div>
    """,
    unsafe_allow_html=True
)

# 4. CONFIGURACIÓN DEL SIDEBAR (FILTROS)
st.sidebar.header("Filtros Globales")

# a. Filtro de Alcaldía
col_alcaldia = 'alcaldia_hecho'

# Se genera el dataframe filtrado con el original
data_completo_filtered = data_completo.copy()

#Se verifica que la columna exista para generar el listado
if col_alcaldia in data_completo.columns:
    lista_alcaldias = sorted(data_completo[col_alcaldia].dropna().unique())
    
    alcaldia_seleccionada = st.sidebar.selectbox(
        "Selecciona Alcaldía:",
        options=["TODAS"] + lista_alcaldias,
        index=0
    )
    
    # Aplicar filtro de alcaldía
    if alcaldia_seleccionada != "TODAS":
        data_completo_filtered = data_completo_filtered[data_completo_filtered[col_alcaldia] == alcaldia_seleccionada]
else:
    st.sidebar.warning("Columna 'alcaldia_hecho' no encontrada en el dataset.")
    alcaldia_seleccionada = "TODAS"

st.sidebar.markdown("---")

# b. Filtro de Año
year_col = 'anio_hecho' if 'anio_hecho' in data_completo.columns else 'anio_hecho_N'

if year_col in data_completo.columns:
    # Obtener años disponibles (No anteriores a 2016)
    all_years_raw = sorted(data_completo[year_col].dropna().unique().astype(int))
    years_available = [y for y in all_years_raw if y >= 2016]
    
    # Se crea checkbox "Seleccionar todos" para evitar confusión
    usar_todos = st.sidebar.checkbox("Seleccionar todos los años", value=True)
    
    if usar_todos:
        selected_years = years_available
        # Se muestra el select deshabilitado
        st.sidebar.multiselect(
            "Años considerados:", 
            options=years_available, 
            default=years_available, 
            disabled=True
        )
    else:
        # Selección manual de los años
        selected_years = st.sidebar.multiselect(
            "Selecciona Año(s):",
            options=years_available,
            default=years_available,
            help="Desmarca la casilla de arriba para personalizar."
        )
    
    # Aplicar filtro de año sobre los datos
    if selected_years:
        data_completo_filtered = data_completo_filtered[data_completo_filtered[year_col].isin(selected_years)]
        
        # Texto resumen de filtros activos para mayor comprensión
        filtro_alcaldia_txt = f"📍 **Alcaldía:** {alcaldia_seleccionada}"
        filtro_anio_txt = f"🗓️ **Años:** {min(selected_years)} - {max(selected_years)}" if usar_todos else f"🗓️ **Años:** {', '.join(map(str, selected_years))}"
        st.markdown(f"{filtro_alcaldia_txt} | {filtro_anio_txt}")
        
    else:
        st.warning("Selecciona al menos un año.")
        data_completo_filtered = data_completo_filtered.iloc[0:0] # Vaciar si no hay años
else:
    st.warning(f"Columna de año no encontrada.")

st.markdown("---")

# 5. VISUALIZACIONES

# Verificación de seguridad por si el filtrado deja el df vacío
if data_completo_filtered.empty:
    st.warning("⚠️ No hay datos disponibles para esta combinación de filtros (Alcaldía/Año).")
else:
# a. Fila 1:
    # Se definenen las dos columnas de la primera fila
    col1, col2 = st.columns(2)

    # Se usa la función de plot.utils para gengerar el gráfico 1
    with col1:
        st.markdown("##### Frecuencia de Crímenes Violentos por Hora")
        chart_frecuencia = plot_utils.plot_crimenes_violentos_por_hora(data_completo_filtered)
        st.altair_chart(chart_frecuencia, use_container_width=True)

    # Se usa la función de plot.utils para gengerar el gráfico 2
    with col2:
        st.markdown("##### Delitos por Hora: Volumen Total y Fracción Violenta")
        chart_volumen = plot_utils.plot_volumen_total_violencia_hora(data_completo_filtered)
        st.altair_chart(chart_volumen, use_container_width=True)

    # Línea divisora entre filas
    st.markdown("---")

# b. Fila 2:
    # Se definen las columnas de la segunda fila
    col3, col4 = st.columns(2)

    # Se usa la función de plot.utils para gengerar el gráfico 3
    with col3:
        st.markdown("##### Porcentaje de Crímenes Violento por Hora")
        chart_ratio = plot_utils.plot_ratio_violencia_hora(data_completo_filtered)
        st.altair_chart(chart_ratio, use_container_width=True)

    # Se usa la función de plot.utils para gengerar el gráfico 4
    with col4:
        st.markdown("##### Heatmap de Proporción de Violencia (Día vs. Hora)")
        chart_heatmap = plot_utils.plot_heatmap_dia_hora(data_completo_filtered)
        st.altair_chart(chart_heatmap, use_container_width=True)
    
    # Línea divisora entre filas      
    st.markdown("---")

# c. Fila 3:
    # Se usa la función de plot.utils para gengerar el gráfico 5
    st.markdown("#### Distribución Temporal de Violencia")
    chart_polar = plot_utils.plot_polar_violencia_hora(data_completo_filtered)
    st.altair_chart(chart_polar, use_container_width=True)

# Botón de cerrar sesión al final del sidebar
auth_utils.renderizar_logout_sidebar()