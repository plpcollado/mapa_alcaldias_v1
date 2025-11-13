# app_dashboard.py
# -----------------------------------------------------------------------------
# APLICACIÓN PRINCIPAL DE STREAMLIT (VERSIÓN FINAL DUAL)
# - Contiene la lógica para el modo "Producción" (comentado)
# - Contiene la lógica para el modo "Dummy" (activo)
# - Layout de 2 columnas para gráficas
# - Implementa todos los módulos (config, data_loader, plot_utils, map_utils)
# -----------------------------------------------------------------------------

import streamlit as st
from streamlit_folium import st_folium
import data_loader  # Módulo local de carga de datos
import map_utils    # Módulo local de utilidades de mapa
import plot_utils   # Módulo local de visualizaciones (Altair)
import numpy as np

# --------------------------------------------------------------------------
# --- SECCIÓN 2: CÓDIGO DE DESARROLLO (PARA 'df_streamlit.csv') ---
# --------------------------------------------------------------------------
# Este bloque está ACTIVO.
# Carga 'df_streamlit.csv' y muestra el mapa de Alcaldías (Puntos/Heatmap).
# --------------------------------------------------------------------------

# === 1. Configuración de la Página ===
st.set_page_config(
    page_title="Dashboard Delitos CDMX",
    page_icon="🚨",
    layout="wide"
)
st.title("🚨 Dashboard de Incidentes Delictivos – CDMX (Modo Dummy)")
st.markdown("Análisis visual (con datos de muestra `df_streamlit.csv`)")

# === 2. Carga de Datos (Dummy) ===
URL_GEOJSON_ALCALDIAS = "https://datos.cdmx.gob.mx/dataset/alcaldias/resource/8648431b-4f34-4f1a-a4b1-19142f944300/download/limite-de-las-alcaldias.json"
delegaciones = map_utils.load_geojson(URL_GEOJSON_ALCALDIAS, local_backup="limite-de-las-alcaldias.json")

data = data_loader.load_data("df_streamlit.csv") 

# Cargar datos completos para gráficos 2 y 3
data_completo = data_loader.load_data("hour_crimes_cleaned.csv")

if data.empty:
    st.error("No se pudieron cargar los datos dummy. El dashboard no puede continuar.")
    st.stop()

# === 3. Sidebar de Filtros (Dummy) ===
st.sidebar.header("⚙️ Filtros Principales")

alcaldia = st.sidebar.selectbox(
    "Selecciona Alcaldía:",
    ["TODAS"] + sorted(data["alcaldia_hecho"].dropna().unique())
)

# El filtro ahora usa la columna 'CATEGORIA' que 'data_loader' crea
categoria = st.sidebar.selectbox(
    "Selecciona Categoría:",
    ["TODAS"] + sorted(data["CATEGORIA"].dropna().unique())
)

# --- Configuración del Mapa (Dummy) ---
st.sidebar.header("🗺️ Configuración del Mapa (Dummy)")
with st.sidebar.form(key="map_config_form"):
    tipo_mapa = st.multiselect(
        "Capas del Mapa:",
        ["Puntos", "Heatmap"],
        default=["Heatmap"]
    )
    
    opciones_muestreo = {
        "20% de los puntos": 0.2,
        "40% de los puntos": 0.4,
        "60% de los puntos": 0.6,
        "80% de los puntos": 0.8,
        "100% (Todos)": 1.0
    }
    
    seleccion_muestreo_texto = st.selectbox(
        "Muestreo de puntos (para rendimiento):",
        options=opciones_muestreo.keys(),
        index=len(opciones_muestreo) - 1  # Por defecto 100%
    )
    
    porcentaje_seleccionado = opciones_muestreo[seleccion_muestreo_texto]
    map_submit_button = st.form_submit_button(label="Aplicar Config. Mapa")


# === 4. Filtrado de Datos (Dummy) ===
df_filtrado = data.copy()

if alcaldia != "TODAS":
    df_filtrado = df_filtrado[df_filtrado["alcaldia_hecho"] == alcaldia]
if categoria != "TODAS":
    df_filtrado = df_filtrado[df_filtrado["CATEGORIA"] == categoria] # Usar CATEGORIA

if df_filtrado.empty:
    st.warning("No se encontraron registros con los filtros seleccionados.")

# === 5. Layout del Dashboard (Dummy) ===

# --- Fila 1: KPIs ---
st.subheader("Resumen de Incidentes (con filtros aplicados)")
kpi1, kpi2, kpi3 = st.columns(3)

total_delitos = df_filtrado.shape[0]
total_violentos = df_filtrado[df_filtrado['Violento'] == 'Violento'].shape[0]
ratio_violencia = (total_violentos / total_delitos) if total_delitos > 0 else 0

kpi1.metric("Total de Delitos", f"{total_delitos:,}")
kpi2.metric("Delitos Violentos", f"{total_violentos:,}")
kpi3.metric("Proporción Violenta", f"{ratio_violencia:.1%}")
st.markdown("---")

# --- Fila 2: Mapa y Gráfica (2 Columnas) ---
col1, col2 = st.columns((6, 4)) # Layout 60% mapa, 40% gráfica

with col1:
    st.subheader("Mapa de Incidencia (Dummy)")
    
    total_registros_filtrados = len(df_filtrado)
    num_points_calculado = int(total_registros_filtrados * porcentaje_seleccionado)
    num_points_a_usar = min(total_registros_filtrados, num_points_calculado)

    if num_points_a_usar < total_registros_filtrados:
        df_mapa = df_filtrado.sample(n=num_points_a_usar)
        st.info(f"Mostrando {num_points_a_usar} puntos ({seleccion_muestreo_texto})")
    else:
        df_mapa = df_filtrado.copy()
    
    # Llamar a la función de mapa dummy
    m = map_utils.render_folium_map(
        df_mapa,
        delegaciones,
        show_points=("Puntos" in tipo_mapa),
        show_heatmap=("Heatmap" in tipo_mapa)
    )
    st_folium(m, height=450, width="stretch") 

with col2:
    st.subheader("Delitos por Alcaldía")
    chart_alcaldia = plot_utils.plot_delitos_por_alcaldia(df_filtrado)
    st.altair_chart(chart_alcaldia, use_container_width=True)

st.markdown("---")
st.subheader("Análisis de Incidentes (con filtros aplicados)")

# --- Fila 3: Gráficas (2 Columnas) ---
col3, col4 = st.columns(2)

with col3:
    st.markdown("##### Gráfico 2: Volumen Total y Fracción Violenta")
    chart2 = plot_utils.plot_volumen_total_violencia_hora(data_completo)
    st.altair_chart(chart2, use_container_width=True)
    
with col4:
    st.markdown("##### Proporción de Violencia (General)")
    chart_donut = plot_utils.plot_proporcion_violencia(df_filtrado)
    st.altair_chart(chart_donut, use_container_width=True)

st.markdown("---")

# --- Fila 4: Gráficas (2 Columnas) ---
col5, col6 = st.columns(2)

with col5:
    st.markdown("##### Gráfico 1: Frecuencia de Crímenes Violentos")
    chart1 = plot_utils.plot_crimenes_violentos_por_hora(data_completo)
    st.altair_chart(chart1, use_container_width=True)
    
with col6:
    st.markdown("##### Gráfico 3: Porcentaje de Crímenes Violentos")
    chart3 = plot_utils.plot_ratio_violencia_hora(data_completo)
    st.altair_chart(chart3, use_container_width=True)
    
st.markdown("---")

# --- Fila 5: Gráficas (2 Columnas) ---
col7, col8 = st.columns(2)

with col7:
    st.markdown("##### Heatmap de Incidencia (Día vs. Hora)")
    chart_heatmap = plot_utils.plot_heatmap_dia_hora(data_completo)
    st.altair_chart(chart_heatmap, use_container_width=True)

with col8:
    st.markdown("##### Gráfico 4/5: Proporción Violenta (Polar)")
    chart_polar = plot_utils.plot_polar_violencia_hora(data_completo)
    st.altair_chart(chart_polar, use_container_width=True)
    
# --- Fila 6: Dataframe (Opcional) ---
if st.sidebar.checkbox("Mostrar datos crudos (filtrados)"):
    st.subheader("Datos Filtrados (Dummy)")
    st.dataframe(df_filtrado.head(100))