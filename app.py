import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Dashboard Calidad - Tribu Food", page_icon="📊", layout="wide")

# --- ESTILOS VISUALES: MODO OSCURO, NEÓN Y BOTONES (PILLS) ---
st.markdown("""
<style>
.stApp { background-color: #0a0e17; }
.stMarkdown, p, label, .stTab { color: #e2e8f0 !important; }
h1, h2, h3 { color: #ff6a00 !important; text-shadow: 0px 0px 12px rgba(255, 106, 0, 0.8); }
[data-testid="stMetricValue"] { color: #39ff14 !important; text-shadow: 0px 0px 12px rgba(57, 255, 20, 0.8); }
[data-testid="stMetricLabel"] { color: #00f3ff !important; text-shadow: 0px 0px 8px rgba(0, 243, 255, 0.5); }
hr { border-bottom: 1px solid #ff6a00; box-shadow: 0px 0px 8px #ff6a00; }
.stAlert { background-color: #111827; border: 1px solid #ff6a00; }
/* Estilo para las pestañas */
.stTabs [data-baseweb="tab-list"] { background-color: #0a0e17; }
.stTabs [data-baseweb="tab"] { color: #00f3ff; font-weight: bold; }
.stTabs [aria-selected="true"] { border-bottom: 2px solid #ff6a00; color: #ff6a00 !important; }

/* ESTILOS PARA LOS BOTONES DE SEGMENTACIÓN (PILLS) */
div[data-testid="stPills"] button,
button[data-testid="stBaseButton-pills"] {
    background-color: #ffffff !important;
    border: 1px solid #d1d5db !important;
}
div[data-testid="stPills"] button p,
button[data-testid="stBaseButton-pills"] p {
    color: #000000 !important;
    font-weight: 600 !important;
}
/* Estado Seleccionado */
div[data-testid="stPills"] button[aria-pressed="true"],
button[data-testid="stBaseButton-pills"][aria-pressed="true"] {
    background-color: #000000 !important;
    border: 1px solid #555555 !important;
}
div[data-testid="stPills"] button[aria-pressed="true"] p,
button[data-testid="stBaseButton-pills"][aria-pressed="true"] p {
    color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)

# --- ENCABEZADO CON LOGO Y TÍTULO ---
col_logo, col_tit = st.columns([1, 10])
with col_logo:
    if os.path.exists("LOGO.webp"):
        st.image("LOGO.webp", use_container_width=True)
with col_tit:
    st.title("Dashboard Calidad - No conformidades")
st.markdown("---")

# --- ZONA DE CARGA ---
file_capa = st.file_uploader("📥 Arrastra aquí tu Excel 'Base Calidad' exportado desde SFS", type=['xlsx', 'xls'])

# --- PROCESAMIENTO DE DATOS ---
@st.cache_data(show_spinner=False)
def procesar_sfs(file):
    try:
        df = pd.read_excel(file)
        
        # 0. ELIMINAR DUPLICADOS DE FOLIOS (Incident Number)
        if 'Incident Number' in df.columns:
            df = df.drop_duplicates(subset=['Incident Number'], keep='first')
        
        # 1. Fecha y Meses
        meses_es = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 
                    7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
        if 'Fecha de Creación' in df.columns:
            fechas_dt = pd.to_datetime(df['Fecha de Creación'], format='%d-%m-%Y', errors='coerce')
            df['Fecha'] = fechas_dt.dt.date
            df['Mes_Num'] = fechas_dt.dt.month
            df['Mes'] = df['Mes_Num'].map(meses_es).fillna('Desconocido')
        else:
            df['Fecha'] = pd.NaT
            df['Mes_Num'] = 99
            df['Mes'] = 'Desconocido'

        # 2. Entidad y Origen
        df['Organización'] = df['Organización'].fillna('')
        df['Nombre del Proveedor'] = df['Nombre del Proveedor'].fillna('')
        
        df['Entidad_Asociada'] = df.apply(lambda r: r['Nombre del Proveedor'] if r['Nombre del Proveedor']!='' else (r['Organización'] if r['Organización']!='' else 'Interno / Planta'), axis=1)
        df['Origen_Clasificado'] = df.apply(lambda r: 'Proveedor' if r['Nombre del Proveedor']!='' else ('Cliente' if r['Organización']!='' else 'Interno'), axis=1)

        # 3. Clasificación y Estados
        col_tipo = 'Tipo de Incidente' if 'Tipo de Incidente' in df.columns else 'Categoría del Incidente'
        df['Clasificacion_General'] = df[col_tipo].apply(lambda x: 'Inocuidad' if any(w in str(x).lower() for w in ['seguridad', 'inocuidad', 'microbiológica']) else 'Calidad')
        df['Estado_Simplificado'] = df['Estado'].apply(lambda x: 'Cerrado' if 'Cerrado' in str(x) else 'Abierto')

        # 4. Detalles
        df['Producto_Afectado'] = df['Product Name'].fillna(df['Origin Type']).fillna('No Especificado')
        df['Causa_Motivo'] = df['Subcategoría del Incidente'].fillna(df['Categoría del Incidente']).fillna('No Definido')

        return df
    except Exception as e:
        st.error(f"Error procesando el archivo: {e}")
        return None

# --- LÓGICA DE INTERFAZ Y GRÁFICOS ---
if file_capa is not None:
    df = procesar_sfs(file_capa)
    
    if df is not None and not df.empty:
        st.markdown("### 🔍 Filtros Generales (Si no seleccionas nada, se muestran todos)")
        
        # Filtros Superiores convertidos a Botones (Pills)
        f1, f2, f3 = st.columns(3)
        
        # Se asume que si la lista está vacía (nada seleccionado), equivale a seleccionarlo todo
        filtro_origen = f1.pills("Origen", options=df['Origen_Clasificado'].unique(), selection_mode="multi")
        filtro_clase = f2.pills("Clasificación", options=df['Clasificacion_General'].unique(), selection_mode="multi")
        filtro_estado = f3.pills("Estado", options=df['Estado_Simplificado'].unique(), selection_mode="multi")
        
        origen_val = filtro_origen if filtro_origen else df['Origen_Clasificado'].unique()
        clase_val = filtro_clase if filtro_clase else df['Clasificacion_General'].unique()
        estado_val = filtro_estado if filtro_estado else df['Estado_Simplificado'].unique()
        
        df_f = df[(df['Origen_Clasificado'].isin(origen_val)) & 
                  (df['Clasificacion_General'].isin(clase_val)) & 
                  (df['Estado_Simplificado'].isin(estado_val))]
                  
        layout_oscuro = dict(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0'))

        # --- PESTAÑAS ---
        tab_global, tab_clientes = st.tabs(["🌐 Visión Global", "👥 Análisis de Clientes (Reclamos)"])

        # ==========================================
        # PESTAÑA 1: VISIÓN GLOBAL
        # ==========================================
        with tab_global:
            st.markdown("### Resumen General Operativo (Folios Únicos)")
            k1, k2, k3 = st.columns(3)
            k1.metric("Total de Hallazgos (Únicos)", len(df_f))
            k2.metric("Eventos Calidad vs Inocuidad", f"{len(df_f[df_f['Clasificacion_General'] == 'Calidad'])} / {len(df_f[df_f['Clasificacion_General'] == 'Inocuidad'])}")
            k3.metric("Tasa de Cierre", f"{(len(df_f[df_f['Estado_Simplificado'] == 'Cerrado'])/len(df_f)*100):.1f}%" if len(df_f)>0 else "0%")
            
            st.dataframe(df_f[['Incident Number', 'Fecha', 'Origen_Clasificado', 'Entidad_Asociada', 'Producto_Afectado', 'Causa_Motivo', 'Clasificacion_General', 'Estado_Simplificado']], use_container_width=True, hide_index=True)

        # ==========================================
        # PESTAÑA 2: ANÁLISIS DE CLIENTES
        # ==========================================
        with tab_clientes:
            df_cli = df_f[df_f['Origen_Clasificado'] == 'Cliente']
            
            if df_cli.empty:
                st.warning("No hay datos de clientes registrados con los filtros actuales.")
            else:
                # --- BOTONES DE SEGMENTACIÓN EN CASCADA ---
                st.markdown("#### 📅 Segmentación por Mes (Si no seleccionas nada, se muestran todos)")
                meses_unicos = df_cli[['Mes_Num', 'Mes']].drop_duplicates().sort_values('Mes_Num')['Mes'].tolist()
                
                meses_sel = st.pills("Meses", options=meses_unicos, selection_mode="multi", label_visibility="collapsed")
                
                if meses_sel:
                    df_cli = df_cli[df_cli['Mes'].isin(meses_sel)]
                
                total_cli = len(df_cli)
                
                if total_cli == 0:
                    st.warning("No hay reclamos para el período seleccionado.")
                else:
                    st.markdown("---")
                    # --- 1. EVOLUCIÓN MENSUAL ---
                    st.markdown("#### 1. Cantidad de Reclamos por Mes")
                    df_mes = df_cli.groupby(['Mes_Num', 'Mes']).size().reset_index(name='Cantidad').sort_values('Mes_Num')
                    if not df_mes.empty:
                        mes_peak = df_mes.loc[df_mes['Cantidad'].idxmax()]['Mes']
                        peak_val = df_mes['Cantidad'].max()
                        prom_mes = round(df_mes['Cantidad'].mean())
                    else:
                        mes_peak, peak_val, prom_mes = "-", 0, 0
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total Reclamos", total_cli)
                    c2.metric("Mes Peak", mes_peak)
                    c3.metric("Peak Reclamos", peak_val)
                    c4.metric("Promedio / Mes", prom_mes)

                    fig_mes = px.bar(df_mes, x='Mes', y='Cantidad', text='Cantidad', color_discrete_sequence=['#00f3ff'])
                    fig_mes.update_traces(textposition='outside')
                    fig_mes.update_layout(**layout_oscuro, margin=dict(t=20, b=0))
                    st.plotly_chart(fig_mes, use_container_width=True)
                    st.markdown("---")

                    # --- 2. CLASIFICACIÓN (Calidad vs Inocuidad) ---
                    st.markdown("#### 2. Clasificación de Reclamos")
                    calidad_cli = len(df_cli[df_cli['Clasificacion_General'] == 'Calidad'])
                    inoc_cli = len(df_cli[df_cli['Clasificacion_General'] == 'Inocuidad'])
                    pct_calidad = (calidad_cli / total_cli * 100) if total_cli > 0 else 0
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total", total_cli)
                    c2.metric("Calidad", calidad_cli)
                    c3.metric("Inocuidad", inoc_cli)
                    c4.metric("% Calidad", f"{pct_calidad:.1f}%")

                    fig_class = px.pie(df_cli, names='Clasificacion_General', hole=0, color_discrete_sequence=['#00f3ff', '#ff6a00'])
                    fig_class.update_traces(textinfo='label+percent+value')
                    fig_class.update_layout(**layout_oscuro, margin=dict(t=20, b=0))
                    st.plotly_chart(fig_class, use_container_width=True)
                    st.markdown("---")

                    # --- 3. MOTIVOS DE RECLAMO ---
                    st.markdown("#### 3. Motivos de Reclamo")
                    df_mot = df_cli['Causa_Motivo'].value_counts().reset_index()
                    df_mot.columns = ['Motivo', 'Cantidad']
                    df_mot['%'] = (df_mot['Cantidad'] / total_cli) * 100
                    df_mot['Texto'] = df_mot['%'].apply(lambda x: f'{x:.1f}%')

                    prin_mot = df_mot.iloc[0]['Motivo'] if len(df_mot) > 0 else "-"
                    n_mot = len(df_mot)
                    sec_mot = df_mot.iloc[1]['Motivo'] if len(df_mot) > 1 else "-"
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total", total_cli)
                    c2.metric("Principal Motivo", prin_mot)
                    c3.metric("N° Motivos Distintos", n_mot)
                    c4.metric("2do Motivo", sec_mot)

                    fig_mot = px.bar(df_mot.sort_values('Cantidad', ascending=True), x='%', y='Motivo', text='Texto', orientation='h', color_discrete_sequence=['#00f3ff'])
                    fig_mot.update_traces(textposition='outside')
                    fig_mot.update_layout(**layout_oscuro, margin=dict(t=20, b=0), xaxis_title="% de Reclamos")
                    st.plotly_chart(fig_mot, use_container_width=True)
                    st.markdown("---")

                    # --- 4. PRODUCTOS RECLAMADOS ---
                    st.markdown("#### 4. Productos Reclamados")
                    df_prod = df_cli['Producto_Afectado'].value_counts().reset_index()
                    df_prod.columns = ['Producto', 'Cantidad']
                    df_prod['%'] = (df_prod['Cantidad'] / total_cli) * 100
                    df_prod['Texto'] = df_prod['%'].apply(lambda x: f'{x:.1f}%')

                    prin_prod = df_prod.iloc[0]['Producto'] if len(df_prod) > 0 else "-"
                    n_prod = len(df_prod)
                    sec_prod = df_prod.iloc[1]['Producto'] if len(df_prod) > 1 else "-"

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total", total_cli)
                    c2.metric("Principal Producto", prin_prod)
                    c3.metric("N° Productos Distintos", n_prod)
                    c4.metric("2do Producto", sec_prod)

                    fig_prod = px.bar(df_prod.head(15).sort_values('Cantidad', ascending=True), x='%', y='Producto', text='Texto', orientation='h', color_discrete_sequence=['#ff6a00'])
                    fig_prod.update_traces(textposition='outside')
                    fig_prod.update_layout(**layout_oscuro, margin=dict(t=20, b=0), xaxis_title="% de Reclamos (Top 15)")
                    st.plotly_chart(fig_prod, use_container_width=True)
                    st.markdown("---")

                    # --- 5. CLIENTES CON RECLAMOS ---
                    st.markdown("#### 5. Clientes con Reclamos")
                    df_cli_nombres = df_cli['Entidad_Asociada'].value_counts().reset_index()
                    df_cli_nombres.columns = ['Cliente', 'Cantidad']
                    df_cli_nombres['%'] = (df_cli_nombres['Cantidad'] / total_cli) * 100
                    df_cli_nombres['Texto'] = df_cli_nombres['%'].apply(lambda x: f'{x:.1f}%')

                    prin_cliente = df_cli_nombres.iloc[0]['Cliente'] if len(df_cli_nombres) > 0 else "-"
                    pct_prin_cliente = df_cli_nombres.iloc[0]['%'] if len(df_cli_nombres) > 0 else 0
                    n_clientes = len(df_cli_nombres)

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total Clientes", n_clientes)
                    c2.metric("Cliente Principal", prin_cliente)
                    c3.metric("% Principal", f"{pct_prin_cliente:.1f}%")
                    c4.metric("N° Clientes Afectados", n_clientes)

                    fig_cli = px.bar(df_cli_nombres.sort_values('Cantidad', ascending=True), x='%', y='Cliente', text='Texto', orientation='h', color_discrete_sequence=['#39ff14'])
                    fig_cli.update_traces(textposition='outside')
                    fig_cli.update_layout(**layout_oscuro, margin=dict(t=20, b=0), xaxis_title="% de Reclamos por Cliente")
                    st.plotly_chart(fig_cli, use_container_width=True)

else:
    st.info("💡 Arrastra el archivo 'Base Calidad.xlsx' de Smart Food Safe para generar tu Dashboard.")
