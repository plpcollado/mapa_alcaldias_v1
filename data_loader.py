import pandas as pd
import streamlit as st

@st.cache_data
def load_data(path="df_streamlit.csv", for_stmap=False):
    """
    Carga y limpia el dataset base de incidentes.
    
    Parámetros:
        path (str): ruta del archivo CSV.
        for_stmap (bool): si True, renombra las columnas para usar con st.map().
    
    Retorna:
        pd.DataFrame: datos listos para visualización.
    """
    try:
        # 1️⃣ Leer el CSV
        df = pd.read_csv(path)
        st.info(f"Archivo cargado: {len(df)} registros totales.")
        
        # Forma automática de detectar y renombrar columnas de latitud y longitud, por ejemplo que se llamen "lat" y "lon"
        lat_cols = [col for col in df.columns if 'lat' in col.lower()]
        lon_cols = [col for col in df.columns if 'lon' in col.lower()]
        if lat_cols and lon_cols:
            df = df.rename(columns={lat_cols[0]: "latitud", lon_cols[0]: "longitud"})
        else:
            st.warning("No se encontraron columnas de latitud/longitud. Asegúrate de que existan.") 

        # 2️⃣ Eliminar filas sin coordenadas válidas
        df = df.dropna(subset=["latitud", "longitud"])
        st.success(f"Datos limpios: {len(df)} registros con coordenadas válidas.")

        # 3️⃣ Si se usará con st.map(), crear columnas compatibles
        if for_stmap:
            df = df.rename(columns={"latitud": "latitude", "longitud": "longitude"})
            st.caption("🗺️ Columnas renombradas a 'latitude' y 'longitude' para st.map().")
        
        return df

    except Exception as e:
        st.error(f"Error al cargar el dataset: {e}")
        return pd.DataFrame()
