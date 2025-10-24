import folium
from folium.plugins import HeatMap
import geopandas as gpd
import streamlit as st
import requests
from io import BytesIO

def load_geojson(url, local_backup="limite-de-las-alcaldias.json"):
    """Carga el GeoJSON desde una URL; si falla, usa una copia local."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        st.success("✅ GeoJSON cargado correctamente desde Datos Abiertos CDMX")
        return gpd.read_file(BytesIO(response.content))
    except Exception as e:
        st.warning(f"⚠️ No se pudo cargar desde la web ({e}). Intentando archivo local...")
        try:
            return gpd.read_file(local_backup)
        except Exception as e2:
            st.error(f"❌ Error al cargar el GeoJSON local: {e2}")
            st.stop()
            
def render_folium_map(df, delegaciones, show_points=True, show_heatmap=True):
    """Construye un mapa Folium con límites y capas."""
    m = folium.Map(location=[19.4326, -99.1332], zoom_start=11, tiles="Cartodb positron")

    folium.GeoJson(
        delegaciones,
        name="Límite de alcaldías CDMX",
        style_function=lambda x: {"color": "gray", "weight": 1, "fillOpacity": 0.05},
        tooltip=folium.GeoJsonTooltip(fields=["NOMGEO"], aliases=["Alcaldía:"]),
    ).add_to(m)

    if show_points:
        for _, row in df.iterrows():
            folium.CircleMarker(
                location=[row["latitud"], row["longitud"]],
                radius=2, color="red", fill=True, fill_opacity=0.6
            ).add_to(m)

    if show_heatmap:
        heat_data = df[["latitud", "longitud"]].values.tolist()
        HeatMap(heat_data, radius=10, blur=15, min_opacity=0.3).add_to(m)

    folium.LayerControl().add_to(m)
    return m
