# data_loader.py
# -----------------------------------------------------------------------------
# MÓDULO DE CARGA Y PROCESAMIENTO DE DATOS
# -----------------------------------------------------------------------------
import pandas as pd
import streamlit as st
import numpy as np


'''
# --------------------------------------------------------------------------
# --- SECCIÓN 1: CÓDIGO DE PRODUCCIÓN (PARA DATASET COMPLETO) ---
# --------------------------------------------------------------------------
# Este bloque contiene todas las funciones originales del notebook y la
# función load_data para cargar el dataset completo desde GitHub.
# Para activarlo:

# --------------------------------------------------------------------------

# --- Funciones de preprocesamiento (Copiadas 1:1 del Notebook) ---

def imputar_centroides(df):
    df = df.copy()
    df["latitud_N"] = pd.to_numeric(
        df["latitud"].replace("SIN DATO", pd.NA), errors="coerce"
    )
    df["longitud_N"] = pd.to_numeric(
        df["longitud"].replace("SIN DATO", pd.NA), errors="coerce"
    )
    centroides = (
        df.dropna(subset=["latitud_N", "longitud_N"])
        .groupby(["alcaldia_hecho", "delito"])
        .agg({"latitud_N": "mean", "longitud_N": "mean"})
    )
    df["lat_centroide"] = df.set_index(["alcaldia_hecho", "delito"]).index.map(
        centroides["latitud_N"]
    )
    df["lon_centroide"] = df.set_index(["alcaldia_hecho", "delito"]).index.map(
        centroides["longitud_N"]
    )
    df.loc[df["latitud_N"].isna(), "latitud_N"] = df.loc[df["latitud_N"].isna(), "lat_centroide"]
    df.loc[df["longitud_N"].isna(), "longitud_N"] = df.loc[df["longitud_N"].isna(), "lon_centroide"]
    df = df.drop(columns=["lat_centroide", "lon_centroide"])
    return df.copy()

def _to_datetime_safe(s, fmt=None):
  return pd.to_datetime(s, errors='coerce', format=fmt)

def _strip_accents_upper(text):
  if pd.isna(text):
    return text
  repl = (("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"))
  for a, b in repl:
    text = text.replace(a, b).replace(a.upper(), b.upper())
  return text

def _normalize_text_series(s):
    return (
        s.astype(str)
        .apply(_strip_accents_upper)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )

def categorizar(df):
    df = df.copy()
    col_delito = "delito_N"
    if col_delito not in df.columns:
        st.error("No se encontró la columna 'delito_N' para categorizar.")
        return df

    delitos_unicos = df[col_delito].unique()
    df_delitos_unicos = pd.DataFrame(delitos_unicos, columns=[col_delito])

    df_robo = df_delitos_unicos[df_delitos_unicos[col_delito].str.contains("ROBO", case=False, na=False)]
    df_robo_violencia = df_robo[df_robo[col_delito].str.contains("CON VIOLENCIA", case=False, na=False)]
    df_homicidio = df_delitos_unicos[df_delitos_unicos[col_delito].str.contains("HOMICIDIO", case=False, na=False)]
    df_feminicidio = df_delitos_unicos[df_delitos_unicos[col_delito].str.contains("FEMINICIDIO", case=False, na=False)]
    df_hom_fem = pd.concat([df_homicidio, df_feminicidio])
    df_lesiones = df_delitos_unicos[df_delitos_unicos[col_delito].str.contains("INTENCIONALES", case=False, na=False)]
    df_lesiones2 = df_delitos_unicos[df_delitos_unicos[col_delito].str.contains("DOLOSAS", case=False, na=False)]
    df_lesionescomplete = pd.concat([df_lesiones, df_lesiones2])
    df_secuestro = df_delitos_unicos[df_delitos_unicos[col_delito].str.contains("SECUESTRO", case=False, na=False)]
    df_sexual = df_delitos_unicos[df_delitos_unicos[col_delito].str.contains("SEXUAL", case=False, na=False)]
    df_homicidio = df_homicidio[df_homicidio[col_delito] != "ACOSO SEXUAL"]
    df_violacion = df_delitos_unicos[df_delitos_unicos[col_delito].str.contains("VIOLACION", case=False, na=False)]
    df_trata = df_delitos_unicos[df_delitos_unicos[col_delito].str.contains("TRATA", case=False, na=False)]
    df_otros_violentos = pd.concat([df_sexual, df_violacion, df_trata])

    df["CATEGORIA"] = None
    df.loc[df[col_delito].isin(df_hom_fem[col_delito]), "CATEGORIA"] = "Homicidio/Feminicidio"
    df.loc[df[col_delito].isin(df_robo[col_delito]), "CATEGORIA"] = "Robo"
    df.loc[df[col_delito].isin(df_lesionescomplete[col_delito]), "CATEGORIA"] = "Lesiones"
    df.loc[df[col_delito].isin(df_secuestro[col_delito]), "CATEGORIA"] = "Secuestro"
    df.loc[df[col_delito].isin(df_otros_violentos[col_delito]), "CATEGORIA"] = "Otros"
    df.loc[df["CATEGORIA"].isna(), "CATEGORIA"] = "No violentos"
    
    df['Violento'] = np.where(
        df['CATEGORIA'] == 'No violentos',
        'No Violento',
        'Violento'
    )
    return df.copy()

# --- Variables Globales (del Notebook, necesarias para preparedata) ---
cols_texto = [
    "delito", "competencia", "alcaldia_hecho", "colonia_hecho",
    "alcaldia_catalogo", "colonia_catalogo", "sector", "agencia", "unidad_investigacion"
]

cols_drop = [
    "fecha_inicio", "fecha_hecho_dt", "hora_inicio", "hora_hecho",
    "hora_inicio_dt", "hora_hecho_dt", "fecha_inicio_dt",
    "latitud", "longitud", "competencia", "colonia_hecho", "agencia", 
    "unidad_investigacion", "sector"
] + [c for c in cols_texto if c != "alcaldia_hecho" and c != "colonia_catalogo" and c != "delito"]


dias_map = {
    'Monday': 'LUNES', 'Tuesday': 'MARTES', 'Wednesday': 'MIERCOLES',
    'Thursday': 'JUEVES', 'Friday': 'VIERNES', 'Saturday': 'SABADO', 'Sunday': 'DOMINGO'
}
orden_dias = ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO", "DOMINGO"]

# --- Función 'preparedata' (Copiada 1:1 del Notebook) ---
def preparedata(df):
    df = df.copy()
    df["fecha_inicio_dt"] = _to_datetime_safe(df.get("fecha_inicio"))
    df["fecha_hecho_dt"] = _to_datetime_safe(df.get("fecha_hecho"))
    df["hora_inicio_dt"] = _to_datetime_safe(df.get("hora_inicio"), "%H:%M:%S")
    df["hora_hecho_dt"] = _to_datetime_safe(df.get("hora_hecho"), "%H:%M:%S")
    for col in cols_texto:
        if col in df.columns:
            df[col+"_N"] = _normalize_text_series(df[col])
    df["anio_inicio_N"] = df["fecha_inicio_dt"].dt.year.astype("Int64")
    df["mes_inicio_N"] = df["fecha_inicio_dt"].dt.month.astype("Int64")
    df["anio_hecho_N"] = df["fecha_hecho_dt"].dt.year.astype("Int64")
    df["mes_hecho_N"] = df["fecha_hecho_dt"].dt.month.astype("Int64")
    df["hora_num"] = df["hora_hecho_dt"].dt.hour
    df["dia_semana"] = df["fecha_hecho_dt"].dt.day_name().map(dias_map)
    df["dia_semana"] = pd.Categorical(df["dia_semana"], categories=orden_dias, ordered=True)
    df = imputar_centroides(df)
    df = df.drop(columns=[c for c in cols_drop if c in df.columns])
    df = df.drop_duplicates()
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype("category")
    df = categorizar(df)
    for col in cols_texto:
        col_n = col + "_N"
        if col_n in df.columns:
            if "SIN DATO" not in df[col_n].cat.categories:
                 df[col_n] = df[col_n].cat.add_categories(["SIN DATO"])
            df[col_n] = df[col_n].fillna("SIN DATO")
    
    # Renombrar columnas a los nombres finales que usará la App
    df = df.rename(columns={
        "latitud_N": "latitud",
        "longitud_N": "longitud",
        "alcaldia_hecho_N": "alcaldia_hecho",
        "colonia_catalogo_N": "colonia_catalogo",
        "delito_N": "delito",
        "hora_num": "hora_hecho_h",
        "anio_hecho_N": "anio_hecho",
        "mes_hecho_N": "mes_hecho_num"
    })
    return df.copy()

# --- Función principal de carga (Producción) ---
@st.cache_data
def load_data(path=None): # path se ignora, usa la URL
    """
    Carga y procesa el dataset COMPLETO desde GitHub.
    """
    st.info("Iniciando carga del dataset completo...")
    URL_DATOS_COMPLETOS = "https://github.com/tu-usuario/tu-repo/raw/main/df_delitos_final_para_proyecto.csv"
    try:
        data = pd.read_csv(URL_DATOS_COMPLETOS)
        st.success(f"Datos completos cargados: {len(data)} registros.")
    except Exception as e:
        st.error(f"Error al cargar el dataset completo desde GitHub: {e}")
        return pd.DataFrame()

    if not data.empty:
        st.info("Aplicando procesamiento 'preparedata'...")
        # Aplicamos la función completa y guardamos como 'data_limpio'
        data_limpio = preparedata(data)
        
        data_limpio = data_limpio.dropna(subset=["latitud", "longitud"])
        st.success(f"Procesamiento finalizado. {len(data_limpio)} registros válidos para mapa.")
    else:
        data_limpio = pd.DataFrame()
    
    return data_limpio
'''


# --------------------------------------------------------------------------
# --- SECCIÓN 2: CÓDIGO DE DESARROLLO (PARA 'df_streamlit.csv') ---
# --------------------------------------------------------------------------
# Este bloque es el que está ACTIVO.
# Carga 'df_streamlit.csv' y aplica una adaptación de 'categorizar'.
# --------------------------------------------------------------------------

def categorizar_dummy(df):
    """
    Versión adaptada de 'categorizar' para el df_streamlit.csv.
    Usa la columna 'delito' (que renombramos desde 'categoria_delito').
    """
    df = df.copy()
    col_delito = "delito" # Usamos la columna 'delito' que creamos
    
    if col_delito not in df.columns:
        st.error("No se encontró la columna 'delito' para categorizar.")
        return df

    delitos_unicos = df[col_delito].unique()
    df_delitos_unicos = pd.DataFrame(delitos_unicos, columns=[col_delito])

    # Lógica de categorización (copiada 1:1 del notebook)
    df_robo = df_delitos_unicos[df_delitos_unicos[col_delito].str.contains("ROBO", case=False, na=False)]
    df_homicidio = df_delitos_unicos[df_delitos_unicos[col_delito].str.contains("HOMICIDIO", case=False, na=False)]
    df_feminicidio = df_delitos_unicos[df_delitos_unicos[col_delito].str.contains("FEMINICIDIO", case=False, na=False)]
    df_hom_fem = pd.concat([df_homicidio, df_feminicidio])
    df_lesiones = df_delitos_unicos[df_delitos_unicos[col_delito].str.contains("INTENCIONALES", case=False, na=False)]
    df_lesiones2 = df_delitos_unicos[df_delitos_unicos[col_delito].str.contains("DOLOSAS", case=False, na=False)]
    df_lesionescomplete = pd.concat([df_lesiones, df_lesiones2])
    df_secuestro = df_delitos_unicos[df_delitos_unicos[col_delito].str.contains("SECUESTRO", case=False, na=False)]
    df_sexual = df_delitos_unicos[df_delitos_unicos[col_delito].str.contains("SEXUAL", case=False, na=False)]
    if not df_homicidio.empty and 'ACOSO SEXUAL' in df_homicidio[col_delito].values:
        df_homicidio = df_homicidio[df_homicidio[col_delito] != "ACOSO SEXUAL"]
    df_violacion = df_delitos_unicos[df_delitos_unicos[col_delito].str.contains("VIOLACION", case=False, na=False)]
    df_trata = df_delitos_unicos[df_delitos_unicos[col_delito].str.contains("TRATA", case=False, na=False)]
    df_otros_violentos = pd.concat([df_sexual, df_violacion, df_trata])

    df["CATEGORIA"] = None
    df.loc[df[col_delito].isin(df_hom_fem[col_delito]), "CATEGORIA"] = "Homicidio/Feminicidio"
    df.loc[df[col_delito].isin(df_robo[col_delito]), "CATEGORIA"] = "Robo"
    df.loc[df[col_delito].isin(df_lesionescomplete[col_delito]), "CATEGORIA"] = "Lesiones"
    df.loc[df[col_delito].isin(df_secuestro[col_delito]), "CATEGORIA"] = "Secuestro"
    df.loc[df[col_delito].isin(df_otros_violentos[col_delito]), "CATEGORIA"] = "Otros"
    
    # La columna 'categoria_delito' original (ej. "DELITO DE BAJO IMPACTO") no
    # coincidirá con las violentas, por lo que 'categorizar' las marcará como None.
    # Las asignamos a "No violentos"
    df.loc[df["CATEGORIA"].isna(), "CATEGORIA"] = "No violentos"
    
    # Crear la columna 'Violento' (necesaria para plot_utils)
    df['Violento'] = np.where(
        df['CATEGORIA'] == 'No violentos',
        'No Violento',
        'Violento'
    )
    return df.copy()

def process_dummy_data(df):
    """Limpia y procesa el df_streamlit.csv"""
    df.columns = df.columns.str.lower().str.replace(' ', '_')
    
    # --- ADAPTACIÓN CLAVE ---
    # Renombramos 'categoria_delito' a 'delito' para que 'categorizar_dummy'
    # la pueda procesar y crear la columna 'CATEGORIA' que pediste.
    if 'categoria_delito' in df.columns:
        df = df.rename(columns={'categoria_delito': 'delito'})
    
    # Renombrar columnas para consistencia
    if 'anio_hecho_i' in df.columns:
         df = df.rename(columns={'anio_hecho_i': 'anio_hecho'})

    # Asegurar tipos de dato
    if 'fecha_hecho' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['fecha_hecho']):
         df['fecha_hecho'] = pd.to_datetime(df['fecha_hecho'], errors='coerce')
         
    if 'hora_hecho_h' in df.columns:
        df['hora_hecho_h'] = df['hora_hecho_h'].fillna(-1).astype(int)
    
    # Mapeo de días (por si acaso no viene en mayúsculas)
    if 'dia_semana' in df.columns:
        dias_map = {
            'MONDAY': 'LUNES', 'TUESDAY': 'MARTES', 'WEDNESDAY': 'MIERCOLES',
            'THURSDAY': 'JUEVES', 'FRIDAY': 'VIERNES', 'SATURDAY': 'SABADO', 'SUNDAY': 'DOMINGO'
        }
        df['dia_semana'] = df['dia_semana'].str.upper().map(dias_map).fillna(df['dia_semana'])

    # --- LLAMADA A categorizar_dummy ---
    st.info("Aplicando función 'categorizar_dummy' al dataset...")
    df = categorizar_dummy(df)
    st.success("'CATEGORIA' y 'Violento' creadas para el dummy.")

    return df

# --- Función principal de carga (Activa) ---
@st.cache_data
def load_data(path="df_streamlit.csv"):
    """
    Carga y procesa el dataset DUMMY 'df_streamlit.csv'.
    """
    try:
        st.info("Cargando dataset local (df_streamlit.csv)...")
        data = pd.read_csv(path)
        st.success(f"Datos locales cargados: {len(data)} registros.")
    except Exception as e:
        st.error(f"Error al cargar el dataset local: {e}")
        return pd.DataFrame()

    if not data.empty:
        st.info("Aplicando procesamiento DUMMY...")
        
        # --- CAMBIO SOLICITADO ---
        # Aplicamos la función completa y guardamos como 'data_limpio'
        data_limpio = process_dummy_data(data)
        # --- FIN CAMBIO ---
        
        data_limpio = data_limpio.dropna(subset=["latitud", "longitud"])
        st.success(f"Procesamiento dummy finalizado. {len(data_limpio)} registros válidos.")
    else:
        data_limpio = pd.DataFrame()
    
    # Retornamos el dataframe procesado
    return data_limpio