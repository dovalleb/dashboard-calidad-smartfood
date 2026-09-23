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
/* Se aplica color claro a los textos generales, pero SE EXCLUYEN los textos de los Pills */
.stMarkdown p:not(div[data-testid="stPills"] p), 
label:not(div[data-testid="stPills"] label), 
.stTab { color: #e2e8f0 !important; }

h1, h2, h3, h4 { color: #ff6a00 !important; text-shadow: 0px 0px 12px rgba(255, 106, 0, 0.8); }
[data-testid="stMetricValue"] { color: #39ff14 !important; text-shadow: 0px 0px 12px rgba(57, 255, 20, 0.8); }
[data-testid="stMetricLabel"] { color: #00f3ff !important; text-shadow: 0px 0px 8px rgba(0, 243, 255, 0.5); }
hr { border-bottom: 1px solid #ff6a00; box-shadow: 0px 0px 8px #ff6a00; }
.stAlert { background-color: #111827; border: 1px solid #ff6a00; }

/* Estilo para las pestañas */
.stTabs [data-baseweb="tab-list"] { background-color: #0a0e17; }
.stTabs [data-baseweb="tab"] { color: #00f3ff; font-weight: bold; font-size: 16px; }
.stTabs [aria-selected="true"] { border-bottom: 2px solid #ff6a00; color: #ff6a00 !important; }

/* --- ESTILOS MEJORADOS PARA LOS BOTONES DE SEGMENTACIÓN (PILLS) --- */
div[data-testid="stPills"] button {
    background-color: #ffffff !important;
    border: 1px solid #d1d5db !important;
}
div[data-testid="stPills"] button p, 
div[data-testid="stPills"] button span, 
div[data-testid="stPills"] button div {
    color: #000000 !important;
    font-weight: 800 !important;
}
div[data-testid="stPills"] button[aria-pressed="true"] {
    background-color: #ff0000 !important;
    border: 1px solid #ff0000 !important;
}
div[data-testid="stPills"] button[aria-pressed="true"] p,
div[data-testid="stPills"] button[aria-pressed="true"] span,
div[data-testid="stPills"] button[aria-pressed="true"] div {
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
        
        # 0. ELIMINAR DUPLICADOS DE FORMA SEGURA
        if 'Incident Number' in df.columns:
            df['Incident Number'] = df['Incident Number'].astype(str).str.strip()
            df = df.drop_duplicates(subset=['Incident Number'], keep='first')
        
        # 1. Fecha y Meses 
        meses_es = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 
                    7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
        if 'Fecha de Creación' in df.columns:
            fechas_dt = pd.to_datetime(df['Fecha de Creación'], errors='coerce', dayfirst=True)
            df['Fecha'] = fechas_dt.dt.date
            df['Mes_Num'] = fechas_dt.dt.month
            df['Mes'] = df['Mes_Num'].map(meses_es).fillna('Desconocido')
        else:
            df['Fecha'] = pd.NaT
            df['Mes_Num'] = 99
            df['Mes'] = 'Desconocido'

        for c in ['Organización', 'Nombre del Proveedor', 'Investigador Asignado']:
            if c not in df.columns: df[c] = ''
            
        df['Organización'] = df['Organización'].fillna('')
        df['Nombre del Proveedor'] = df['Nombre del Proveedor'].fillna('')
        df['Investigador Asignado'] = df['Investigador Asignado'].fillna('Sin Asignar')

        # 2. REGLA LÓGICA: COMERCIAL VALORA = PROVEEDOR, RESTO = CLIENTE
        def determinar_origen(r):
            org = str(r['Organización']).strip().upper()
            prov = str(r['Nombre del Proveedor']).strip()
            
            if 'VALORA' in org:
                return 'Proveedor'
            elif org != '':
                return 'Cliente'
            elif prov != '':
                return 'Proveedor'
            else:
                return 'Interno'
                
        df['Origen_Clasificado'] = df.apply(determinar_origen, axis=1)

        def determinar_entidad(r):
            org = str(r['Organización']).strip()
            prov = str(r['Nombre del Proveedor']).strip()
            
            if r['Origen_Clasificado'] == 'Cliente':
                return org
            elif r['Origen_Clasificado'] == 'Proveedor':
                if prov != '': return prov
                if org != '': return org
                return 'Proveedor No Especificado'
            return 'Interno / Planta'
            
        df['Entidad_Asociada'] = df.apply(determinar_entidad, axis=1)
        
        # 3. LÓGICA DINÁMICA DE ENTIDAD (Investigador vs Cliente)
        df['Entidad_Grafico'] = df.apply(lambda r: r['Investigador Asignado'] if r['Origen_Clasificado'] == 'Proveedor' else r['Entidad_Asociada'], axis=1)

        # 4. Clasificación (REGLA INOCUIDAD)
        col_tipo = 'Tipo de Incidente' if 'Tipo de Incidente' in df.columns else 'Categoría del Incidente'
        if col_tipo in df.columns:
            df['Clasificacion_General'] = df[col_tipo].apply(lambda x: 'Inocuidad' if 'seguridad alimentaria' in str(x).strip().lower() else 'Calidad')
        else:
            df['Clasificacion_General'] = 'Calidad'
            
        if 'Estado' in df.columns:
            df['Estado_Simplificado'] = df['Estado'].apply(lambda x: 'Cerrado' if 'Cerrado' in str(x) else 'Abierto')
        else:
            df['Estado_Simplificado'] = 'Abierto'

        # 5. Detalles 
        col_prod = 'Product Name' if 'Product Name' in df.columns else 'Producto'
        col_orig_type = 'Origin Type' if 'Origin Type' in df.columns else 'Tipo de Origen'
        if col_prod not in df.columns: df[col_prod] = ''
        if col_orig_type not in df.columns: df[col_orig_type] = ''
        df['Producto_Afectado'] = df[col_prod].replace('', pd.NA).fillna(df[col_orig_type]).fillna('No Especificado')
        
        col_subcat = 'Subcategoría del Incidente' if 'Subcategoría del Incidente' in df.columns else 'Subcategoría'
        col_cat = 'Categoría del Incidente' if 'Categoría del Incidente' in df.columns else 'Categoría'
        if col_subcat not in df.columns: df[col_subcat] = ''
        if col_cat not in df.columns: df[col_cat] = ''
        df['Causa_Motivo'] = df[col_subcat].replace('', pd.NA).fillna(df[col_cat]).fillna('No Definido')

        return df
    except Exception as e:
        st.error(f"Error procesando el archivo: {e}")
        return None

# --- LÓGICA DE INTERFAZ Y GRÁFICOS ---
if file_capa is not None:
    df = procesar_sfs(file_capa)
    
    if df is not None and not df.empty:
        st.markdown("### 🔍 Filtros Generales (Si no seleccionas nada, se muestran todos)")
        
        f1, f2, f3, f4 = st.columns(4)
        
        meses_unicos = df[['Mes_Num', 'Mes']].drop_duplicates().sort_values('Mes_Num')['Mes'].tolist()
        
        filtro_mes = f1.pills("Mes", options=meses_unicos, selection_mode="multi")
        filtro_origen = f2.pills("Origen", options=df['Origen_Clasificado'].unique(), selection_mode="multi")
        filtro_clase = f3.pills("Clasificación", options=df['Clasificacion_General'].unique(), selection_mode="multi")
        filtro_estado = f4.pills("Estado", options=df['Estado_Simplificado'].unique(), selection_mode="multi")
        
        mes_val = filtro_mes if filtro_mes else meses_unicos
        origen_val = filtro_origen if filtro_origen else df['Origen_Clasificado'].unique()
        clase_val = filtro_clase if filtro_clase else df['Clasificacion_General'].unique()
        estado_val = filtro_estado if filtro_estado else df['Estado_Simplificado'].unique()
        
        df_temp = df[(df['Mes'].isin(mes_val)) & 
                     (df['Origen_Clasificado'].isin(origen_val)) & 
                     (df['Clasificacion_General'].isin(clase_val)) & 
                     (df['Estado_Simplificado'].isin(estado_val))]

        # --- SUB-FILTROS EN CASCADA (AL 100% DE ANCHO) ---
        sel_inv, sel_cli = [], []
        if 'Proveedor' in origen_val or 'Cliente' in origen_val:
            st.markdown("#### 🎯 Sub-Filtros Dinámicos (Se activan según el Origen seleccionado)")
            
            if 'Proveedor' in origen_val:
                inv_opts = [x for x in df_temp[df_temp['Origen_Clasificado'] == 'Proveedor']['Investigador Asignado'].unique() if str(x).strip() != '']
                if inv_opts:
                    sel_inv = st.pills("Investigador a cargo (Proveedores)", options=inv_opts, selection_mode="multi")
            
            if 'Cliente' in origen_val:
                cli_opts = [x for x in df_temp[df_temp['Origen_Clasificado'] == 'Cliente']['Entidad_Asociada'].unique() if str(x).strip() != '']
                if cli_opts:
                    sel_cli = st.pills("Clientes Específicos", options=cli_opts, selection_mode="multi")

        df_f = df_temp.copy()
        if sel_inv:
            df_f = df_f[~((df_f['Origen_Clasificado'] == 'Proveedor') & (~df_f['Investigador Asignado'].isin(sel_inv)))]
        if sel_cli:
            df_f = df_f[~((df_f['Origen_Clasificado'] == 'Cliente') & (~df_f['Entidad_Asociada'].isin(sel_cli)))]

        layout_oscuro = dict(
            template='plotly_dark', 
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)', 
            font=dict(color='#e2e8f0', size=14)
        )

        # --- PESTAÑAS ---
        tab_global, tab_analisis = st.tabs(["🌐 Visión Global", "📊 Análisis Detallado (Reclamos)"])

        # ==========================================
        # PESTAÑA 1: VISIÓN GLOBAL
        # ==========================================
        with tab_global:
            st.markdown("### Resumen General Operativo (Folios Únicos)")
            k1, k2, k3 = st.columns(3)
            k1.metric("Total de Hallazgos (Únicos)", len(df_f))
            k2.metric("Eventos Calidad vs Inocuidad", f"{len(df_f[df_f['Clasificacion_General'] == 'Calidad'])} / {len(df_f[df_f['Clasificacion_General'] == 'Inocuidad'])}")
            k3.metric("Tasa de Cierre", f"{(len(df_f[df_f['Estado_Simplificado'] == 'Cerrado'])/len(df_f)*100):.1f}%" if len(df_f)>0 else "0%")
            
            st.dataframe(df_f[['Incident Number', 'Fecha', 'Mes', 'Origen_Clasificado', 'Entidad_Asociada', 'Investigador Asignado', 'Producto_Afectado', 'Causa_Motivo', 'Clasificacion_General', 'Estado_Simplificado']], use_container_width=True, hide_index=True)

        # ==========================================
        # PESTAÑA 2: ANÁLISIS DETALLADO
        # ==========================================
        with tab_analisis:
            df_analisis = df_f.copy()
            
            if df_analisis.empty:
                st.warning("No hay datos registrados con los filtros actuales.")
            else:
                total_analisis = len(df_analisis)
                
                # --- 1. EVOLUCIÓN MENSUAL ---
                st.markdown("#### 1. Cantidad de Reclamos por Mes")
                df_mes = df_analisis.groupby(['Mes_Num', 'Mes']).size().reset_index(name='Cantidad').sort_values('Mes_Num')
                if not df_mes.empty:
                    mes_peak = df_mes.loc[df_mes['Cantidad'].idxmax()]['Mes']
                    peak_val = df_mes['Cantidad'].max()
                    prom_mes = round(df_mes['Cantidad'].mean())
                else:
                    mes_peak, peak_val, prom_mes = "-", 0, 0
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Reclamos", total_analisis)
                c2.metric("Mes Peak", mes_peak)
                c3.metric("Peak Reclamos", peak_val)
                c4.metric("Promedio / Mes", prom_mes)

                fig_mes = px.bar(df_mes, x='Mes', y='Cantidad', text='Cantidad', color_discrete_sequence=['#00f3ff'])
                fig_mes.update_traces(textposition='outside', textfont=dict(size=14, color='white'))
                fig_mes.update_xaxes(showgrid=False, tickfont=dict(size=13), title_font=dict(size=15))
                fig_mes.update_yaxes(showgrid=False, tickfont=dict(size=13), title_font=dict(size=15))
                fig_mes.update_layout(**layout_oscuro, margin=dict(t=20, b=0))
                st.plotly_chart(fig_mes, use_container_width=True)
                st.markdown("---")

                # --- 2. CLASIFICACIÓN (Calidad vs Inocuidad) ---
                st.markdown("#### 2. Clasificación de Reclamos")
                calidad_cli = len(df_analisis[df_analisis['Clasificacion_General'] == 'Calidad'])
                inoc_cli = len(df_analisis[df_analisis['Clasificacion_General'] == 'Inocuidad'])
                pct_calidad = (calidad_cli / total_analisis * 100) if total_analisis > 0 else 0
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total", total_analisis)
                c2.metric("Calidad", calidad_cli)
                c3.metric("Inocuidad", inoc_cli)
                c4.metric("% Calidad", f"{pct_calidad:.1f}%")

                fig_class = px.pie(df_analisis, names='Clasificacion_General', hole=0, color_discrete_sequence=['#00f3ff', '#ff6a00'])
                fig_class.update_traces(textinfo='label+percent+value', textfont=dict(size=16, color='white'))
                fig_class.update_layout(**layout_oscuro, margin=dict(t=20, b=0), legend=dict(font=dict(size=15)))
                st.plotly_chart(fig_class, use_container_width=True)
                st.markdown("---")

                # --- 3. MOTIVOS DE RECLAMO ---
                st.markdown("#### 3. Motivos de Reclamo")
                df_mot = df_analisis['Causa_Motivo'].value_counts().reset_index()
                df_mot.columns = ['Motivo', 'Cantidad']
                df_mot['%'] = (df_mot['Cantidad'] / total_analisis) * 100
                df_mot['Texto'] = df_mot['%'].apply(lambda x: f'{x:.1f}%')

                prin_mot = df_mot.iloc[0]['Motivo'] if len(df_mot) > 0 else "-"
                n_mot = len(df_mot)
                sec_mot = df_mot.iloc[1]['Motivo'] if len(df_mot) > 1 else "-"
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total", total_analisis)
                c2.metric("Principal Motivo", prin_mot)
                c3.metric("N° Motivos Distintos", n_mot)
                c4.metric("2do Motivo", sec_mot)

                fig_mot = px.bar(df_mot.sort_values('Cantidad', ascending=True), x='%', y='Motivo', text='Texto', orientation='h', color_discrete_sequence=['#00f3ff'])
                fig_mot.update_traces(textposition='outside', textfont=dict(size=14, color='white'))
                fig_mot.update_xaxes(showgrid=False, tickfont=dict(size=13), title_font=dict(size=15))
                fig_mot.update_yaxes(showgrid=False, tickfont=dict(size=14), title_font=dict(size=15))
                # Ajuste de altura dinámica según cantidad de motivos para que no se agrupen ni se vean apretados
                fig_mot.update_layout(**layout_oscuro, margin=dict(t=20, b=0, l=150), xaxis_title="% de Reclamos", height=max(400, len(df_mot)*30))
                st.plotly_chart(fig_mot, use_container_width=True)
                st.markdown("---")

                # --- 4. PRODUCTOS RECLAMADOS ---
                st.markdown("#### 4. Productos Reclamados")
                df_prod = df_analisis['Producto_Afectado'].value_counts().reset_index()
                df_prod.columns = ['Producto', 'Cantidad']
                df_prod['%'] = (df_prod['Cantidad'] / total_analisis) * 100
                df_prod['Texto'] = df_prod['%'].apply(lambda x: f'{x:.1f}%')

                prin_prod = df_prod.iloc[0]['Producto'] if len(df_prod) > 0 else "-"
                n_prod = len(df_prod)
                sec_prod = df_prod.iloc[1]['Producto'] if len(df_prod) > 1 else "-"

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total", total_analisis)
                c2.metric("Principal Producto", prin_prod)
                c3.metric("N° Productos Distintos", n_prod)
                c4.metric("2do Producto", sec_prod)

                fig_prod = px.bar(df_prod.head(15).sort_values('Cantidad', ascending=True), x='%', y='Producto', text='Texto', orientation='h', color_discrete_sequence=['#ff6a00'])
                fig_prod.update_traces(textposition='outside', textfont=dict(size=14, color='white'))
                fig_prod.update_xaxes(showgrid=False, tickfont=dict(size=13), title_font=dict(size=15))
                fig_prod.update_yaxes(showgrid=False, tickfont=dict(size=14), title_font=dict(size=15))
                fig_prod.update_layout(**layout_oscuro, margin=dict(t=20, b=0, l=150), xaxis_title="% de Reclamos (Top 15)", height=max(400, min(15, len(df_prod))*30))
                st.plotly_chart(fig_prod, use_container_width=True)
                st.markdown("---")

                # --- 5. ENTIDADES CON RECLAMOS ---
                st.markdown("#### 5. Entidades con Reclamos (Investigadores vs Clientes)")
                df_entidades = df_analisis['Entidad_Grafico'].value_counts().reset_index()
                df_entidades.columns = ['Entidad', 'Cantidad']
                df_entidades['%'] = (df_entidades['Cantidad'] / total_analisis) * 100
                df_entidades['Texto'] = df_entidades['%'].apply(lambda x: f'{x:.1f}%')

                prin_entidad = df_entidades.iloc[0]['Entidad'] if len(df_entidades) > 0 else "-"
                pct_prin_entidad = df_entidades.iloc[0]['%'] if len(df_entidades) > 0 else 0
                n_entidades = len(df_entidades)

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Entidades", n_entidades)
                c2.metric("Entidad Principal", prin_entidad)
                c3.metric("% Principal", f"{pct_prin_entidad:.1f}%")
                c4.metric("N° Entidades Afectadas", n_entidades)

                fig_ent = px.bar(df_entidades.sort_values('Cantidad', ascending=True), x='%', y='Entidad', text='Texto', orientation='h', color_discrete_sequence=['#39ff14'])
                fig_ent.update_traces(textposition='outside', textfont=dict(size=14, color='white'))
                fig_ent.update_xaxes(showgrid=False, tickfont=dict(size=13), title_font=dict(size=15))
                fig_ent.update_yaxes(showgrid=False, tickfont=dict(size=14), title_font=dict(size=15))
                fig_ent.update_layout(**layout_oscuro, margin=dict(t=20, b=0, l=150), xaxis_title="% de Reclamos por Entidad", height=max(300, len(df_entidades)*30))
                st.plotly_chart(fig_ent, use_container_width=True)

else:
    st.info("💡 Arrastra el archivo 'Base Calidad.xlsx' de Smart Food Safe para generar tu Dashboard.")
