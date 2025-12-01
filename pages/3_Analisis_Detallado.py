import streamlit as st
import auth_utils
import pandas as pd
import geopandas as gpd
import folium
import joblib
import os
from datetime import date
import streamlit.components.v1 as components
import matplotlib.cm as cm
import matplotlib.colors as mcolors

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
def load_clusters_data(path: str = "clusters_cuadrantes.csv") -> pd.DataFrame:
    """Carga datos de clusters de cuadrantes."""
    try:
        if os.path.exists(path):
            df = pd.read_csv(path)
            # Normalizar ID: convertir "0.0" a "0" para coincidir con GeoJSON
            df['cuadrante_id'] = df['cuadrante_id'].astype(float).astype(int).astype(str)
            return df
    except Exception:
        pass
    return pd.DataFrame(columns=['cuadrante_id', 'cluster_kmeans'])


@st.cache_data
def load_idsm_data(path: str = "idsm_cuadrantes.csv") -> pd.DataFrame:
    """Carga datos de IDSM (Índice de Desarrollo Social)."""
    try:
        if os.path.exists(path):
            df = pd.read_csv(path)
            # Normalizar ID: convertir "0.0" a "0" para coincidir con GeoJSON
            df['cuadrante_id'] = df['cuadrante_id'].astype(float).astype(int).astype(str)
            return df
    except Exception:
        pass
    return pd.DataFrame(columns=['cuadrante_id', 'valor_ids', 'estrato_ids'])


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

st.sidebar.markdown("---")
st.sidebar.markdown("### 🗺️ Capas del Mapa")
st.sidebar.markdown("*Configura las capas a visualizar*")

# Inicializar estado de sesión para controlar el modo
if 'last_date' not in st.session_state:
    st.session_state.last_date = sel_date
if 'show_clusters' not in st.session_state:
    st.session_state.show_clusters = False
if 'show_idsm' not in st.session_state:
    st.session_state.show_idsm = False

# Si cambió la fecha, resetear a modo predicción
date_changed = st.session_state.last_date != sel_date
if date_changed:
    st.session_state.show_clusters = False
    st.session_state.show_idsm = False
    st.session_state.last_date = sel_date

# Checkboxes para capas adicionales (forzar desactivación si cambió la fecha)
show_clusters = st.sidebar.checkbox(
    "Mostrar Clusters (Perfiles Delictivos)", 
    value=False if date_changed else st.session_state.show_clusters,
    help="Visualiza los 10 perfiles delictivos identificados por clustering",
    key=f"cb_clusters_{sel_date}"  # Key única por fecha para forzar reset
)
show_idsm = st.sidebar.checkbox(
    "Mostrar IDSM (Desarrollo Social)", 
    value=False if date_changed else st.session_state.show_idsm,
    help="Visualiza el Índice de Desarrollo Social por cuadrante",
    key=f"cb_idsm_{sel_date}"  # Key única por fecha para forzar reset
)

# Actualizar estado solo si no cambió la fecha
if not date_changed:
    st.session_state.show_clusters = show_clusters
    st.session_state.show_idsm = show_idsm
else:
    # Si cambió la fecha, los checkboxes ya están en False
    show_clusters = False
    show_idsm = False

# Determinar si mostrar predicción (solo si NO hay capas adicionales activas)
show_prediction = not (show_clusters or show_idsm)

# Mensaje informativo
if show_clusters or show_idsm:
    st.sidebar.info("⚠️ Predicción Top-5 oculta mientras las capas adicionales estén activas")

st.markdown(f"### Top-5 Cuadrantes con mayor probabilidad de violencia para el **{sel_date}**")

# Mostrar información de la capa de predicción
if show_prediction:
    st.info("🎯 **Visualizando Predicción Top-5**: Los 5 cuadrantes con mayor probabilidad de violencia para la fecha seleccionada")

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

        # Cargar polígonos y centroides desde URL remota (único necesario)
        geojson_url = "https://raw.githubusercontent.com/plpcollado/TC3001_Team5/main/cuadrantes.geojson"
        
        centroids = load_cuadrante_centroids(geojson_url=geojson_url)
        gdf_polygons = load_polygons(geojson_url)
        
        # Descripciones de perfiles de clusters (según mapeo del notebook)
        # Cluster 0 = Perfil_01, Cluster 1 = Perfil_02, Cluster 2 = Perfil_04, Cluster 3 = Perfil_03
        cluster_profiles = {
            0: {
                'nombre': 'Perfil 1: Muy Alto Volumen - Baja Violencia',
                'descripcion': '~1584 eventos/mes, 17.7% violentos. Muy alto volumen delictivo pero proporción de violencia baja.',
                'color': '#9F2241'
            },
            1: {
                'nombre': 'Perfil 2: Alto Volumen - Alta Violencia',
                'descripcion': '~1475 eventos/mes, 38.7% violentos. Mayor proporción de delitos violentos - ZONAS PRIORITARIAS.',
                'color': '#691C32'
            },
            2: {
                'nombre': 'Perfil 4: Bajo Volumen - Concentración Temporal',
                'descripcion': '~534 eventos/mes, 19.3% violentos. Mayor concentración en horarios/días específicos.',
                'color': '#235B4E'
            },
            3: {
                'nombre': 'Perfil 3: Volumen Medio - Violencia Elevada',
                'descripcion': '~721 eventos/mes, 34.1% violentos. Violencia concentrada con volumen medio.',
                'color': '#BC955C'
            }
        }
        
        # Cargar datos adicionales si las capas están habilitadas
        clusters_data = load_clusters_data() if show_clusters else pd.DataFrame()
        idsm_data = load_idsm_data() if show_idsm else pd.DataFrame()

        merged = top5.merge(centroids, on="cuadrante_id", how="left")

        # Leyenda compacta de IDSM (justo antes del mapa, solo cuando esté activo)
        if show_idsm:
            st.markdown(
                "<div style='padding: 10px 15px; background-color: #f8f9fa; border-radius: 5px; margin: 12px 0; border-left: 5px solid #41B6C4;'>"
                "<div style='display: flex; align-items: center; gap: 20px;'>"
                "<span style='font-size: 14px; font-weight: bold; color: #333;'>📊 IDSM:</span>"
                "<div style='flex: 1; height: 22px; background: linear-gradient(to right, #FFFFD9, #C7E9B4, #41B6C4, #225EA8, #081D58); border-radius: 4px; max-width: 250px;'></div>"
                "<span style='font-size: 12px; color: #666;'><b>Bajo</b> → Desarrollo Social → <b>Alto</b></span>"
                "<span style='font-size: 11px; color: #888; font-style: italic;'>| Gris = Sin datos</span>"
                "</div>"
                "</div>",
                unsafe_allow_html=True
            )

        # Crear mapa con folium
        if not merged["lat"].notna().any():
            st.warning("No se encontraron coordenadas para los cuadrantes (intenta proporcionar 'cuadrante_features_N7.csv' o el joblib mapping). Se mostrará la tabla únicamente.")
            st.table(merged)
        else:
            # Centro del mapa
            center_lat = merged["lat"].dropna().mean() if merged["lat"].notna().any() else 19.4326
            center_lon = merged["lon"].dropna().mean() if merged["lon"].notna().any() else -99.1332

            m = folium.Map(location=[center_lat, center_lon], zoom_start=11, tiles="Cartodb positron")

            # ========== CAPAS BASE (TODOS LOS CUADRANTES) ===========
            # Añadir polígonos de TODOS los cuadrantes (capa base siempre visible)
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

            # ========== CAPA DE PREDICCIÓN (SOLO SI ESTÁ ACTIVA) ===========
            if show_prediction and gdf_polygons is not None:
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

                # Añadir marcadores Top-5 de predicción
                for i, row in merged.iterrows():
                    if pd.isna(row.get("lat")) or pd.isna(row.get("lon")):
                        continue
                    rank = merged["score"].rank(method="first", ascending=False).loc[i]
                    folium.CircleMarker(
                        location=[row["lat"], row["lon"]],
                        radius=8,
                        color="#990000",
                        fill=True,
                        fill_color="#ff4444",
                        fill_opacity=0.9,
                        popup=(f"<b>Top {int(rank)}</b><br>Cuadrante: {row['cuadrante_id']}<br>Score: {row['score']:.4f}"),
                        tooltip=f"Predicción #{int(rank)} · {row['score']:.4f}",
                        weight=2
                    ).add_to(m)

            # ========== CAPA IDSM (Desarrollo Social) ===========
            if show_idsm and not idsm_data.empty and gdf_polygons is not None:
                # Unir polígonos con datos de IDSM
                gdf_idsm = gdf_polygons.merge(idsm_data, on='cuadrante_id', how='inner')
                
                if not gdf_idsm.empty:
                    # Normalizar valores para colores (solo valores no-NaN)
                    gdf_idsm_valid = gdf_idsm[gdf_idsm['valor_ids'].notna()].copy()
                    
                    if not gdf_idsm_valid.empty:
                        min_ids = gdf_idsm_valid['valor_ids'].min()
                        max_ids = gdf_idsm_valid['valor_ids'].max()
                    else:
                        min_ids = max_ids = 0
                    
                    colormap = cm.get_cmap('YlGnBu')
                    idsm_layer = folium.FeatureGroup(name='📊 IDSM (Desarrollo Social)', show=True)
                    
                    for idx, row in gdf_idsm.iterrows():
                        # Verificar si el valor es NaN
                        is_nan = pd.isna(row['valor_ids'])
                        
                        if is_nan:
                            # Polígonos sin datos: gris claro
                            color_hex = '#E0E0E0'
                            popup_html = f"""
                            <div style="font-family: Arial; font-size: 12px;">
                                <b>IDS: Sin datos</b><br>
                                Cuadrante: {row['cuadrante_id']}<br>
                                Estrato: N/A
                            </div>
                            """
                            tooltip_text = "IDS: Sin datos"
                        else:
                            # Polígonos con datos: color según escala
                            normalized_value = (row['valor_ids'] - min_ids) / (max_ids - min_ids) if max_ids > min_ids else 0.5
                            color_rgba = colormap(normalized_value)
                            color_hex = mcolors.rgb2hex(color_rgba[:3])
                            popup_html = f"""
                            <div style="font-family: Arial; font-size: 12px;">
                                <b>IDS: {row['valor_ids']:.3f}</b><br>
                                Cuadrante: {row['cuadrante_id']}<br>
                                Estrato: {row.get('estrato_ids', 'N/A')}
                            </div>
                            """
                            tooltip_text = f"IDS: {row['valor_ids']:.3f}"
                        
                        folium.GeoJson(
                            row['geometry'],
                            style_function=lambda x, color=color_hex: {
                                'fillColor': color,
                                'color': '#555555',
                                'weight': 0.8,
                                'fillOpacity': 0.4
                            },
                            tooltip=tooltip_text,
                            popup=folium.Popup(popup_html, max_width=200)
                        ).add_to(idsm_layer)
                    
                    idsm_layer.add_to(m)
                    
                    # Agregar leyenda de colores IDSM al mapa
                    legend_html = f'''
                    <div style="position: fixed; 
                                bottom: 50px; right: 50px; width: 200px; height: auto; 
                                background-color: white; z-index:9999; font-size:12px;
                                border:2px solid grey; border-radius: 5px; padding: 10px">
                    <p style="margin: 0; font-weight: bold; text-align: center;">📊 IDSM (Desarrollo Social)</p>
                    <div style="margin-top: 8px; height: 20px; background: linear-gradient(to right, #FFFFD9, #C7E9B4, #41B6C4, #225EA8, #081D58); border-radius: 3px;"></div>
                    <div style="display: flex; justify-content: space-between; margin-top: 4px; font-size: 10px;">
                        <span>{min_ids:.2f}</span>
                        <span>{(min_ids + max_ids) / 2:.2f}</span>
                        <span>{max_ids:.2f}</span>
                    </div>
                    <p style="margin-top: 8px; font-size: 10px; color: #666; text-align: center;">
                        Mayor valor = Mayor desarrollo social
                    </p>
                    </div>
                    '''
                    m.get_root().html.add_child(folium.Element(legend_html))

            # ========== CAPA CLUSTERS (Perfiles Delictivos) ===========
            if show_clusters and not clusters_data.empty and gdf_polygons is not None:
                # Unir polígonos con datos de clusters
                gdf_clusters = gdf_polygons.merge(clusters_data, on='cuadrante_id', how='inner')
                
                if not gdf_clusters.empty:
                    # Paleta de colores para 4 clusters (tonos del dashboard)
                    cluster_colors = {
                        0: '#9F2241',  # Rojo principal (dashboard)
                        1: '#691C32',  # Guinda
                        2: '#235B4E',  # Verde oscuro
                        3: '#BC955C'   # Ocre
                    }
                    
                    cluster_layer = folium.FeatureGroup(name='🎯 Clusters (Perfiles)', show=True)
                    
                    for idx, row in gdf_clusters.iterrows():
                        cluster_id = int(row['cluster_kmeans'])
                        color = cluster_colors.get(cluster_id, '#999999')
                        
                        # Calcular centroide
                        centroid = row['geometry'].centroid
                        
                        popup_html = f"""
                        <div style="font-family: Arial; font-size: 12px;">
                            <b style="color: {color};">Cluster {cluster_id}</b><br>
                            Cuadrante: {row['cuadrante_id']}
                        </div>
                        """
                        
                        folium.CircleMarker(
                            location=[centroid.y, centroid.x],
                            radius=3,  # Más pequeño (antes era 5)
                            popup=folium.Popup(popup_html, max_width=200),
                            tooltip=f"Cluster {cluster_id}",
                            color=color,
                            fillColor=color,
                            fillOpacity=0.85,
                            weight=1.2
                        ).add_to(cluster_layer)
                    
                    cluster_layer.add_to(m)
                    
                    # Agregar leyenda de clusters al mapa con perfiles
                    cluster_legend_html = '''
                    <div style="position: fixed; 
                                bottom: 50px; right: 50px; width: 280px; height: auto; 
                                background-color: white; z-index:9999; font-size:11px;
                                border:2px solid grey; border-radius: 5px; padding: 10px">
                    <p style="margin: 0; font-weight: bold; text-align: center; margin-bottom: 8px;">🎯 Perfiles Delictivos</p>
                    '''
                    
                    for cluster_id in sorted(cluster_colors.keys()):
                        color = cluster_colors[cluster_id]
                        profile = cluster_profiles[cluster_id]
                        cluster_legend_html += f'''
                        <div style="margin: 6px 0; padding: 6px; border-left: 4px solid {color}; background-color: rgba(159, 34, 65, 0.05);">
                            <div style="display: flex; align-items: center;">
                                <div style="width: 12px; height: 12px; background-color: {color}; border-radius: 50%; margin-right: 6px;"></div>
                                <b style="color: {color};">Cluster {cluster_id}: {profile['nombre']}</b>
                            </div>
                            <p style="margin: 4px 0 0 18px; font-size: 10px; color: #555;">{profile['descripcion']}</p>
                        </div>
                        '''
                    
                    cluster_legend_html += '</div>'
                    m.get_root().html.add_child(folium.Element(cluster_legend_html))

            # Renderizar mapa en Streamlit
            html_map = m._repr_html_()
            components.html(html_map, height=600)

            # Leyenda de clusters con tarjetas individuales (inmediatamente debajo del mapa)
            if show_clusters:
                st.markdown("#### 🎯 Perfiles Delictivos")
                cols = st.columns(4)
                
                cluster_cards = {
                    0: {'color': '#9F2241', 'label': 'Perfil 1', 'desc': 'Muy alto volumen, baja violencia', 'pct': '17.7%'},
                    1: {'color': '#691C32', 'label': 'Perfil 2 🚨', 'desc': 'Alto volumen, alta violencia', 'pct': '38.7%'},
                    2: {'color': '#235B4E', 'label': 'Perfil 4', 'desc': 'Bajo volumen, concentración temporal', 'pct': '19.3%'},
                    3: {'color': '#BC955C', 'label': 'Perfil 3', 'desc': 'Volumen medio, violencia elevada', 'pct': '34.1%'}
                }
                
                for idx, (cluster_id, card) in enumerate(cluster_cards.items()):
                    with cols[idx]:
                        st.markdown(
                            f"<div style='padding: 16px; background-color: {card['color']}18; border-left: 6px solid {card['color']}; border-radius: 6px; height: 100%; box-shadow: 0 2px 4px rgba(0,0,0,0.08);'>"
                            f"<div style='display: flex; align-items: center; margin-bottom: 8px;'>"
                            f"<span style='width: 22px; height: 22px; background-color: {card['color']}; border-radius: 50%; display: inline-block; margin-right: 10px;'></span>"
                            f"<b style='font-size: 16px; color: {card['color']};'>{card['label']}</b>"
                            f"</div>"
                            f"<p style='font-size: 13px; color: #444; margin: 6px 0; line-height: 1.5;'>{card['desc']}</p>"
                            f"<p style='font-size: 15px; font-weight: bold; color: {card['color']}; margin: 6px 0 0 0;'>{card['pct']} violentos</p>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                st.markdown("---")

            # Mostrar también una tabla con top5
            st.table(merged[["cuadrante_id", "score", "lat", "lon"]].assign(score=lambda d: d["score"].round(4)))

# Botón de cerrar sesión al final del sidebar
auth_utils.renderizar_logout_sidebar()
