# plot_utils.py
# -----------------------------------------------------------------------------
# MÓDULO DE VISUALIZACIÓN (ALTAIR)
# CORRECCIÓN 7: Se corrige el nombre del método a 'configure_axis_radius' (snake_case)
# -----------------------------------------------------------------------------
import altair as alt
import pandas as pd
import numpy as np
from config import PALETA_PRINCIPAL, ESCALA_ROJOS, COLORES_STACK

# --- Gráficas del Mockup (Simples) ---

def plot_delitos_por_alcaldia(data):
    """Gráfica de barras: Conteo de delitos por alcaldía."""
    if data.empty:
        return alt.Chart(pd.DataFrame()).mark_text(text="No hay datos").encode()

    df_plot = data['alcaldia_hecho'].value_counts().reset_index()
    df_plot.columns = ['Alcaldía', 'Total']

    chart = alt.Chart(df_plot).mark_bar(
        color=PALETA_PRINCIPAL[0] # Color principal (Rojo)
    ).encode(
        x=alt.X('Total:Q', title='Número de Delitos'),
        y=alt.Y('Alcaldía:N', sort='-x', title='Alcaldía'),
        tooltip=[
            alt.Tooltip('Alcaldía', title='Alcaldía'),
            alt.Tooltip('Total', title='Total de Delitos', format=',')
        ]
    ).properties(
        title='Delitos por Alcaldía'
    ).interactive()

    return chart

def plot_proporcion_violencia(data):
    """Gráfica de dona: Proporción de delitos violentos vs. no violentos."""
    if data.empty or 'Violento' not in data.columns:
        return alt.Chart(pd.DataFrame()).mark_text(text="No hay datos").encode()

    df_plot = data['Violento'].value_counts(normalize=True).reset_index()
    df_plot.columns = ['Categoría', 'Porcentaje']
    df_plot['Porcentaje_fmt'] = (df_plot['Porcentaje'] * 100).round(1)

    base = alt.Chart(df_plot).encode(
       theta=alt.Theta("Porcentaje", stack=True)
    )

    # Usar Verde para 'No Violento' y Rojo para 'Violento'
    color_scale = alt.Scale(
        domain=['No Violento', 'Violento'],
        range=[PALETA_PRINCIPAL[1], PALETA_PRINCIPAL[0]] 
    )

    pie = base.mark_arc(outerRadius=120, innerRadius=80).encode(
        color=alt.Color("Categoría", scale=color_scale),
        order=alt.Order("Porcentaje", sort="descending"),
        tooltip=["Categoría", alt.Tooltip("Porcentaje", format=".1%")]
    ).properties(
        title='Proporción Violencia'
    )

    text = base.mark_text(radius=140).encode(
        text=alt.Text("Porcentaje_fmt", format=".1f"),
        order=alt.Order("Porcentaje", sort="descending"),
        color=alt.value("black") 
    )

    return pie + text

def plot_heatmap_dia_hora(data):
    """Heatmap: Delitos por día de la semana y hora."""
    if data.empty:
        return alt.Chart(pd.DataFrame()).mark_text(text="No hay datos").encode()

    data_heatmap = data[data['hora_hecho_h'].between(0, 23)]
    
    dias_ordenados = ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO", "DOMINGO"]
    # Asegurar que 'dia_semana' sea categórica con el orden correcto
    if 'dia_semana' in data_heatmap.columns:
        # Usamos 'astype' por si acaso ya era categórica pero con otro orden
        data_heatmap['dia_semana'] = pd.Categorical(data_heatmap['dia_semana'], categories=dias_ordenados, ordered=True)
    
    # Agrupar en lugar de crosstab para manejar NaNs en el categórico
    df_plot = data_heatmap.groupby(['dia_semana', 'hora_hecho_h']).size().reset_index(name='Total')
    
    # Crear un grid completo para que Altair muestre 0s
    all_hours = pd.DataFrame({'hora_hecho_h': range(24)})
    all_days = pd.DataFrame({'dia_semana': dias_ordenados})
    grid = all_days.merge(all_hours, how='cross')
    
    df_plot = grid.merge(df_plot, on=['dia_semana', 'hora_hecho_h'], how='left').fillna(0)


    heatmap = alt.Chart(df_plot).mark_rect().encode(
        x=alt.X('hora_hecho_h:O', title='Hora del Día', axis=alt.Axis(labels=True, ticks=True)),
        y=alt.Y('dia_semana:O', title='Día de la Semana', sort=dias_ordenados),
        color=alt.Color('Total:Q', 
                        title='Total Delitos',
                        scale=alt.Scale(range=ESCALA_ROJOS)), # Usar escala de rojos
        tooltip=[
            alt.Tooltip('dia_semana', title='Día'),
            alt.Tooltip('hora_hecho_h', title='Hora'),
            alt.Tooltip('Total', title='Total Delitos', format=',')
        ]
    ).properties(
        title='Heatmap de Incidencia (Día vs. Hora)'
    ).interactive()

    return heatmap

# --- Gráficas del Notebook (Traducidas a Altair) ---

def plot_crimenes_violentos_por_hora(data):
    """Gráfico 1 (Notebook): Barras apiladas de crímenes VIOLENTOS por hora."""
    if data.empty or 'CATEGORIA' not in data.columns:
        return alt.Chart(pd.DataFrame()).mark_text(text="No hay datos").encode()

    # Filtrar solo horas válidas y categorías violentas
    df_plot = data[
        (data['hora_hecho_h'].between(0, 23)) &
        (data['CATEGORIA'] != 'No violentos')
    ].copy()

    # Definir orden de categorías para apilar
    category_order = df_plot['CATEGORIA'].value_counts().index.tolist()
    
    # Colores: Asignar colores de PALETA_PRINCIPAL a las categorías
    color_scale = alt.Scale(domain=category_order, range=PALETA_PRINCIPAL)
    
    # Gráfico base
    base = alt.Chart(df_plot).encode(
        x=alt.X('hora_hecho_h:O', title='Hora del Día', axis=alt.Axis(values=list(range(0, 24, 2)))),
        tooltip=[
            alt.Tooltip('hora_hecho_h', title='Hora'),
            alt.Tooltip('CATEGORIA', title='Categoría'),
            alt.Tooltip('count()', title='Total')
        ]
    )
    
    # Barras apiladas
    bars = base.mark_bar().encode(
        y=alt.Y('count()', title='Número de Crímenes', stack='zero'),
        color=alt.Color('CATEGORIA', scale=color_scale),
        order=alt.Order('CATEGORIA', sort='descending')
    )
    
    # Bandas de noche y madrugada
    bands = alt.Chart(pd.DataFrame({'start': [0, 20], 'stop': [6, 24]})).mark_rect(
        color='grey', opacity=0.1
    ).encode(x='start:Q', x2='stop:Q')
    
    # Etiqueta de la hora máxima
    totales = df_plot.groupby('hora_hecho_h').size().reset_index(name='Total')
    if not totales.empty:
        max_data = totales.loc[totales['Total'].idxmax()]
        
        max_text = alt.Chart(pd.DataFrame([max_data])).mark_text(
            dy=-10, fontWeight='bold', color='black', fontSize=9
        ).encode(
            x=alt.X('hora_hecho_h:O'),
            y=alt.Y('Total:Q'),
            text=alt.Text('Total:Q', format=',.0f')
        )
        
        return (bands + bars + max_text).properties(
            title='Frecuencia de Crímenes Violentos por Hora'
        ).interactive()
    
    else:
        # Si no hay datos después de filtrar
        return (bands + bars).properties(
            title='Frecuencia de Crímenes Violentos por Hora'
        ).interactive()


def plot_volumen_total_violencia_hora(data):
    """Gráfico 2 (Notebook): Área apilada de Violentos vs No Violentos."""
    if data.empty or 'Violento' not in data.columns:
        return alt.Chart(pd.DataFrame()).mark_text(text="No hay datos").encode()

    df_plot = data[data['hora_hecho_h'].between(0, 23)]

    # Agrupar por hora y 'Violento'
    df_grouped = df_plot.groupby(['hora_hecho_h', 'Violento']).size().reset_index(name='Total')
    
    # Gráfico base
    base = alt.Chart(df_grouped).encode(
        x=alt.X('hora_hecho_h:Q', title='Hora del Día', axis=alt.Axis(values=list(range(0, 24, 2)))),
        tooltip=[
            alt.Tooltip('hora_hecho_h', title='Hora'),
            alt.Tooltip('Violento', title='Categoría'),
            alt.Tooltip('Total', title='Total', format=',')
        ]
    )
    
    # Áreas apiladas
    areas = base.mark_area(opacity=0.8).encode(
        y=alt.Y('Total:Q', title='Número de Delitos', stack='zero'),
        color=alt.Color('Violento', scale=alt.Scale(domain=['No Violento', 'Violento'], range=COLORES_STACK)),
        order=alt.Order('Violento', sort='descending')
    )
    
    # Bandas de noche y madrugada
    bands = alt.Chart(pd.DataFrame({'start': [0, 20], 'stop': [6, 24]})).mark_rect(
        color='grey', opacity=0.1
    ).encode(x='start:Q', x2='stop:Q')

    # Etiquetas de texto para horas clave
    totales_hora = df_grouped.groupby('hora_hecho_h')['Total'].sum().reset_index()
    text_data = totales_hora[totales_hora['hora_hecho_h'].isin([4, 10, 12, 20])]
    
    text = alt.Chart(text_data).mark_text(
        dy=-10, fontWeight='bold', fontSize=9
    ).encode(
        x=alt.X('hora_hecho_h:Q'),
        y=alt.Y('Total:Q'),
        text=alt.Text('Total:Q', format=',.0f')
    )

    return (bands + areas + text).properties(
        title='Delitos por Hora: Volumen Total y Fracción Violenta'
    ).interactive()

def plot_ratio_violencia_hora(data):
    """Gráfico 3 (Notebook): Línea de Ratio de Violencia (con media móvil)."""
    if data.empty or 'CATEGORIA' not in data.columns:
        return alt.Chart(pd.DataFrame()).mark_text(text="No hay datos").encode()

    data_plot = data[data['hora_hecho_h'].between(0, 23)]
    
    totales = data_plot.groupby('hora_hecho_h').size().reindex(range(24), fill_value=0)
    violentos = data_plot[data_plot['CATEGORIA'] != 'No violentos'].groupby('hora_hecho_h').size().reindex(range(24), fill_value=0)
    
    ratio = (violentos / totales.replace(0, np.nan)).fillna(0)
    ratio_smooth = ratio.rolling(window=3, center=True, min_periods=1).mean()
    
    ratio_df = pd.DataFrame({
        "hora": ratio.index,
        "ratio": ratio.values,
        "ratio_smooth": ratio_smooth.values
    })
    
    # Gráfico base
    base = alt.Chart(ratio_df).encode(
        x=alt.X("hora:Q", title="Hora del Día", axis=alt.Axis(values=list(range(0, 24, 2))))
    )

    # Línea de ratio original
    line_raw = base.mark_line(
        point={'size': 25}, 
        strokeWidth=1.5, 
        color=PALETA_PRINCIPAL[0]
    ).encode(
        y=alt.Y("ratio:Q", title="Proporción de Delitos Violentos", axis=alt.Axis(format='.0%'), scale=alt.Scale(domain=[0, 1])),
        tooltip=[alt.Tooltip("hora:Q"), alt.Tooltip("ratio:Q", format=".1%")]
    )

    # Línea suavizada
    line_smooth = base.mark_line(
        strokeWidth=2.5, color=PALETA_PRINCIPAL[1]
    ).encode(
        y=alt.Y("ratio_smooth:Q"),
        tooltip=[alt.Tooltip("hora:Q"), alt.Tooltip("ratio_smooth:Q", title="Media Móvil", format=".1%")]
    )

    # Bandas de noche y madrugada
    bands = alt.Chart(pd.DataFrame({'start': [0, 20], 'stop': [6, 24]})).mark_rect(
        color=PALETA_PRINCIPAL[6], opacity=0.12 # Color Ocre
    ).encode(x='start:Q', x2='stop:Q')

    # Línea de promedio global
    prom_global = (violentos.sum() / totales.replace(0, np.nan).sum())
    avg_line = alt.Chart(pd.DataFrame({'y': [prom_global]})).mark_rule(
        strokeDash=[4,2], color='black', opacity=0.6
    ).encode(y='y:Q')
    
    # Etiquetas de texto
    text_data = ratio_df[ratio_df['hora'].isin([6, 12, 21])]
    
    text = alt.Chart(text_data).mark_text(
        fontWeight='bold', 
        fontSize=10,
        dy=alt.expr("datum.hora == 12 ? 20 : -15") # Ajuste condicional
    ).encode(
        x=alt.X('hora:Q'),
        y=alt.Y('ratio:Q'),
        text=alt.Text('ratio:Q', format='.1%')
    )
    
    return (bands + line_raw + line_smooth + avg_line + text).properties(
        title='Porcentaje de Crímenes Violentos por Hora'
    ).interactive()

def plot_polar_violencia_hora(data):
    """Gráfico 4/5 (Notebook): Gráfico polar del ratio de violencia."""
    if data.empty or 'CATEGORIA' not in data.columns:
        return alt.Chart(pd.DataFrame()).mark_text(text="No hay datos").encode()

    # --- Preprocesamiento ---
    data_plot = data[data['hora_hecho_h'].between(0, 23)]
    totales = data_plot.groupby('hora_hecho_h').size().reindex(range(24), fill_value=0)
    violentos = data_plot[data_plot['CATEGORIA'] != 'No violentos'].groupby('hora_hecho_h').size().reindex(range(24), fill_value=0)
    ratio = (violentos / totales.replace(0, np.nan)).fillna(0)

    ratio_df = ratio.reset_index()
    ratio_df.columns = ['hora', 'ratio']
    ratio_df['hora_label'] = ratio_df['hora'].astype(str).str.zfill(2) + ":00"

    # --- Base circular ---
    base = alt.Chart(ratio_df).encode(
        theta=alt.Theta("hora:O", title=None, sort=None),
        radius=alt.Radius("ratio:Q", scale=alt.Scale(domain=[0, 1]), title=None),
        color=alt.Color("ratio:Q", scale=alt.Scale(range=ESCALA_ROJOS), legend=None)
    )

    # --- Barras polares ---
    arcs = base.mark_arc(innerRadius=40, outerRadius=220, opacity=0.9).encode(
        tooltip=[
            alt.Tooltip("hora_label", title="Hora"),
            alt.Tooltip("ratio", title="Proporción Violenta", format=".1%")
        ]
    )

    # --- Etiquetas radiales (horas) ---
    text_horas = alt.Chart(ratio_df).mark_text(
        radius=250,  # Más grande para que no se corten
        fontSize=10,
        fontWeight="bold",
        color="gray"
    ).encode(
        theta=alt.Theta("hora:O"),
        text=alt.Text("hora_label:N")
    )

    # --- Etiquetas interiores (porcentajes) ---
    text_ratio = alt.Chart(ratio_df).mark_text(
        fontSize=9,
        fontWeight='bold',
        color='black',
        radiusOffset=10  # ✅ desplazamiento correcto (parámetro válido)
    ).encode(
        theta=alt.Theta("hora:O"),
        radius=alt.Radius("ratio:Q", scale=alt.Scale(domain=[0, 1]), title=None),
        text=alt.Text("ratio:Q", format=".0%")
    ).transform_filter(
        alt.datum.ratio > 0
    )

    # --- Unión y configuración ---
    chart = (arcs + text_horas + text_ratio).properties(
        title="Proporción de delitos violentos por hora",
        width=500,   # más grande para mejor visibilidad
        height=500
    ).configure_view(
        stroke=None
    ).configure_title(
        fontSize=16,
        fontWeight='bold',
        anchor='middle',
        color=PALETA_PRINCIPAL[0]
    )

    return chart
