# Librerías necesarias para el funcionamiento del archivo
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

# configuración de la página
st.set_page_config(
    page_title="Análisis Detallado - Dashboard Delitos CDMX",
    page_icon="🔍",
    layout="wide",
)

# Control de acceso: solo usuarios privilegiados
auth_utils.requiere_autenticacion(user_types=["privilegiado"]) 

# títulos
st.title("Análisis Detallado")
st.subheader("Visualización de Predicciones, Clustering e Índice de Desarrollo Social (IDS) por Cuadrante")

st.markdown("---")

# Carga de las predicciones a dataframe
@st.cache_data
def load_predictions(path: str) -> pd.DataFrame:
    if path.endswith(".parquet"):
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path, parse_dates=["ds"]) 
        
    df = df.rename(columns={c: c.strip() for c in df.columns})
    if "yhat_N_cuadrante" in df.columns:
        df = df.rename(columns={"yhat_N_cuadrante": "yhat"})
    
    if "cuadrante_id" in df.columns:
        try:
            df["cuadrante_id"] = df["cuadrante_id"].astype(str).str.replace('.0', '', regex=False)
        except Exception:
            df["cuadrante_id"] = df["cuadrante_id"].astype(str)
            
    return df

# Carga de los polígonos de las alcaldías
@st.cache_data
def load_polygons(url: str) -> gpd.GeoDataFrame:
    try:
        gdf = gpd.read_file(url)
        cols = gdf.columns
        cuadrante_col = next((c for c in cols if c.lower() == 'cuadrante_id'), None)
        if not cuadrante_col:
            cuadrante_col = next((c for c in cols if c.lower() == 'id'), None)
        
        if cuadrante_col:
            gdf = gdf.rename(columns={cuadrante_col: "cuadrante_id"})
            try:
                gdf["cuadrante_id"] = gdf["cuadrante_id"].astype(float).astype(int).astype(str)
            except:
                gdf["cuadrante_id"] = gdf["cuadrante_id"].astype(str)
            
            if gdf.crs and gdf.crs.to_string() != "EPSG:4326":
                gdf = gdf.to_crs("EPSG:4326")
            return gdf
    except Exception:
        pass
    return None

# cargar los datos del clustering realizado
@st.cache_data
def load_clusters_data(path: str = "clusters_cuadrantes.csv") -> pd.DataFrame:
    try:
        if os.path.exists(path):
            df = pd.read_csv(path)
            df['cuadrante_id'] = df['cuadrante_id'].astype(float).astype(int).astype(str)
            return df
    except Exception:
        pass
    return pd.DataFrame(columns=['cuadrante_id', 'cluster_kmeans'])

# cargar los datos del IDS para mapeo
@st.cache_data
def load_idsm_data(path: str = "idsm_cuadrantes.csv") -> pd.DataFrame:
    try:
        if os.path.exists(path):
            df = pd.read_csv(path)
            df['cuadrante_id'] = df['cuadrante_id'].astype(float).astype(int).astype(str)
            return df
    except Exception:
        pass
    return pd.DataFrame(columns=['cuadrante_id', 'valor_ids', 'estrato_ids'])


@st.cache_data
def load_cuadrante_centroids(features_csv: str = None, joblib_path: str = None, geojson_url: str = None) -> pd.DataFrame:
    if joblib_path and os.path.exists(joblib_path):
        try:
            mapping = joblib.load(joblib_path)
            rows = []
            for k, v in mapping.items():
                try:
                    geom = getattr(v, "geometry", v)
                    if hasattr(geom, "centroid"):
                        c = geom.centroid
                        rows.append({"cuadrante_id": str(k), "lat": float(c.y), "lon": float(c.x)})
                        continue
                except Exception:
                    pass
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

    if features_csv and os.path.exists(features_csv):
        try:
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
                out = out.groupby("cuadrante_id")["lat", "lon"].mean().reset_index()
                return out
        except Exception:
            pass

    if geojson_url:
        try:
            gdf = gpd.read_file(geojson_url)
            cols = gdf.columns
            cuadrante_col = next((c for c in cols if c.lower() == 'cuadrante_id'), None)
            if not cuadrante_col:
                cuadrante_col = next((c for c in cols if c.lower() == 'id'), None)
            
            if cuadrante_col:
                gdf["centroid"] = gdf.geometry.centroid
                gdf["lat"] = gdf["centroid"].y
                gdf["lon"] = gdf["centroid"].x
                out = gdf[[cuadrante_col, "lat", "lon"]].rename(columns={cuadrante_col: "cuadrante_id"})
                try:
                    out["cuadrante_id"] = out["cuadrante_id"].astype(float).astype(int).astype(str)
                except Exception:
                    out["cuadrante_id"] = out["cuadrante_id"].astype(str)
                return out
        except Exception:
            pass

    return pd.DataFrame(columns=["cuadrante_id", "lat", "lon"]) 

# Carga de datos
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

# Inicializar estado de sesión
if 'last_date' not in st.session_state:
    st.session_state.last_date = sel_date
if 'show_clusters' not in st.session_state:
    st.session_state.show_clusters = False
if 'show_idsm' not in st.session_state:
    st.session_state.show_idsm = False

# Resetear si cambió la fecha
date_changed = st.session_state.last_date != sel_date
if date_changed:
    st.session_state.show_clusters = False
    st.session_state.show_idsm = False
    st.session_state.last_date = sel_date

show_clusters = st.sidebar.checkbox(
    "Mostrar Clusters (Perfiles Delictivos)", 
    value=False if date_changed else st.session_state.show_clusters,
    help="Visualiza los 10 perfiles delictivos identificados por clustering",
    key=f"cb_clusters_{sel_date}"
)
show_idsm = st.sidebar.checkbox(
    "Mostrar IDS (Desarrollo Social)", 
    value=False if date_changed else st.session_state.show_idsm,
    help="Visualiza el Índice de Desarrollo Social por cuadrante",
    key=f"cb_idsm_{sel_date}"
)

if not date_changed:
    st.session_state.show_clusters = show_clusters
    st.session_state.show_idsm = show_idsm
else:
    show_clusters = False
    show_idsm = False

show_prediction = not (show_clusters or show_idsm)

# Mensaje informativo en Sidebar
if show_clusters or show_idsm:
    st.sidebar.markdown(
        """
        <div style="background-color: rgba(159, 34, 65, 0.05); color: #555; padding: 10px; border-radius: 5px; font-size: 14px; margin-top: 10px;">
            ⚠️ Predicción Top-5 oculta mientras las capas adicionales estén activas
        </div>
        """,
        unsafe_allow_html=True
    )

# Título dinámico según la visualización activa
if show_prediction:
    map_title = f"Top-5 Cuadrantes con mayor probabilidad de violencia para el **{sel_date}**"
else:
    active_layers = []
    if show_clusters:
        active_layers.append("Perfiles Delictivos")
    if show_idsm:
        active_layers.append("IDS")
    
    layers_text = " + ".join(active_layers)
    map_title = f"Visualización de {layers_text} por Cuadrante"

st.markdown(f"### {map_title}")

# Cuadro informativo de Predicción (Estilo Gris personalizado SIN emoji)
if show_prediction:
    st.markdown(
        """
        <div style="padding: 12px 15px; background-color: #f8f9fa; border-left: 5px solid #6c757d; border-radius: 4px; margin-bottom: 15px;">
            <div style="display: flex; align-items: center;">
                <span style="color: #333; font-size: 14px;"><b>Visualizando Predicción Top-5</b>: Los 5 cuadrantes con mayor probabilidad de violencia para la fecha seleccionada</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# Filtrar por fecha
df_date = preds[preds["ds"].dt.date == sel_date].copy()
if df_date.empty:
    st.info("No hay predicciones para la fecha seleccionada.")
else:
    if "yhat" in df_date.columns:
        score_col = "yhat"
    else:
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

        geojson_url = "https://raw.githubusercontent.com/plpcollado/TC3001_Team5/main/cuadrantes.geojson"
        
        centroids = load_cuadrante_centroids(geojson_url=geojson_url)
        gdf_polygons = load_polygons(geojson_url)
        
        # Update: Invertir colores para Cluster 0 y Cluster 1
        cluster_profiles = {
            0: {
                'nombre': 'Perfil 1: Muy Alto Volumen - Baja Violencia',
                'descripcion': '~1584 eventos/mes, 17.7% violentos. Muy alto volumen delictivo pero proporción de violencia baja.',
                'color': '#6F7271' # Gris (antes guinda)
            },
            1: {
                'nombre': 'Perfil 2: Alto Volumen - Alta Violencia',
                'descripcion': '~1475 eventos/mes, 38.7% violentos. Mayor proporción de delitos violentos - ZONAS PRIORITARIAS.',
                'color': '#9F2241' # Guinda (antes gris)
            },
            2: {
                'nombre': 'Perfil 3: Volumen Medio - Violencia Elevada',
                'descripcion': '~721 eventos/mes, 34.1% violentos. Violencia concentrada con volumen medio.',
                'color': '#BC955C' 
            },
            3: {
                'nombre': 'Perfil 4: Bajo Volumen - Concentración Temporal',
                'descripcion': '~534 eventos/mes, 19.3% violentos. Mayor concentración en horarios/días específicos.',
                'color': '#235B4E' 
            }
        }
        
        clusters_data = load_clusters_data() if show_clusters else pd.DataFrame()
        idsm_data = load_idsm_data() if show_idsm else pd.DataFrame()

        merged = top5.merge(centroids, on="cuadrante_id", how="left")

        # Barra de Color para IDS (Barra Superior Ancha) - Solo si IDS activo
        if show_idsm:
            st.markdown(
                "<div style='padding: 10px 15px; background-color: #f8f9fa; border-radius: 5px; margin: 12px 0; border-left: 5px solid #41B6C4;'>"
                "<div style='display: flex; align-items: center; gap: 15px; width: 100%;'>"
                "<span style='font-size: 14px; font-weight: bold; color: #333; white-space: nowrap;'>IDS:</span>"
                "<div style='flex: 1; height: 25px; background: linear-gradient(to right, #FFFFD9, #C7E9B4, #41B6C4, #225EA8, #081D58); border-radius: 4px;'></div>"
                "<div style='display: flex; flex-direction: column; align-items: flex-end;'>"
                "<span style='font-size: 11px; color: #666; white-space: nowrap;'><b>Bajo</b> → Desarrollo Social → <b>Alto</b></span>"
                "<span style='font-size: 10px; color: #888; font-style: italic; white-space: nowrap;'>| Gris = Sin datos</span>"
                "</div>"
                "</div>"
                "</div>",
                unsafe_allow_html=True
            )

        if not merged["lat"].notna().any():
            st.warning("No se encontraron coordenadas para los cuadrantes (intenta proporcionar 'cuadrante_features_N7.csv' o el joblib mapping). Se mostrará la tabla únicamente.")
            st.table(merged)
        else:
            center_lat = merged["lat"].dropna().mean() if merged["lat"].notna().any() else 19.4326
            center_lon = merged["lon"].dropna().mean() if merged["lon"].notna().any() else -99.1332

            m = folium.Map(location=[center_lat, center_lon], zoom_start=11, tiles="Cartodb positron")

            # ========== CAPAS BASE ===========
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

            # ========== CAPA DE PREDICCIÓN ===========
            if show_prediction and gdf_polygons is not None:
                top5_ids = merged["cuadrante_id"].unique()
                subset = gdf_polygons[gdf_polygons["cuadrante_id"].isin(top5_ids)].copy()
                
                # Paleta de colores solicitada
                fill_color_pred = "#9F2241" # Rojo oscuro
                circle_color_pred = "#235B4E" # Verde oscuro

                if not subset.empty:
                    subset = subset.merge(merged[["cuadrante_id", "score"]], on="cuadrante_id", how="left")
                    
                    folium.GeoJson(
                        subset,
                        name="Límites Top 5",
                        style_function=lambda x: {
                            'fillColor': fill_color_pred,
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

                for i, row in merged.iterrows():
                    if pd.isna(row.get("lat")) or pd.isna(row.get("lon")):
                        continue
                    rank = merged["score"].rank(method="first", ascending=False).loc[i]
                    folium.CircleMarker(
                        location=[row["lat"], row["lon"]],
                        radius=8,
                        color=circle_color_pred,
                        fill=True,
                        fill_color=circle_color_pred,
                        fill_opacity=0.9,
                        popup=(f"<b>Top {int(rank)}</b><br>Cuadrante: {row['cuadrante_id']}<br>Score: {row['score']:.4f}"),
                        tooltip=f"Predicción #{int(rank)} · {row['score']:.4f}",
                        weight=2
                    ).add_to(m)

            # ========== CAPA IDS (Desarrollo Social) ===========
            if show_idsm and not idsm_data.empty and gdf_polygons is not None:
                gdf_idsm = gdf_polygons.merge(idsm_data, on='cuadrante_id', how='inner')
                
                if not gdf_idsm.empty:
                    gdf_idsm_valid = gdf_idsm[gdf_idsm['valor_ids'].notna()].copy()
                    
                    if not gdf_idsm_valid.empty:
                        min_ids = gdf_idsm_valid['valor_ids'].min()
                        max_ids = gdf_idsm_valid['valor_ids'].max()
                    else:
                        min_ids = max_ids = 0
                    
                    colormap = cm.get_cmap('YlGnBu')
                    idsm_layer = folium.FeatureGroup(name='📊 IDS (Desarrollo Social)', show=True)
                    
                    for idx, row in gdf_idsm.iterrows():
                        is_nan = pd.isna(row['valor_ids'])
                        
                        if is_nan:
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
                    
                    # Leyenda IDSM flotante sobre el mapa (misma posición que clusters)
                    ids_legend_html = f'''
                    <div style="position: fixed; 
                                top: 10px; right: 10px; width: 220px; height: auto; 
                                background-color: white; z-index:9998; font-size:12px;
                                border:2px solid grey; border-radius: 5px; padding: 10px;
                                box-shadow: 0 0 5px rgba(0,0,0,0.2);">
                    <div style="display: flex; align-items: center; margin-bottom: 5px;">
                        <span style="font-size: 14px;">📊</span> 
                        <span style="font-weight: bold; margin-left: 5px;">IDS (Desarrollo Social)</span>
                    </div>
                    <div style="margin-top: 5px; height: 20px; background: linear-gradient(to right, #FFFFD9, #C7E9B4, #41B6C4, #225EA8, #081D58); border-radius: 3px;"></div>
                    <div style="display: flex; justify-content: space-between; margin-top: 2px; font-size: 10px; color: #333;">
                        <span>{min_ids:.2f}</span>
                        <span>{(min_ids + max_ids) / 2:.2f}</span>
                        <span>{max_ids:.2f}</span>
                    </div>
                    <p style="margin-top: 6px; font-size: 10px; color: #666; text-align: center; margin-bottom: 0;">
                        Mayor valor = Mayor desarrollo social
                    </p>
                    </div>
                    '''
                    m.get_root().html.add_child(folium.Element(ids_legend_html))

            # ========== CAPA CLUSTERS (Perfiles Delictivos) ===========
            if show_clusters and not clusters_data.empty and gdf_polygons is not None:
                gdf_clusters = gdf_polygons.merge(clusters_data, on='cuadrante_id', how='inner')
                
                if not gdf_clusters.empty:
                    # Update: Paleta de colores invertida para 0 y 1
                    cluster_colors = {
                        0: '#6F7271', # Gris (antes guinda)
                        1: '#9F2241', # Guinda (antes gris)
                        2: '#BC955C', 
                        3: '#235B4E'  
                    }
                    
                    cluster_layer = folium.FeatureGroup(name='🎯 Clusters (Perfiles)', show=True)
                    
                    for idx, row in gdf_clusters.iterrows():
                        cluster_id = int(row['cluster_kmeans'])
                        color = cluster_colors.get(cluster_id, '#999999')
                        centroid = row['geometry'].centroid
                        
                        popup_html = f"""
                        <div style="font-family: Arial; font-size: 12px;">
                            <b style="color: {color};">Cluster {cluster_id}</b><br>
                            Cuadrante: {row['cuadrante_id']}
                        </div>
                        """
                        
                        folium.CircleMarker(
                            location=[centroid.y, centroid.x],
                            radius=3,
                            popup=folium.Popup(popup_html, max_width=200),
                            tooltip=f"Cluster {cluster_id}",
                            color=color,
                            fillColor=color,
                            fillOpacity=0.85,
                            weight=1.2
                        ).add_to(cluster_layer)
                    
                    cluster_layer.add_to(m)
                    
                    # Leyenda de clusters pegada arriba a la derecha (Z-index mayor para tapar IDS si ambos están activos)
                    cluster_legend_html = '''
                    <div style="position: fixed; 
                                top: 10px; right: 10px; width: 280px; height: auto; 
                                background-color: white; z-index:9999; font-size:13px;
                                border:2px solid grey; border-radius: 5px; padding: 10px;
                                box-shadow: 0 0 5px rgba(0,0,0,0.2);">
                    <p style="margin: 0; font-weight: bold; text-align: center; margin-bottom: 8px;">Perfiles Delictivos</p>
                    '''
                    
                    for cluster_id in sorted(cluster_colors.keys()):
                        color = cluster_colors[cluster_id]
                        profile = cluster_profiles[cluster_id]
                        # Usar el color del cluster para el borde y el icono
                        cluster_legend_html += f'''
                        <div style="margin: 6px 0; padding: 6px; border-left: 4px solid {color}; background-color: rgba(159, 34, 65, 0.05);">
                            <div style="display: flex; align-items: center;">
                                <div style="width: 12px; height: 12px; background-color: {color}; border-radius: 50%; margin-right: 6px;"></div>
                                <b style="color: {color};">Cluster {cluster_id}: {profile['nombre']}</b>
                            </div>
                            <p style="margin: 4px 0 0 18px; font-size: 11px; color: #555;">{profile['descripcion']}</p>
                        </div>
                        '''
                    
                    cluster_legend_html += '</div>'
                    m.get_root().html.add_child(folium.Element(cluster_legend_html))

            html_map = m._repr_html_()
            components.html(html_map, height=600)

            if show_clusters:
                # Título sin emoji
                st.markdown("#### Perfiles Delictivos")
                cols = st.columns(4)
                
                # Tarjetas actualizadas con colores invertidos para 0 y 1
                cluster_cards = {
                    0: {'color': '#6F7271', 'label': 'Perfil 1', 'desc': 'Muy alto volumen, baja violencia', 'pct': '17.7%'}, # Gris
                    1: {'color': '#9F2241', 'label': 'Perfil 2 🚨', 'desc': 'Alto volumen, alta violencia', 'pct': '38.7%'}, # Guinda
                    2: {'color': '#BC955C', 'label': 'Perfil 3', 'desc': 'Volumen medio, violencia elevada', 'pct': '34.1%'},
                    3: {'color': '#235B4E', 'label': 'Perfil 4', 'desc': 'Bajo volumen, concentración temporal', 'pct': '19.3%'}
                }
                
                for idx, (cluster_id, card) in enumerate(cluster_cards.items()):
                    with cols[idx]:
                        # Altura ajustada a 140px, estilo no compacto
                        st.markdown(
                            f"<div style='padding: 16px; background-color: {card['color']}18; border-left: 6px solid {card['color']}; border-radius: 6px; height: 140px; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 0 2px 4px rgba(0,0,0,0.08);'>"
                            f"<div>"
                            f"<div style='display: flex; align-items: center; margin-bottom: 8px;'>"
                            f"<span style='width: 22px; height: 22px; background-color: {card['color']}; border-radius: 50%; display: inline-block; margin-right: 10px;'></span>"
                            f"<b style='font-size: 16px; color: {card['color']};'>{card['label']}</b>"
                            f"</div>"
                            f"<p style='font-size: 13px; color: #444; margin: 6px 0; line-height: 1.5;'>{card['desc']}</p>"
                            f"</div>"
                            f"<p style='font-size: 15px; font-weight: bold; color: {card['color']}; margin: 0;'>{card['pct']} violentos</p>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                st.markdown("---")

            st.table(merged[["cuadrante_id", "score", "lat", "lon"]].assign(score=lambda d: d["score"].round(4)))

# Botón de cerrar sesión al final del sidebar
auth_utils.renderizar_logout_sidebar()