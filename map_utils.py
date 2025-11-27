# map_utils.py
# -----------------------------------------------------------------------------
# MÓDULO DE UTILIDADES DE MAPAS (FOLIUM)
# -----------------------------------------------------------------------------
import folium
from folium.plugins import HeatMap
import geopandas as gpd
import streamlit as st
import requests
from io import BytesIO
import pandas as pd
import numpy as np

# --- Importar colores ---
from config import PALETA_PRINCIPAL, ESCALA_ROJOS

# --------------------------------------------------------------------------
# --- FUNCIONES DE MAPA ---
# --------------------------------------------------------------------------

@st.cache_data
def load_geojson(url, local_backup="limite-de-las-alcaldias.json"):
    """Carga el GeoJSON de ALCALDÍAS desde una URL; si falla, usa una copia local."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return gpd.read_file(BytesIO(response.content))
    except Exception:
        try:
            return gpd.read_file(local_backup)
        except Exception as e2:
            st.error(f"❌ Error crítico: No se pudo cargar el mapa base (GeoJSON): {e2}")
            st.stop()
            
def render_folium_map(df, delegaciones, show_points=True, show_heatmap=True):
    """Construye un mapa Folium simple (Puntos/Heatmap) con límites de alcaldías."""
    
    # Determinar el centro del mapa
    if not df.empty:
        map_center = [df["latitud"].mean(), df["longitud"].mean()]
    else:
        map_center = [19.4326, -99.1332] # Centro CDMX

    m = folium.Map(location=map_center, zoom_start=11, tiles="Cartodb positron")

    # 1. Capa de límites de alcaldías (Fondo gris transparente)
    folium.GeoJson(
        delegaciones,
        name="Límite de alcaldías CDMX",
        style_function=lambda x: {"color": "gray", "weight": 1, "fillOpacity": 0.05},
        tooltip=folium.GeoJsonTooltip(fields=["NOMGEO"], aliases=["Alcaldía:"]),
    ).add_to(m)

    # Preparar datos de localizaciones
    df_map = df[["latitud", "longitud"]].dropna()
    locations = list(zip(df_map["latitud"], df_map["longitud"]))

    # 2. Capa de Heatmap
    if show_heatmap and not df_map.empty:
        HeatMap(locations, radius=12, blur=10).add_to(m)

    # 3. Capa de Puntos (Círculos)
    if show_points and not df_map.empty:
        color_puntos = PALETA_PRINCIPAL[0] # Usar el rojo principal
        
        for loc in locations:
            # Usar CircleMarker ligeros para mejor rendimiento
            folium.CircleMarker(
                location=loc,
                radius=2, 
                color=color_puntos,
                fill=True,
                fill_color=color_puntos,
                fill_opacity=0.7,
                weight=0 # Sin borde para renderizado más rápido
            ).add_to(m)

    return m