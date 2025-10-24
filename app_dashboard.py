import streamlit as st
from streamlit_folium import st_folium
from data_loader import load_data
from map_utils import load_geojson, render_folium_map

st.set_page_config(page_title="Dashboard CDMX", layout="wide")
st.title("🚨 Dashboard de Incidentes Delictivos – CDMX")

# === 1. Carga de datos y GeoJSON ===
url_geojson = "https://datos.cdmx.gob.mx/dataset/alcaldias/resource/8648431b-4f34-4f1a-a4b1-19142f944300/download/limite-de-las-alcaldias.json"
delegaciones = load_geojson(url_geojson)
df = load_data("df_streamlit.csv")

# === 2. Controles de interfaz ===
st.sidebar.header("⚙️ Configuración del mapa")
opcion = st.sidebar.selectbox("Selecciona alcaldía (opcional):", ["TODAS"] + sorted(df["alcaldia_hecho"].dropna().unique()))
tipo_capa = st.sidebar.multiselect("Capas a mostrar:", ["Puntos", "Heatmap"], default=["Heatmap"])
num_points = st.sidebar.slider("Número de puntos (muestreo)", 100, 2000, 500, step=100)

# === 3. Filtrado ===
if opcion != "TODAS":
    df = df[df["alcaldia_hecho"] == opcion]
if len(df) > num_points:
    df = df.sample(num_points, random_state=42)

# === 4. Render del mapa ===
m = render_folium_map(
    df,
    delegaciones,
    show_points="Puntos" in tipo_capa,
    show_heatmap="Heatmap" in tipo_capa
)
st_folium(m, width=800, height=600)
