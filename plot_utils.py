# Librerías necesarias para el funcionamiento de este archivo
import altair as alt
import pandas as pd
import numpy as np
from config import PALETA_PRINCIPAL, ESCALA_ROJOS, COLORES_STACK

# Definición estándar del eje X para los gráficos
EJE_X_HORAS = alt.Axis(
    values=list(range(0, 24, 2)), 
    labelAngle=0, 
    title='Hora del Día'
)

# GRÁFICOS AUXILIARES

# Gráfico complemento de página Mapa
def plot_delitos_por_alcaldia(data):
    """Gráfica de barras: Conteo de delitos por alcaldía."""
    if data.empty:
        return alt.Chart(pd.DataFrame()).mark_text(text="No hay datos").encode()

    df_plot = data['alcaldia_hecho'].value_counts().reset_index()
    df_plot.columns = ['Alcaldía', 'Total']

    chart = alt.Chart(df_plot).mark_bar(
        color=PALETA_PRINCIPAL[0] 
    ).encode(
        x=alt.X('Total:Q', title='Número de Delitos'),
        y=alt.Y('Alcaldía:N', sort='-x', title='Alcaldía'),
        tooltip=[
            alt.Tooltip('Alcaldía', title='Alcaldía'),
            alt.Tooltip('Total', title='Total de Delitos', format=',')
        ]
    ).properties(
        title='Delitos por Alcaldía',
        height=300 
    ).interactive()

    return chart.configure_axis(
        labelFontSize=11,
        titleFontSize=12
    )

# GRÁFICOS DASHBOARD INICIAL

# Gráfico 1: Barras Apiladas
def plot_crimenes_violentos_por_hora(data):
    """Gráfico 1: Barras apiladas."""
    if data.empty or 'CATEGORIA' not in data.columns:
        return alt.Chart(pd.DataFrame()).mark_text(text="No hay datos").encode()

    df_plot = data[
        (data['hora_hecho_h'].between(0, 23)) &
        (data['CATEGORIA'].astype(str).str.upper().ne('NO VIOLENTOS'))
    ].copy()

    df_aggregated = df_plot.groupby(['hora_hecho_h', 'CATEGORIA']).size().reset_index(name='Total')
    category_order = df_aggregated.groupby('CATEGORIA')['Total'].sum().sort_values(ascending=False).index.tolist()
    
    color_mapping = {
        'Robo': '#98989A',
        'Otros': '#D0C9A3',
        'Lesiones': '#235B4E',
        'Homicidio/Feminicidio': '#9F2241',
        'Secuestro': '#691C32'
    }
    
    color_scale = alt.Scale(
        domain=category_order,
        range=[color_mapping.get(cat, '#98989A') for cat in category_order]
    )
    
    bars = alt.Chart(df_aggregated).mark_bar().encode(
        x=alt.X('hora_hecho_h:O', axis=EJE_X_HORAS),
        y=alt.Y('Total:Q', title='Número de Crímenes', stack='zero'),
        color=alt.Color('CATEGORIA:N', 
                        title='Categoría de crimen',
                        scale=color_scale,
                        legend=alt.Legend(
                            orient='none',
                            legendX=0,
                            legendY=0,
                            direction='vertical',
                            title=None,
                            fillColor='rgba(255, 255, 255, 0.8)',
                            cornerRadius=5,
                            padding=10,
                            labelFontSize=11,
                            symbolSize=100
                        )),
        order=alt.Order('CATEGORIA', sort='descending'),
        tooltip=[
            alt.Tooltip('hora_hecho_h', title='Hora'),
            alt.Tooltip('CATEGORIA', title='Categoría'),
            alt.Tooltip('Total:Q', title='Total', format=',')
        ]
    )
    
    totales = df_aggregated.groupby('hora_hecho_h')['Total'].sum().reset_index()
    if not totales.empty:
        max_data = totales.loc[totales['Total'].idxmax()]
        
        max_text = alt.Chart(pd.DataFrame([max_data])).mark_text(
            dy=-10, fontWeight='bold', color='black', fontSize=10
        ).encode(
            x=alt.X('hora_hecho_h:O'),
            y=alt.Y('Total:Q'),
            text=alt.Text('Total:Q', format=',')
        )
        
        return (bars + max_text).properties(
            height=300
        ).configure_view(
            strokeWidth=0
        ).configure_axis(
            labelFontSize=11,
            titleFontSize=12
        ).configure_title(
            anchor='start',
            offset=20
        ).interactive()
    else:
        return bars.properties(height=300).configure_view(strokeWidth=0).configure_axis(labelFontSize=11, titleFontSize=12)

# Gráfico 2: Áreas apiladas
def plot_volumen_total_violencia_hora(data):
    """Gráfico 2: Área apilada."""
    if data.empty or 'CATEGORIA' not in data.columns:
        return alt.Chart(pd.DataFrame()).mark_text(text="No hay datos").encode()

    df_plot = data[data['hora_hecho_h'].between(0, 23)].copy()
    
    df_plot['Violento'] = np.where(
        df_plot['CATEGORIA'].astype(str).str.upper() == 'NO VIOLENTOS',
        'No Violento',
        'Violento'
    )

    df_grouped = df_plot.groupby(['hora_hecho_h', 'Violento']).size().reset_index(name='Total')
    
    base = alt.Chart(df_grouped).encode(
        x=alt.X('hora_hecho_h:Q', axis=EJE_X_HORAS),
        tooltip=[alt.Tooltip('hora_hecho_h'), alt.Tooltip('Violento'), alt.Tooltip('Total', format=',')]
    )
    
    areas = base.mark_area(opacity=0.8).encode(
        y=alt.Y('Total:Q', title='Número de Delitos', stack='zero'),
        color=alt.Color('Violento', 
            scale=alt.Scale(domain=['No Violento', 'Violento'], range=COLORES_STACK),
            legend=alt.Legend(
                orient='none',
                legendX=10,
                legendY=10,
                direction='vertical',
                title=None,
                fillColor='rgba(255, 255, 255, 0.8)',
                cornerRadius=5,
                padding=10,
                labelFontSize=11,
                symbolSize=100
            )
        ),
        order=alt.Order('Violento', sort='descending')
    )
    
    bands = alt.Chart(pd.DataFrame({'start': [0, 20], 'stop': [6, 24]})).mark_rect(
        color='grey', opacity=0.1
    ).encode(x='start:Q', x2='stop:Q')

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
        height=300
    ).interactive().configure_axis(
        labelFontSize=11,
        titleFontSize=12
    )

# Gráfico 3: Linea + Promedios Móviles
def plot_ratio_violencia_hora(data):
    """Gráfico 3: Línea de Ratio con Leyenda corregida (sin título)."""
    if data.empty or 'CATEGORIA' not in data.columns:
        return alt.Chart(pd.DataFrame()).mark_text(text="No hay datos").encode()

    data_plot = data[data['hora_hecho_h'].between(0, 23)]
    
    totales = data_plot.groupby('hora_hecho_h').size().reindex(range(24), fill_value=0)
    violentos = data_plot[
        data_plot['CATEGORIA'].astype(str).str.upper().ne('NO VIOLENTOS')
    ].groupby('hora_hecho_h').size().reindex(range(24), fill_value=0)
    
    ratio = (violentos / totales.replace(0, np.nan)).fillna(0)
    ratio_smooth = ratio.rolling(window=3, center=True, min_periods=1).mean()
    
    ratio_df = pd.DataFrame({
        "hora": ratio.index,
        "ratio": ratio.values,
        "ratio_smooth": ratio_smooth.values
    })
    
    # Gráfico base
    base = alt.Chart(ratio_df).encode(
        x=alt.X("hora:Q", axis=EJE_X_HORAS)
    )

    # Se define la escala con los nuevos nombres
    legend_scale = alt.Scale(
        domain=["Datos", "Promedio Móvil"],
        range=[PALETA_PRINCIPAL[0], PALETA_PRINCIPAL[1]]
    )

    # Línea original
    line_raw = base.transform_calculate(
        Tipo="'Datos'"
    ).mark_line(
        point={'size': 25}, 
        strokeWidth=1.5
    ).encode(
        y=alt.Y("ratio:Q", title="Proporción de Delitos Violentos", axis=alt.Axis(format='.0%'), scale=alt.Scale(domain=[0, 1])),
        color=alt.Color("Tipo:N", scale=legend_scale, legend=alt.Legend(
            orient='none',
            legendX=120, 
            legendY=5,
            direction='horizontal',
            title=None, 
            fillColor='rgba(255, 255, 255, 0.8)',
            cornerRadius=5,
            padding=5,
            labelFontSize=11,
            symbolSize=100
        )),
        tooltip=[alt.Tooltip("hora:Q"), alt.Tooltip("ratio:Q", format=".1%")]
    )

    # Línea suavizada
    line_smooth = base.transform_calculate(
        Tipo="'Promedio Móvil'"
    ).mark_line(
        strokeWidth=2.5
    ).encode(
        y=alt.Y("ratio_smooth:Q"),
        color=alt.Color("Tipo:N", scale=legend_scale), 
        tooltip=[alt.Tooltip("hora:Q"), alt.Tooltip("ratio_smooth:Q", title="Media Móvil", format=".1%")]
    )

    bands = alt.Chart(pd.DataFrame({'start': [0, 20], 'stop': [6, 24]})).mark_rect(
        color=PALETA_PRINCIPAL[6], opacity=0.12
    ).encode(x='start:Q', x2='stop:Q')

    prom_global = (violentos.sum() / totales.replace(0, np.nan).sum())
    avg_line = alt.Chart(pd.DataFrame({'y': [prom_global]})).mark_rule(
        strokeDash=[4,2], color='black', opacity=0.6
    ).encode(y='y:Q')
    
    text_data = ratio_df[ratio_df['hora'].isin([6, 12, 21])]
    
    text = alt.Chart(text_data).mark_text(
        fontWeight='bold', 
        fontSize=10,
        dy=alt.expr("datum.hora == 12 ? 20 : -15") 
    ).encode(
        x=alt.X('hora:Q'),
        y=alt.Y('ratio:Q'),
        text=alt.Text('ratio:Q', format='.1%')
    )
    
    return (bands + line_raw + line_smooth + avg_line + text).properties(
        height=300
    ).interactive().configure_axis(
        labelFontSize=11,
        titleFontSize=12
    )

# Gráfico 4: Heatmap
def plot_heatmap_dia_hora(data):
    """Heatmap: Porcentaje de delitos violentos por día de la semana y hora."""
    if data.empty:
        return alt.Chart(pd.DataFrame()).mark_text(text="No hay datos").encode()

    data_heatmap = data[data['hora_hecho_h'].between(0, 23)].copy()
    
    if 'dia_semana' in data_heatmap.columns:
        sample_dias = data_heatmap['dia_semana'].dropna().unique()
        if any('Á' in str(d) or 'É' in str(d) for d in sample_dias):
            dias_ordenados = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"]
        else:
            dias_ordenados = ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO", "DOMINGO"]
    else:
        dias_ordenados = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"]
    
    if 'dia_semana' not in data_heatmap.columns or 'CATEGORIA' not in data_heatmap.columns:
        return alt.Chart(pd.DataFrame()).mark_text(text="Faltan columnas necesarias").encode()
    
    if pd.api.types.is_categorical_dtype(data_heatmap['dia_semana']):
        data_heatmap['dia_semana'] = data_heatmap['dia_semana'].astype(str)
    
    total_delitos = data_heatmap.groupby(['dia_semana', 'hora_hecho_h']).size().reset_index(name='Total')
    violentos = data_heatmap[
        data_heatmap['CATEGORIA'].astype(str).str.upper().ne('NO VIOLENTOS')
    ].groupby(['dia_semana', 'hora_hecho_h']).size().reset_index(name='Violentos')
    
    df_plot = total_delitos.merge(violentos, on=['dia_semana', 'hora_hecho_h'], how='left')
    df_plot['Violentos'] = df_plot['Violentos'].fillna(0)
    df_plot['Porcentaje_Violentos'] = (df_plot['Violentos'] / df_plot['Total']).fillna(0)
    
    all_hours = pd.DataFrame({'hora_hecho_h': range(24)})
    all_days = pd.DataFrame({'dia_semana': dias_ordenados})
    grid = all_days.merge(all_hours, how='cross')
    
    df_plot = grid.merge(df_plot, on=['dia_semana', 'hora_hecho_h'], how='left')
    df_plot['Total'] = df_plot['Total'].fillna(0)
    df_plot['Violentos'] = df_plot['Violentos'].fillna(0)
    df_plot['Porcentaje_Violentos'] = df_plot['Porcentaje_Violentos'].fillna(0)

    heatmap = alt.Chart(df_plot).mark_rect().encode(
        x=alt.X('hora_hecho_h:O', axis=EJE_X_HORAS),
        y=alt.Y('dia_semana:O', title='Día de la Semana', sort=dias_ordenados),
        color=alt.Color('Porcentaje_Violentos:Q', 
                        title='% Violentos',
                        scale=alt.Scale(range=ESCALA_ROJOS, domain=[0, 1])), 
        tooltip=[
            alt.Tooltip('dia_semana', title='Día'),
            alt.Tooltip('hora_hecho_h', title='Hora'),
            alt.Tooltip('Porcentaje_Violentos', title='% Violentos', format='.1%')
        ]
    ).interactive()

    return heatmap.properties(
        height=300
    ).configure_axis(
        labelFontSize=11,
        titleFontSize=12
    )

# Gráfico 5: Reloj o Polar
def plot_polar_violencia_hora(data):
    """Gráfico 5: Gráfico polar."""
    if data.empty or 'CATEGORIA' not in data.columns:
        return alt.Chart(pd.DataFrame()).mark_text(text="No hay datos").encode()

    data_plot = data[data['hora_hecho_h'].between(0, 23)]
    totales = data_plot.groupby('hora_hecho_h').size().reindex(range(24), fill_value=0)
    violentos = data_plot[
        data_plot['CATEGORIA'].astype(str).str.upper().ne('NO VIOLENTOS')
    ].groupby('hora_hecho_h').size().reindex(range(24), fill_value=0)
    ratio = (violentos / totales.replace(0, np.nan)).fillna(0)

    ratio_df = ratio.reset_index()
    ratio_df.columns = ['hora', 'ratio']
    ratio_df['hora_label'] = ratio_df['hora'].astype(str).str.zfill(2) + ":00"
    
    # Escala área del gráfico
    ratio_df['ratio_scaled'] = 50 + (ratio_df['ratio'] * 250) 
    
    polar_bars = alt.Chart(ratio_df).mark_arc(stroke='white', tooltip=True).encode(
        theta=alt.Theta("hora:O", title=None, sort=None),
        radius=alt.Radius('ratio_scaled:Q', scale=alt.Scale(type='linear', domain=[0, 250])), 
        radius2=alt.value(40), 
        color=alt.Color("ratio:Q", scale=alt.Scale(range=ESCALA_ROJOS, domain=[0, 1]), legend=None),
        tooltip=[
            alt.Tooltip("hora_label", title="Hora"),
            alt.Tooltip("ratio", title="Proporción Violenta", format=".1%")
        ]
    )

    text_horas = alt.Chart(ratio_df).mark_text(
        fontSize=12,
        fontWeight="bold",
        color="#2c3e50"
    ).encode(
        theta=alt.Theta("hora:O"),
        radius=alt.value(230), 
        text=alt.Text("hora_label:N")
    )

    text_ratio = alt.Chart(ratio_df[ratio_df['ratio'] > 0.15]).mark_text(
        fontSize=9, 
        fontWeight='bold',
        color='white',
        radiusOffset=-10
    ).encode(
        theta=alt.Theta("hora:O"),
        radius=alt.Radius('ratio_scaled:Q', scale=alt.Scale(type='linear')),
        text=alt.Text("ratio:Q", format=".0%")
    )

    chart = (polar_bars + text_horas + text_ratio).properties(
        title="Proporción de delitos violentos por hora",
        width=500,
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