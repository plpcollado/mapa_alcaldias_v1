# data_loader.py
# -----------------------------------------------------------------------------
# MÓDULO DE CARGA Y PROCESAMIENTO DE DATOS
# -----------------------------------------------------------------------------
import pandas as pd
import streamlit as st
import numpy as np

def process_hour_crimes_data(df):
    """
    Procesa el archivo hour_crimes_optimized.csv para compatibilidad total.
    Renombra columnas para que coincidan con lo que esperan las visualizaciones.
    """
    # Renombrar columnas con sufijo _N a nombres sin sufijo para uso en la app
    rename_map = {
        'latitud_N': 'latitud',
        'longitud_N': 'longitud',
        'alcaldia_hecho_N': 'alcaldia_hecho',
        'delito_N': 'delito',
        'anio_hecho_N': 'anio_hecho',
        'mes_hecho_N': 'mes_hecho_num'
    }
    
    df.rename(columns=rename_map, inplace=True)
    
    # Usar la columna 'hora' existente y renombrarla a 'hora_hecho_h'
    if 'hora' in df.columns:
        df.rename(columns={'hora': 'hora_hecho_h'}, inplace=True)
        df['hora_hecho_h'] = pd.to_numeric(df['hora_hecho_h'], errors='coerce')
    
    # Asegurar que dia_semana esté en el formato correcto
    if 'dia_semana' in df.columns:
        dias_ordenados = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"]
        df['dia_semana'] = pd.Categorical(df['dia_semana'], categories=dias_ordenados, ordered=True)
    
    # Crear columna 'Violento' si no existe (CRUCIAL para que Análisis Inicial no falle)
    if 'CATEGORIA' in df.columns:
        df['Violento'] = np.where(
            df['CATEGORIA'].astype(str).str.upper() == 'NO VIOLENTOS',
            'No Violento',
            'Violento'
        )
        # Convertir a string o category para evitar problemas con Altair
        df['Violento'] = df['Violento'].astype(str)
    
    return df

@st.cache_data
def load_data(path="hour_crimes_optimized.csv"):
    """
    Función Universal: Carga siempre el dataset optimizado.
    Si una página antigua pide 'df_streamlit.csv', se le redirige al archivo optimizado.
    """
    # Forzamos siempre el uso del archivo real
    real_path = "hour_crimes_optimized.csv"
    
    try:
        # Cargar columnas necesarias para AMBAS páginas (Mapa y Análisis)
        usecols = [
            'latitud_N', 'longitud_N', 'alcaldia_hecho_N', 'delito_N',
            'anio_hecho_N', 'mes_hecho_N', 'hora', 'dia_semana', 'CATEGORIA'
        ]
        
        # Tipos de datos para optimizar memoria
        dtype = {
            'alcaldia_hecho_N': 'category',
            'delito_N': 'category',
            'dia_semana': 'category',
            'CATEGORIA': 'category',
            'anio_hecho_N': 'int16',
            'mes_hecho_N': 'int8',
            'hora': 'float32',
            'latitud_N': 'float32',
            'longitud_N': 'float32'
        }
        
        data = pd.read_csv(real_path, usecols=usecols, dtype=dtype, low_memory=False)
        
        if not data.empty:
            data_limpio = process_hour_crimes_data(data)
            # Limpieza básica de coordenadas
            data_limpio = data_limpio.dropna(subset=["latitud", "longitud"])
            return data_limpio
        else:
            return pd.DataFrame()
            
    except FileNotFoundError:
         st.error(f"❌ Archivo no encontrado: {real_path}")
         return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error en data_loader: {e}")
        return pd.DataFrame()