import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración inicial de la página
st.set_page_config(page_title="Dashboard de Calidad", page_icon="📋", layout="wide")

st.title("📋 Control Operativo de Calidad")
st.markdown("Monitoreo de No Conformidades - Carga de Datos Dinámica")
st.markdown("---")

# Zona de carga de archivos
col_upload1, col_upload2 = st.columns(2)
with col_upload1:
    file_clientes = st.file_uploader("📥 Subir archivo: Reclamos Clientes (Excel)", type=['xlsx'])
with col_upload2:
    file_proveedores = st.file_uploader("📥 Subir archivo: Estadística Proveedores (Excel)", type=['xlsx'])

# Función para procesar y unificar los datos
@st.cache_data(show_spinner=False)
def procesar_datos(file_cli, file_prov):
    try:
        # Lectura de hojas específicas
        df_cli = pd.read_excel(file_cli, sheet_name='BASE DE DATOS')
        df_prov = pd.read_excel(file_prov, sheet_name='REGISTRO')
        
        # Transformación Clientes
        df_cli['Origen'] = 'Cliente'
        df_cli.rename(columns={'Ano': 'Año', 'Cliente': 'Entidad', 'Status': 'Estado'}, inplace=True)
        
        # Transformación Proveedores
        df_prov['Origen'] = 'Proveedor'
        df_prov.rename(columns={'Proveedor': 'Entidad', 'Clasificación': 'Clasificacion', 'Cantidad ': 'Cantidad'}, inplace=True)
        df_prov['Lote'] = None
        df_prov['Observaciones'] = None
        
        # Consolidación
        cols = ['Fecha', 'Año', 'Origen', 'Entidad', 'Producto', 'Motivo', 'Clasificacion', 'Estado', 'Cantidad', 'Lote', 'Observaciones']
        df_cli = df_cli[cols]
        df_prov = df_prov[cols]
        df_maestra = pd.concat([df_cli, df_prov], ignore_index=True)
        
        # Limpieza estándar
        df_maestra['Fecha'] = pd.to_datetime(df_maestra['Fecha'], errors='coerce')
        df_maestra['Estado'] = df_maestra['Estado'].fillna('Abierto').astype(str).str.capitalize()
        df_maestra['Clasificacion'] = df_maestra['Clasificacion'].fillna('No Definido').astype(str).str.capitalize()
        
        return df_maestra
    except Exception as e:
        st.error(f"Error al procesar los archivos. Verifica que las hojas se llamen 'BASE DE DATOS' y 'REGISTRO'. Detalle: {e}")
        return None

# Lógica principal del Dashboard
if file_clientes is not None and file_proveedores is not None:
    df = procesar_datos(file_clientes, file_proveedores)
    
    if df is not None:
        # --- FILTROS ---
        st.markdown("### Filtros de Análisis")
        col_f1, col_f2, col_f3 = st.columns(3)
        origen_filtro = col_f1.multiselect("Origen", options=df['Origen'].unique(), default=df['Origen'].unique())
        estado_filtro = col_f2.multiselect("Estado", options=df['Estado'].unique(), default=df['Estado'].unique())
        clasif_filtro = col_f3.multiselect("Clasificación", options=df['Clasificacion'].unique(), default=df['Clasificacion'].unique())
        
        df_filtrado = df[
            (df['Origen'].isin(origen_filtro)) & 
            (df['Estado'].isin(estado_filtro)) &
            (df['Clasificacion'].isin(clasif_filtro))
        ]
        
        # --- KPIs ---
        st.markdown("---")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        total_nc = len(df_filtrado)
        abiertas = len(df_filtrado[df_filtrado['Estado'] != 'Cerrado'])
        criticas = len(df_filtrado[df_filtrado['Clasificacion'].isin(['Inocuidad', 'Critico', 'Crítico'])])
        tasa_res = ((total_nc - abiertas) / total_nc * 100) if total_nc > 0 else 0
        
        kpi1.metric("Total de Hallazgos", total_nc)
        kpi2.metric("Casos Abiertos", abiertas)
        kpi3.metric("Eventos de Inocuidad/Críticos", criticas)
        kpi4.metric("Tasa de Resolución", f"{tasa_res:.1f}%")
        
        # --- GRÁFICOS ---
        st.markdown("---")
        chart1, chart2 = st.columns(2)
        
        with chart1:
            st.markdown("**Top 5 Motivos Recurrentes**")
            top_motivos = df_filtrado['Motivo'].value_counts().head(5).reset_index()
            top_motivos.columns = ['Motivo', 'Cantidad']
            fig_bar = px.bar(top_motivos, x='Cantidad', y='Motivo', orientation='h', color_discrete_sequence=['#0f766e'])
            fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with chart2:
            st.markdown("**Distribución por Severidad**")
            clasif_count = df_filtrado['Clasificacion'].value_counts().reset_index()
            clasif_count.columns = ['Clasificacion', 'Cantidad']
            fig_pie = px.pie(clasif_count, values='Cantidad', names='Clasificacion', hole=0.4)
            fig_pie.update_layout(margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig_pie, use_container_width=True)
            
        # --- TABLA DE DETALLE ---
        st.markdown("---")
        st.markdown("**Registro Detallado de No Conformidades**")
        st.dataframe(df_filtrado.sort_values(by='Fecha', ascending=False), use_container_width=True, hide_index=True)

else:
    st.info("💡 Por favor, arrastra y suelta ambos archivos de Excel en las cajas superiores para desplegar los indicadores.")
