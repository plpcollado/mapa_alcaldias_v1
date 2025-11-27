import streamlit as st
import auth_utils
import pandas as pd
import geopandas as gpd
import folium
import joblib
import os
from datetime import date
import streamlit.components.v1 as components

# Configuración de la página
st.set_page_config(
    page_title="Análisis Detallado - Dashboard Delitos CDMX",
    page_icon="🔍",
    layout="wide",
)

# Control de acceso: solo usuarios privilegiados
auth_utils.requiere_autenticacion(user_types=["privilegiado"]) 

# === 2. Encabezado ===
st.title("Análisis Detallado")
st.subheader("Visualización de Predicciones por Cuadrante")

st.markdown("---")


@st.cache_data
def load_predictions(path: str) -> pd.DataFrame:
    # Carga de las predicciones desde CSV o Parquet y normaliza columnas
    if path.endswith(".parquet"):
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path, parse_dates=["ds"]) 
        
    df = df.rename(columns={c: c.strip() for c in df.columns})
    # Normalizar nombres comunes
    if "yhat_N_cuadrante" in df.columns:
        df = df.rename(columns={"yhat_N_cuadrante": "yhat"})
    
    # Normalizar cuadrante_id (siempre string limpio)
    if "cuadrante_id" in df.columns:
        try:
            # Si es float/int, convertir a string sin decimales
            df["cuadrante_id"] = df["cuadrante_id"].astype(str).str.replace('.0', '', regex=False)
        except Exception:
            df["cuadrante_id"] = df["cuadrante_id"].astype(str)
            
    return df


@st.cache_data
def load_polygons(url: str) -> gpd.GeoDataFrame:
    # Carga polígnonos de cuadrantes desde GeoJSON URL
    try:
        gdf = gpd.read_file(url)
        # Normalizar nombre de columna
        cols = gdf.columns
        cuadrante_col = next((c for c in cols if c.lower() == 'cuadrante_id'), None)
        if not cuadrante_col:
            cuadrante_col = next((c for c in cols if c.lower() == 'id'), None)
        
        if cuadrante_col:
            gdf = gdf.rename(columns={cuadrante_col: "cuadrante_id"})
            # Normalizar ID
            try:
                gdf["cuadrante_id"] = gdf["cuadrante_id"].astype(float).astype(int).astype(str)
            except:
                gdf["cuadrante_id"] = gdf["cuadrante_id"].astype(str)
            
            # Asegurar CRS
            if gdf.crs and gdf.crs.to_string() != "EPSG:4326":
                gdf = gdf.to_crs("EPSG:4326")
            return gdf
    except Exception:
        pass
    return None


@st.cache_data
def load_cuadrante_centroids(features_csv: str = None, joblib_path: str = None, geojson_url: str = None) -> pd.DataFrame:
    # Cargar el centroide de los cuadrantes desde diversas fuentes
    # Mapeo de joblib
    if joblib_path and os.path.exists(joblib_path):
        try:
            mapping = joblib.load(joblib_path)
            rows = []
            # mapping puede ser dict cuyas values sean polígonos o tuplas
            for k, v in mapping.items():
                try:
                    # si v es un shapely geometry
                    geom = getattr(v, "geometry", v)
                    if hasattr(geom, "centroid"):
                        c = geom.centroid
                        rows.append({"cuadrante_id": str(k), "lat": float(c.y), "lon": float(c.x)})
                        continue
                except Exception:
                    pass
                # si v es tupla (lat, lon) o (lon, lat) - intentar detectar
                if isinstance(v, (list, tuple)) and len(v) >= 2:
                    lat, lon = (v[0], v[1]) if abs(v[0]) <= 90 else (v[1], v[0])
                    try:
                        rows.append({"cuadrante_id": str(k), "lat": float(lat), "lon": float(lon)})
                        continue
                    except Exception:
                        pass
            if rows:
                return pd.DataFrame(rows)
        except Exception:
            pass

    # 2) CSV de features (espera columnas con lat/lon)
    if features_csv and os.path.exists(features_csv):
        try:
            # Leer solo columnas probables para ahorrar memoria
            usecols = None
            try:
                tmp = pd.read_csv(features_csv, nrows=5)
                cols = tmp.columns.str.lower()
                lat_col = next((c for c in cols if "lat" in c), None)
                lon_col = next((c for c in cols if "lon" in c or "long" in c), None)
                if lat_col and lon_col and "cuadrante_id" in cols:
                    usecols = [c for c in tmp.columns if c.lower() in [lat_col, lon_col, 'cuadrante_id']]
            except Exception:
                usecols = None

            df = pd.read_csv(features_csv, usecols=usecols) if usecols else pd.read_csv(features_csv)
            lower_cols = {c.lower(): c for c in df.columns}
            lat_col = lower_cols.get("latitud_n") or lower_cols.get("lat") or lower_cols.get("latitud")
            lon_col = lower_cols.get("longitud_n") or lower_cols.get("lon") or lower_cols.get("longitud") or lower_cols.get("long")
            if lat_col and lon_col and "cuadrante_id" in df.columns:
                out = df[["cuadrante_id", lat_col, lon_col]].dropna()
                out = out.rename(columns={lat_col: "lat", lon_col: "lon"})
                out["cuadrante_id"] = out["cuadrante_id"].astype(str)
                # agrupar por cuadrante y tomar centroid promedio
                out = out.groupby("cuadrante_id")["lat", "lon"].mean().reset_index()
                return out
        except Exception:
            pass

    # 3) GeoJSON URL
    if geojson_url:
        try:
            gdf = gpd.read_file(geojson_url)
            # Buscar columna de cuadrante
            cols = gdf.columns
            cuadrante_col = next((c for c in cols if c.lower() == 'cuadrante_id'), None)
            if not cuadrante_col:
                # Fallback: buscar 'id' si no existe cuadrante_id
                cuadrante_col = next((c for c in cols if c.lower() == 'id'), None)
            
            if cuadrante_col:
                # Calcular centroides
                gdf["centroid"] = gdf.geometry.centroid
                gdf["lat"] = gdf["centroid"].y
                gdf["lon"] = gdf["centroid"].x
                out = gdf[[cuadrante_col, "lat", "lon"]].rename(columns={cuadrante_col: "cuadrante_id"})
                
                # Normalizar ID para coincidir con predicciones
                try:
                    out["cuadrante_id"] = out["cuadrante_id"].astype(float).astype(int).astype(str)
                except Exception:
                    out["cuadrante_id"] = out["cuadrante_id"].astype(str)
                    
                return out
        except Exception:
            pass

    return pd.DataFrame(columns=["cuadrante_id", "lat", "lon"]) 

# Carga de datos (prioridad: parquet local > csv absoluto)
local_parquet = "data/predicciones_lite.parquet"

absolute_csv_fallback = "/Users/pedropc/Downloads/full-pipeline-clasificacion/Team5/results/prediccion_violencia/pred_prophet_cuadrantes_N7.csv"

if os.path.exists(local_parquet):
    pred_path = local_parquet
      
preds = load_predictions(pred_path)

# Selector de fecha en Sidebar
min_date = preds["ds"].min().date() if not preds.empty else date.today()
max_date = preds["ds"].max().date() if not preds.empty else date.today()

st.sidebar.markdown("### 📅 Configuración de Predicción")
sel_date = st.sidebar.date_input("Fecha de interés", value=min_date, min_value=min_date, max_value=max_date)

st.markdown(f"### Top-5 Cuadrantes con mayor probabilidad de violencia para el **{sel_date}**")

# Filtrar por fecha y agregar score por cuadrante
df_date = preds[preds["ds"].dt.date == sel_date].copy()
if df_date.empty:
    st.info("No hay predicciones para la fecha seleccionada.")
else:
    # Acomodar columna de score
    if "yhat" in df_date.columns:
        score_col = "yhat"
    else:
        # intentar encontrar columna numérica adicional
        numeric_cols = df_date.select_dtypes("number").columns.tolist()
        score_col = numeric_cols[0] if numeric_cols else None

    if not score_col:
        st.error("No se encontró columna de score en el CSV de predicción.")
    else:
        agg = (
            df_date.groupby("cuadrante_id")[score_col]
            .mean()
            .reset_index()
            .rename(columns={score_col: "score"})
            .sort_values("score", ascending=False)
        )

        top5 = agg.head(5).copy()

        # Cargar centroides (intentar joblib primero)
        joblib_map = "/Users/pedropc/Downloads/full-pipeline-clasificacion/Team5/results/prediccion_violencia/h3_cuadrante_mapping.joblib"
        features_csv = "/Users/pedropc/Downloads/full-pipeline-clasificacion/Team5/results/prediccion_violencia/cuadrante_features_N7.csv"
        geojson_url = "https://raw.githubusercontent.com/plpcollado/TC3001_Team5/main/cuadrantes.geojson"
        
        centroids = load_cuadrante_centroids(features_csv=features_csv, joblib_path=joblib_map, geojson_url=geojson_url)
        gdf_polygons = load_polygons(geojson_url)

        merged = top5.merge(centroids, on="cuadrante_id", how="left")

        # Crear mapa con folium
        if not merged["lat"].notna().any():
            st.warning("No se encontraron coordenadas para los cuadrantes (intenta proporcionar 'cuadrante_features_N7.csv' o el joblib mapping). Se mostrará la tabla únicamente.")
            st.table(merged)
        else:
            # Centro del mapa
            center_lat = merged["lat"].dropna().mean() if merged["lat"].notna().any() else 19.4326
            center_lon = merged["lon"].dropna().mean() if merged["lon"].notna().any() else -99.1332

            m = folium.Map(location=[center_lat, center_lon], zoom_start=11, tiles="Cartodb positron")

            # Añadir polígonos de TODOS los cuadrantes (capa base)
            if gdf_polygons is not None:
                folium.GeoJson(
                    gdf_polygons,
                    name="Todos los Cuadrantes",
                    style_function=lambda x: {
                        'fillColor': "#9F22413D",
                        'color': '#666666',
                        'weight': 1.0,
                        'fillOpacity': 0.05
                    },
                    tooltip=folium.GeoJsonTooltip(
                        fields=['cuadrante_id'],
                        aliases=['Cuadrante:'],
                        localize=True
                    )
                ).add_to(m)

                # Añadir polígonos de los Top-5 (resaltados)
                top5_ids = merged["cuadrante_id"].unique()
                subset = gdf_polygons[gdf_polygons["cuadrante_id"].isin(top5_ids)].copy()
                
                if not subset.empty:
                    # Merge con score para tooltip
                    subset = subset.merge(merged[["cuadrante_id", "score"]], on="cuadrante_id", how="left")
                    
                    folium.GeoJson(
                        subset,
                        name="Límites Top 5",
                        style_function=lambda x: {
                            'fillColor': '#ff4444',
                            'color': 'black',
                            'weight': 2,
                            'fillOpacity': 0.4
                        },
                        tooltip=folium.GeoJsonTooltip(
                            fields=['cuadrante_id', 'score'],
                            aliases=['Cuadrante:', 'Score:'],
                            localize=True
                        )
                    ).add_to(m)

            # Añadir marcadores Top-5
            for i, row in merged.iterrows():
                if pd.isna(row.get("lat")) or pd.isna(row.get("lon")):
                    continue
                rank = merged["score"].rank(method="first", ascending=False).loc[i]
                folium.CircleMarker(
                    location=[row["lat"], row["lon"]],
                    radius=3,
                    color="#990000",
                    fill=True,
                    fill_color="#ff4444",
                    fill_opacity=0.9,
                    popup=(f"Top {int(rank)}<br>Cuadrante: {row['cuadrante_id']}<br>Score: {row['score']:.4f}"),
                    tooltip=f"#{int(rank)} · {row['score']:.4f}",
                ).add_to(m)

            # Mostrar también una tabla con top5
            st.table(merged[["cuadrante_id", "score", "lat", "lon"]].assign(score=lambda d: d["score"].round(4)))

            # Renderizar mapa en Streamlit
            html_map = m._repr_html_()
            components.html(html_map, height=600)

# Botón de cerrar sesión al final del sidebar
auth_utils.renderizar_logout_sidebar()
