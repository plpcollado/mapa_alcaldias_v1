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
# Ambas secciones (Dummy y Prod) usan los colores de config.py
from config import PALETA_PRINCIPAL, ESCALA_ROJOS


'''
# --------------------------------------------------------------------------
# --- SECCIÓN 1: CÓDIGO DE PRODUCCIÓN (PARA DATASET COMPLETO Y CUADRANTES) ---
# --------------------------------------------------------------------------
# Este bloque contiene todas las funciones del notebook para los mapas
# coropléticos.
# --------------------------------------------------------------------------

from matplotlib.colors import ListedColormap
from folium.plugins import BeautifyIcon

# --- Funciones Helper del Notebook ---

def load_polygons(path_or_url: str, crs: int = 4326) -> gpd.GeoDataFrame:
    """Carga un shapefile o archivo geoespacial y asegura que tenga el CRS correcto."""
    gdf = gpd.read_file(path_or_url)
    return gdf.set_crs(crs) if gdf.crs is None else gdf.to_crs(crs)


def clean_events(df: pd.DataFrame, lat_col: str, lon_col: str) -> pd.DataFrame:
    """Limpia los datos de coordenadas de eventos (latitud/longitud)."""
    out = df.copy()
    out[lon_col] = out[lon_col].astype(str).str.replace(",", ".", regex=False)
    out[lat_col] = out[lat_col].astype(str).str.replace(",", ".", regex=False)
    out[lon_col] = pd.to_numeric(out[lon_col], errors="coerce")
    out[lat_col] = pd.to_numeric(out[lat_col], errors="coerce")
    return out.dropna(subset=[lon_col, lat_col])


def to_points(events: pd.DataFrame, lat_col: str, lon_col: str, crs: int = 4326) -> gpd.GeoDataFrame:
    """Convierte un DataFrame con coordenadas (lat/lon) en un GeoDataFrame de puntos."""
    return gpd.GeoDataFrame(
        events,
        geometry=gpd.points_from_xy(events[lon_col], events[lat_col]),
        crs=crs
    )


def tag_points_with_polygons(points: gpd.GeoDataFrame, polygons: gpd.GeoDataFrame, predicate: str = "within") -> gpd.GeoDataFrame:
    """Relaciona cada punto con el polígono en el que se encuentra (ej. cuadrante, zona, etc.)"""
    # Asegurarse que ambos GDF tengan el mismo CRS
    polygons = polygons.to_crs(points.crs)
    
    # Usar solo las columnas necesarias para el join
    poly_cols_to_use = ["cuadrante_id", "geometry"]
    if "sector" in polygons.columns:
        poly_cols_to_use.append("sector")
        
    tagged = gpd.sjoin(
        points,
        polygons[poly_cols_to_use],
        how="left",
        predicate=predicate
    )
    if "index_right" in tagged.columns:
        tagged = tagged.drop(columns=["index_right"])
    return tagged

# --- Función de procesamiento de datos (La que faltaba) ---
def calculate_percentage_by_cuadrante(data, cuadrantes_gdf, specific_hour):
    """
    Calcula el % de delitos violentos por cuadrante para una hora específica.
    Este es el pre-procesamiento que tu notebook hacía antes de 'make_violent_crime_percentage_map'.
    """
    st.info(f"Procesando datos para la hora: {specific_hour}")
    
    # 1. Filtrar data por hora
    data_hora = data[data['hora_hecho_h'] == specific_hour].copy()
    if data_hora.empty:
        st.warning(f"No hay datos para la hora {specific_hour}")
        return cuadrantes_gdf.assign(violent_crime_percentage=0.0)

    # 2. Convertir eventos a GeoDataFrame
    event_points = to_points(data_hora, lat_col='latitud', lon_col='longitud')

    # 3. Etiquetar puntos con polígonos (cuadrantes)
    tagged_events = tag_points_with_polygons(event_points, cuadrantes_gdf)

    # 4. Calcular total de delitos por cuadrante
    total_delitos = tagged_events.groupby('cuadrante_id').size().reset_index(name='total_delitos')
    
    # 5. Calcular delitos violentos por cuadrante
    violentos = tagged_events[tagged_events['CATEGORIA'] != 'No violentos']
    total_violentos = violentos.groupby('cuadrante_id').size().reset_index(name='delitos_violentos')
    
    # 6. Unir todo al GDF de cuadrantes
    cuadrantes_stats = cuadrantes_gdf.merge(total_delitos, on='cuadrante_id', how='left')
    cuadrantes_stats = cuadrantes_stats.merge(total_violentos, on='cuadrante_id', how='left')
    
    cuadrantes_stats['total_delitos'] = cuadrantes_stats['total_delitos'].fillna(0)
    cuadrantes_stats['delitos_violentos'] = cuadrantes_stats['delitos_violentos'].fillna(0)
    
    # 7. Calcular porcentaje
    cuadrantes_stats['violent_crime_percentage'] = (
        (cuadrantes_stats['delitos_violentos'] / cuadrantes_stats['total_delitos']) * 100
    ).fillna(0).replace([np.inf, -np.inf], 0)
    
    return cuadrantes_stats


# --- Función de renderizado de mapa (Copiada 1:1 del Notebook y Corregida) ---

def make_violent_crime_percentage_map(
    poly_gdf,
    title,
    tiles="CartoDB positron",
    center=(19.4326, -99.1332),
    zoom_start=11,
    bounds_gdf=None,
    k_classes=5,
    legend_font_px=18,
    legend_title_px=20,
    top5_hex=PALETA_PRINCIPAL[1], # <-- CORREGIDO: Usar color de config.py
    color_mode="fixed_quintiles",
    fixed_edges=None,
    continuous_cmap=None,
):
    """Renderiza un mapa de porcentaje de delitos violentos con distintas escalas de color."""

    gdf_plot = poly_gdf.copy()
    if gdf_plot.crs is not None and str(gdf_plot.crs).lower() not in ("epsg:4326", "wgs84"):
        gdf_plot = gdf_plot.to_crs(epsg=4326)

    if bounds_gdf is None:
        bounds_ref = gdf_plot
    else:
        bounds_ref = bounds_gdf
        if bounds_ref.crs is not None and str(bounds_ref.crs).lower() not in ("epsg:4326", "wgs84"):
            bounds_ref = bounds_ref.to_crs(epsg=4326)

    m = folium.Map(
        tiles=tiles,
        location=center,
        zoom_start=zoom_start,
        max_bounds=True,
    )

    minx, miny, maxx, maxy = bounds_ref.total_bounds
    m.fit_bounds([[miny, minx], [maxy, maxx]])
    m.get_root().html.add_child(
        folium.Element(f"<script>{m.get_name()}.setView([{center[0]},{center[1]}], {zoom_start});</script>")
    )

    col = "violent_crime_percentage"
    s = pd.to_numeric(gdf_plot[col], errors="coerce")
    s_valid = s.replace([np.inf, -np.inf], np.nan).dropna()
    if s_valid.empty:
        return m

    # --- CORREGIDO: Usar ESCALA_ROJOS de config.py ---
    base_cmap = ListedColormap(ESCALA_ROJOS, name="custom_reds")
    legend_kwargs = {"caption": "Porcentaje de delitos violentos (%)", "loc": "topright"}

    m.get_root().header.add_child(
        folium.Element(
            f"""
    <style>
      .legend, .legend * {{ font-size: {legend_font_px}px !important; }}
      .legend .legend-title {{ font-size: {legend_title_px}px !important; font-weight: 800 !important; }}
      .leaflet-control {{ z-index: 1000; }}
    </style>
    """
        )
    )

    mode = (color_mode or "fixed_quintiles").lower()

    if mode == "continuous":
        # --- CORREGIDO: Usar base_cmap (de config.py) ---
        cmap_obj = continuous_cmap if continuous_cmap is not None else base_cmap
        vmin = float(s_valid.min())
        vmax = float(s_valid.max())
        if np.isclose(vmin, vmax):
            vmin -= 0.5
            vmax += 0.5

        gdf_plot.explore(
            column=col,
            cmap=cmap_obj,
            legend=True,
            vmin=vmin,
            vmax=vmax,
            m=m,
            name="Porcentaje de crímenes violentos",
            tooltip=["cuadrante_id", "sector", col],
            style_kwds=dict(color="#555", weight=1, fillOpacity=0.6),
            highlight_kwds=dict(color="#000", weight=2, fillOpacity=0.8),
            legend_kwds=legend_kwargs,
        )

    else:
        if mode == "quantiles":
            qs = np.linspace(0, 1, k_classes + 1)
            edges = np.unique(s_valid.quantile(qs).to_numpy().round(10))
            if edges.size < 2:
                v = float(s_valid.median())
                edges = np.array([v - 0.5, v + 0.5])
            labels = [f"{edges[i]:.1f}–{edges[i + 1]:.1f}%" for i in range(edges.size - 1)]
        else:
            edges = np.arange(0, 101, 20, dtype=float) if fixed_edges is None else np.asarray(fixed_edges, dtype=float)
            min_val = float(s_valid.min())
            max_val = float(s_valid.max())
            while min_val < edges[0]:
                edges = np.insert(edges, 0, edges[0] - 20)
            while max_val > edges[-1]:
                edges = np.append(edges, edges[-1] + 20)
            labels = [f"{edges[i]:.0f}–{edges[i + 1]:.0f}%" for i in range(len(edges) - 1)]

        gdf_plot["__bin__"] = pd.cut(
            s,
            bins=edges,
            include_lowest=True,
            labels=labels,
            right=True,
        ).astype(str)

        if len(labels) == 0:
            return m

        color_samples = [base_cmap(x) for x in np.linspace(0, 1, len(labels))]
        cmap_obj = ListedColormap(color_samples, name=f"custom_reds_{len(labels)}")

        gdf_plot.explore(
            column="__bin__",
            categorical=True,
            categories=labels,
            cmap=cmap_obj,
            legend=True,
            m=m,
            name="Porcentaje de crímenes violentos",
            tooltip=["cuadrante_id", "sector", col],
            style_kwds=dict(color="#555", weight=1, fillOpacity=0.6),
            highlight_kwds=dict(color="#000", weight=2, fillOpacity=0.8),
            legend_kwds=legend_kwargs,
        )

    title_html = f"""
      <div style="
        position:absolute; top:10px; left:50%; transform:translateX(-50%);
        z-index: 1100; pointer-events: none;">
        <div style="
          background: rgba(255,255,255,0.92); padding: 6px 12px; border-radius: 8px;
          box-shadow: 0 2px 6px rgba(0,0,0,.25); font-size: 20px; font-weight: 700;">
          {title}
        </div>
      </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    top_5 = gdf_plot.nlargest(5, col)
    for i, (_, row) in enumerate(top_5.iterrows(), start=1):
        geom = row.geometry
        point = geom.representative_point() if geom.geom_type == "MultiPolygon" else geom.centroid
        icono = BeautifyIcon(
            icon="fa-shield",
            prefix="fa",
            icon_shape="marker",
            background_color=top5_hex,
            text_color="#ffffff",
            border_color="#000000",
            border_width=1,
            inner_icon_style="font-size:12px;",
        )
        folium.Marker(
            location=[point.y, point.x],
            popup=(
                f"<b>Top {i}</b><br>"
                f"<b>Cuadrante:</b> {row.get('cuadrante_id','')}<br>"
                f"<b>Sector:</b> {row.get('sector','')}<br>"
                f"<b>Porcentaje violento:</b> {row.get(col,0):.2f}%"
            ),
            tooltip=f"#{i} · {row.get(col,0):.2f}%",
            icon=icono,
        ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m

# --- Función de Carga Principal (Producción) ---
@st.cache_data
def create_notebook_map(data, map_choice, url_cuadrantes):
    """
    Función principal que la App llamará.
    Carga los polígonos, calcula los datos y genera el mapa seleccionado.
    """
    
    # 1. Cargar polígonos (cacheado)
    try:
        cuadrantes_gdf = load_polygons(url_cuadrantes)
    except Exception as e:
        st.error(f"Error al cargar GDF de cuadrantes: {e}")
        return folium.Map(location=[19.4326, -99.1332], zoom_start=11)
    
    # 2. Asignar hora y título
    if map_choice == "Mapa 6:00":
        hour = 6
        title = "Porcentaje Crímenes Violentos por Cuadrante - 06:00"
    elif map_choice == "Mapa 12:00":
        hour = 12
        title = "Porcentaje Crímenes Violentos por Cuadrante - 12:00"
    else: # map_choice == "Mapa 21:00"
        hour = 21
        title = "Porcentaje Crímenes Violentos por Cuadrante - 21:00"
        
    # 3. Calcular datos (pesado, pero cacheado por 'create_notebook_map')
    poly_with_percentage = calculate_percentage_by_cuadrante(data, cuadrantes_gdf, hour)
    
    # 4. Renderizar mapa
    folium_map = make_violent_crime_percentage_map(
        poly_with_percentage, 
        title,
        bounds_gdf=cuadrantes_gdf # Usar los límites generales para el zoom
    )
    
    return folium_map

'''

# --------------------------------------------------------------------------
# --- SECCIÓN 2: CÓDIGO DE DESARROLLO (PARA 'df_streamlit.csv') ---
# --------------------------------------------------------------------------
# Este bloque es el que está ACTIVO.
# Provee el mapa simple de Puntos/Heatmap sobre ALCALDÍAS.
# --------------------------------------------------------------------------

@st.cache_data
def load_geojson(url, local_backup="limite-de-las-alcaldias.json"):
    """Carga el GeoJSON de ALCALDÍAS desde una URL; si falla, usa una copia local."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        st.success("✅ GeoJSON de Alcaldías cargado correctamente")
        return gpd.read_file(BytesIO(response.content))
    except Exception as e:
        st.warning(f"⚠️ No se pudo cargar GeoJSON de alcaldías desde la web ({e}). Intentando archivo local...")
        try:
            return gpd.read_file(local_backup)
        except Exception as e2:
            st.error(f"❌ Error al cargar el GeoJSON local de alcaldías: {e2}")
            st.stop()
            
def render_folium_map(df, delegaciones, show_points=True, show_heatmap=True):
    """Construye un mapa Folium simple (Puntos/Heatmap) con límites de alcaldías."""
    
    if not df.empty:
        map_center = [df["latitud"].mean(), df["longitud"].mean()]
    else:
        map_center = [19.4326, -99.1332] # Centro CDMX

    m = folium.Map(location=map_center, zoom_start=11, tiles="Cartodb positron")

    # 1. Capa de límites de alcaldías
    folium.GeoJson(
        delegaciones,
        name="Límite de alcaldías CDMX",
        style_function=lambda x: {"color": "gray", "weight": 1, "fillOpacity": 0.05},
        tooltip=folium.GeoJsonTooltip(fields=["NOMGEO"], aliases=["Alcaldía:"]),
    ).add_to(m)

    df_map = df[["latitud", "longitud"]].dropna()
    locations = list(zip(df_map["latitud"], df_map["longitud"]))

    # 2. Capa de Heatmap
    if show_heatmap and not df_map.empty:
        HeatMap(locations, radius=12, blur=10).add_to(m)

    # 3. Capa de Puntos (Círculos)
    if show_points and not df_map.empty:
        # --- CORREGIDO: Usar el color principal de la paleta ---
        color_puntos = PALETA_PRINCIPAL[0] # El rojo principal
        
        for loc in locations:
            folium.CircleMarker(
                location=loc,
                radius=1,
                color=color_puntos,
                fill=True,
                fill_color=color_puntos,
                fill_opacity=0.6
            ).add_to(m)

    return m