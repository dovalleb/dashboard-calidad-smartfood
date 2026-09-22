import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración inicial
st.set_page_config(page_title="Dashboard CAPA - Smart Food Safe", page_icon="🛡️", layout="wide")

st.title("🛡️ Panel de Control - No Conformidades (CAPA)")
st.markdown("Plataforma de análisis dinámico conectada a Smart Food Safe")
st.markdown("---")

# Zona única de carga
st.markdown("### 📥 Carga de Datos")
file_capa = st.file_uploader("Arrastra aquí el reporte exportado (Excel/CSV) desde el módulo CAPA de SFS", type=['xlsx', 'xls', 'csv'])

# Función para leer el archivo dinámicamente
@st.cache_data(show_spinner=False)
def procesar_base(file):
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        
        # Estandarización básica por si hay diferencias de mayúsculas/minúsculas en columnas
        df.columns = df.columns.str.strip().str.upper()
        
        # Intentar convertir columnas que parezcan fechas
        for col in df.columns:
            if 'FECHA' in col or 'DATE' in col:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
                
        return df
    except Exception as e:
        st.error(f"Error al leer el archivo. Verifica el formato. Detalle: {e}")
        return None

if file_capa is not None:
    df = procesar_base(file_capa)
    
    if df is not None and not df.empty:
        st.markdown("---")
        st.markdown("### 🔍 Filtros de Análisis Avanzado")
        
        # Filtros Dinámicos (Se adaptan a las columnas que tenga tu Excel)
        cols = st.columns(4)
        
        # 1. Filtro de Origen (Cliente, Proveedor, Interno)
        origen_col = 'ORIGEN' if 'ORIGEN' in df.columns else (df.columns[3] if len(df.columns) > 3 else None)
        if origen_col:
            origen_filtro = cols[0].multiselect("Origen (Tipo)", options=df[origen_col].dropna().unique(), default=df[origen_col].dropna().unique())
            df = df[df[origen_col].isin(origen_filtro)]

        # 2. Filtro de Estado
        estado_col = 'ESTADO' if 'ESTADO' in df.columns else (df.columns[10] if len(df.columns) > 10 else None)
        if estado_col:
            estado_filtro = cols[1].multiselect("Estado CAPA", options=df[estado_col].dropna().unique(), default=df[estado_col].dropna().unique())
            df = df[df[estado_col].isin(estado_filtro)]
            
        # 3. Filtro de Clasificación/Severidad
        clasif_col = 'CLASIFICACION' if 'CLASIFICACION' in df.columns else (df.columns[9] if len(df.columns) > 9 else None)
        if clasif_col:
            clasif_filtro = cols[2].multiselect("Nivel de Severidad", options=df[clasif_col].dropna().unique(), default=df[clasif_col].dropna().unique())
            df = df[df[clasif_col].isin(clasif_filtro)]
            
        # 4. Filtro de Motivo/Desviación
        motivo_col = 'MOTIVO' if 'MOTIVO' in df.columns else (df.columns[8] if len(df.columns) > 8 else None)
        if motivo_col:
            motivos_lista = df[motivo_col].dropna().unique()
            motivo_filtro = cols[3].multiselect("Motivo Específico", options=motivos_lista, default=motivos_lista)
            df = df[df[motivo_col].isin(motivo_filtro)]

        st.markdown("---")
        
        # --- KPIs ---
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        total_casos = len(df)
        kpi1.metric("Total de Hallazgos Filtrados", total_casos)
        
        if estado_col:
            abiertos = len(df[~df[estado_col].astype(str).str.contains('Cerrad|Closed', case=False, na=False)])
            kpi2.metric("Casos Abiertos / Pendientes", abiertos)
            tasa = ((total_casos - abiertos) / total_casos * 100) if total_casos > 0 else 0
            kpi4.metric("Efectividad de Cierre", f"{tasa:.1f}%")
        else:
            kpi2.metric("Casos Abiertos / Pendientes", "N/A")
            kpi4.metric("Efectividad de Cierre", "N/A")
            
        if clasif_col:
            criticos = len(df[df[clasif_col].astype(str).str.contains('Crítico|Inocuidad|Critical', case=False, na=False)])
            kpi3.metric("Hallazgos Críticos / Inocuidad", criticos)
        else:
            kpi3.metric("Hallazgos Críticos / Inocuidad", "N/A")

        # --- GRÁFICOS ---
        st.markdown("---")
        c1, c2 = st.columns(2)
        
        with c1:
            if motivo_col:
                st.markdown("**Distribución por Motivo / Causa Raíz**")
                df_motivos = df[motivo_col].value_counts().reset_index()
                df_motivos.columns = [motivo_col, 'Cantidad']
                fig1 = px.bar(df_motivos.head(10), x='Cantidad', y=motivo_col, orientation='h', color_discrete_sequence=['#0d9488'])
                fig1.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(t=10))
                st.plotly_chart(fig1, use_container_width=True)
                
        with c2:
            st.markdown("**Trazabilidad por Entidad (Cliente / Proveedor / Línea)**")
            entidad_col = 'CLIENTE_PROVEEDOR' if 'CLIENTE_PROVEEDOR' in df.columns else (df.columns[4] if len(df.columns) > 4 else None)
            if entidad_col:
                df_entidad = df[entidad_col].value_counts().reset_index()
                df_entidad.columns = [entidad_col, 'Cantidad']
                fig2 = px.bar(df_entidad.head(10), x=entidad_col, y='Cantidad', color_discrete_sequence=['#ea580c'])
                fig2.update_layout(xaxis_tickangle=-45, margin=dict(t=10))
                st.plotly_chart(fig2, use_container_width=True)

        # --- TABLA DE DATOS ---
        st.markdown("---")
        st.markdown("**Matriz Detallada de CAPAs (Datos Filtrados)**")
        
        # Intentar ordenar por fecha si existe
        fecha_col = next((col for col in df.columns if 'FECHA' in col or 'DATE' in col), None)
        if fecha_col:
            df = df.sort_values(by=fecha_col, ascending=False)
            
        st.dataframe(df, use_container_width=True, hide_index=True)

else:
    st.info("💡 Por favor, sube el archivo unificado exportado desde Smart Food Safe para activar el panel.")
