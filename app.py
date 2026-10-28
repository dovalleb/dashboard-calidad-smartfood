import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# --- CONFIGURACION ---
st.set_page_config(page_title="Dashboard Integral - Tribu Food", layout="wide")

# --- ESTILOS VISUALES: MODO OSCURO, NEON Y BOTONES ---
st.markdown("""
<style>
.stApp { background-color: #0a0e17; }
.stMarkdown p:not(div[data-testid="stPills"] p), 
label:not(div[data-testid="stPills"] label), 
.stTab { color: #e2e8f0 !important; }

h1, h2, h3, h4 { color: #ff6a00 !important; text-shadow: 0px 0px 12px rgba(255, 106, 0, 0.8); }
[data-testid="stMetricValue"] { color: #39ff14 !important; text-shadow: 0px 0px 12px rgba(57, 255, 20, 0.8); }
[data-testid="stMetricLabel"] { color: #00f3ff !important; text-shadow: 0px 0px 8px rgba(0, 243, 255, 0.5); }
hr { border-bottom: 1px solid #ff6a00; box-shadow: 0px 0px 8px #ff6a00; }
.stAlert { background-color: #111827; border: 1px solid #ff6a00; }

.stTabs [data-baseweb="tab-list"] { background-color: #0a0e17; }
.stTabs [data-baseweb="tab"] { color: #00f3ff; font-weight: bold; font-size: 16px; }
.stTabs [aria-selected="true"] { border-bottom: 2px solid #ff6a00; color: #ff6a00 !important; }

div[data-testid="stPills"] button { background-color: #ffffff !important; border: 1px solid #d1d5db !important; }
div[data-testid="stPills"] button p, div[data-testid="stPills"] button span, div[data-testid="stPills"] button div { color: #000000 !important; font-weight: 800 !important; }
div[data-testid="stPills"] button[aria-pressed="true"] { background-color: #ff0000 !important; border: 1px solid #ff0000 !important; }
div[data-testid="stPills"] button[aria-pressed="true"] p, div[data-testid="stPills"] button[aria-pressed="true"] span, div[data-testid="stPills"] button[aria-pressed="true"] div { color: #ffffff !important; }
</style>
""", unsafe_allow_html=True)

# --- ENCABEZADO CON LOGO Y TITULO ---
col_logo, col_tit = st.columns([1, 10])
with col_logo:
    if os.path.exists("LOGO.webp"):
        st.image("LOGO.webp", width="stretch")
with col_tit:
    st.title("Dashboard Integral de Gestion - Tribu Food")
st.markdown("---")

# --- ZONAS DE CARGA ---
c_up1, c_up2 = st.columns(2)
with c_up1:
    file_capa = st.file_uploader("Excel Base Calidad (Reclamos SFS)", type=['xlsx', 'xls'])
with c_up2:
    file_train = st.file_uploader("Excel Capacitaciones (Calidad)", type=['xlsx', 'xls'])

# --- PROCESAMIENTO DE DATOS: RECLAMOS E INDICADORES SLA ---
@st.cache_data(show_spinner=False)
def procesar_sfs(file):
    try:
        df = pd.read_excel(file)
        
        columnas_base = [
            'Incident Number', 'Recibido De', 'Organización', 'Investigador Asignado', 
            'Nombre del Material de Empaque', 'Nombre de la Materia Prima', 'Product Name', 
            'Nombre del Trabajo en Progreso', 'Código de Lote', 'Descripción',
            'Fecha de Creación', 'Fecha Límite de Finalización', 'Fecha Límite de la Investigación', 'Fecha de Finalización'
        ]
        for c in columnas_base:
            if c not in df.columns: 
                df[c] = ''
            
        df['Incident Number'] = df['Incident Number'].fillna('Sin Folio').astype(str).str.strip()
        
        meses_es = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 
                    7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
        
        fechas_dt = pd.to_datetime(df['Fecha de Creación'], errors='coerce', dayfirst=True)
        df['Fecha_Real'] = fechas_dt
        df['Fecha'] = fechas_dt.dt.date
        df['Mes_Num'] = fechas_dt.dt.month
        df['Mes'] = df['Mes_Num'].map(meses_es).fillna('Desconocido')

        df['Recibido De'] = df['Recibido De'].fillna('')
        df['Organización'] = df['Organización'].fillna('')
        df['Investigador Asignado'] = df['Investigador Asignado'].fillna('Sin Asignar')
        df['Código de Lote'] = df['Código de Lote'].fillna('')

        df['Origen_Clasificado'] = df['Recibido De'].apply(lambda x: str(x).strip().capitalize() if str(x).strip() != '' else 'Interno')
        df['Entidad_Asociada'] = df['Organización'].apply(lambda x: str(x).strip() if str(x).strip() != '' else 'No Especificado')
        df['Entidad_Grafico'] = df.apply(lambda r: r['Investigador Asignado'] if r['Origen_Clasificado'] == 'Proveedor' else r['Entidad_Asociada'], axis=1)

        col_tipo = 'Tipo de Incidente' if 'Tipo de Incidente' in df.columns else 'Categoría del Incidente'
        if col_tipo in df.columns:
            df['Clasificacion_General'] = df[col_tipo].apply(lambda x: 'Inocuidad' if 'seguridad alimentaria' in str(x).strip().lower() else 'Calidad')
        else:
            df['Clasificacion_General'] = 'Calidad'
            
        if 'Estado' in df.columns:
            df['Estado_Simplificado'] = df['Estado'].apply(lambda x: 'Cerrado' if 'Cerrado' in str(x) else 'Abierto')
        else:
            df['Estado_Simplificado'] = 'Abierto'

        # Lógica SLA
        limite_col = 'Fecha Límite de Finalización' if df['Fecha Límite de Finalización'].astype(str).str.strip().replace('', 'nan').nunique() > 1 else 'Fecha Límite de la Investigación'
        
        df['Fecha_Limite_SLA'] = pd.to_datetime(df[limite_col], errors='coerce', dayfirst=True)
        df['Fecha_Cierre_SLA'] = pd.to_datetime(df['Fecha de Finalización'], errors='coerce', dayfirst=True)
        hoy = pd.to_datetime(datetime.today())
        
        def calcular_dias(r):
            if r['Estado_Simplificado'] == 'Abierto' and pd.notna(r['Fecha_Real']):
                return (hoy - r['Fecha_Real']).days
            return 0
            
        df['Dias_Pendientes'] = df.apply(calcular_dias, axis=1)

        def calcular_estado_sla(r):
            if r['Estado_Simplificado'] == 'Cerrado':
                if pd.notna(r['Fecha_Cierre_SLA']) and pd.notna(r['Fecha_Limite_SLA']):
                    return 'Cerrado a Tiempo' if r['Fecha_Cierre_SLA'] <= r['Fecha_Limite_SLA'] else 'Cerrado Atrasado'
                return 'Cerrado'
            else:
                if pd.notna(r['Fecha_Limite_SLA']):
                    return 'Pendiente a Tiempo' if hoy <= r['Fecha_Limite_SLA'] else 'Pendiente Atrasado'
                return 'Pendiente (Sin Plazo)'
                
        df['Estado_SLA'] = df.apply(calcular_estado_sla, axis=1)

        def asignar_producto_afectado(r):
            cols_producto = ['Nombre de la Materia Prima', 'Nombre del Material de Empaque', 'Product Name', 'Nombre del Trabajo en Progreso']
            for c in cols_producto:
                val = str(r[c]).replace('nan', '').strip()
                if val != '': return val
            
            desc = str(r['Descripción']).lower()
            productos_conocidos = ['mix fiesta', 'granola berries', 'granola', 'stick maní', 'mix cajuna', 
                                   'mix frutos del bosque', 'castaña de cajú', 'castaña', 'ciruelas sin carozo', 'ciruela', 'huesillo', 'nuez', 'almendra', 'maní']
            for prod in productos_conocidos:
                if prod in desc: return prod.title()
            return 'No Especificado'

        def asignar_lote(r):
            lote = str(r['Código de Lote']).replace('nan', '').strip()
            if r['Clasificacion_General'] == 'Inocuidad': return lote if lote != '' else 'Sin Lote'
            return '-'

        df['Producto_Afectado'] = df.apply(asignar_producto_afectado, axis=1)
        df['Lote_Materia_Prima'] = df.apply(asignar_lote, axis=1)
        
        col_subcat = 'Subcategoría del Incidente' if 'Subcategoría del Incidente' in df.columns else 'Subcategoría'
        col_cat = 'Categoría del Incidente' if 'Categoría del Incidente' in df.columns else 'Categoría'
        if col_subcat not in df.columns: df[col_subcat] = ''
        if col_cat not in df.columns: df[col_cat] = ''
        
        df['Causa_Motivo_Raw'] = df[col_subcat].replace('', pd.NA).fillna(df[col_cat]).fillna('No Definido')
        diccionario_motivos = {
            'extraneous vegetable material': 'Material Vegetal Extraño', 'bitter': 'Sabor Amargo', 
            'other appearance': 'Otra Apariencia', 'unexpected ingredient': 'Ingrediente Inesperado', 
            'exploded bag': 'Bolsa Explotada', 'open and close issues': 'Problemas de Apertura y Cierre',
            'yeast and mold': 'Levaduras y Mohos', 'plastic': 'Presencia de Plástico', 
            'metal': 'Presencia de Metal', 'color': 'Problemas de Color', 
            'cuerpos extraños origen vegetal': 'Cuerpos Extraños (Vegetal)', 'salmonella spp.': 'Presencia de Salmonella spp.'
        }
        df['Causa_Motivo'] = df['Causa_Motivo_Raw'].apply(lambda x: diccionario_motivos.get(str(x).strip().lower(), str(x).strip()))
        return df
    except Exception as e:
        st.error(f"Error procesando el archivo de Reclamos. Detalle: {e}")
        return None

# --- PROCESAMIENTO DE DATOS: CAPACITACIONES ---
@st.cache_data(show_spinner=False)
def procesar_capacitaciones(file):
    try:
        df = pd.read_excel(file)
        if 'Nombre curso' not in df.columns:
            df = pd.read_excel(file, skiprows=3)
        
        part_col = [c for c in df.columns if 'participante' in c.lower()]
        if part_col:
            df['Participante'] = df[part_col[-1]].astype(str).str.strip().str.title()
        else:
            df['Participante'] = 'Desconocido'

        df = df[~df['Participante'].isin(['Nan', 'None', '', 'Na', 'Nan Nan', 'Nat', 'NaT'])]

        df['Curso'] = df.get('Nombre curso', pd.Series(dtype=str)).astype(str).str.strip().str.capitalize()
        df['Relator'] = df.get('Nombre relator', pd.Series(dtype=str)).astype(str).str.strip().str.title()
        df['Temas'] = df.get('Temas', pd.Series(dtype=str)).fillna('Sin Especificar')
        df['Registro_Id'] = df.get('Registro Id', pd.Series(dtype=str)).fillna('Sin ID')
        
        df['Curso'] = df['Curso'].replace('Nan', 'Sin Especificar')
        df['Relator'] = df['Relator'].replace('Nan', 'Sin Especificar')

        meses_es = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 
                    7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
        
        if 'Fecha' in df.columns:
            fechas_dt = pd.to_datetime(df['Fecha'], errors='coerce', dayfirst=True)
            df['Mes_Num'] = fechas_dt.dt.month
            df['Mes'] = df['Mes_Num'].map(meses_es).fillna('Desconocido')
            df['Fecha_Limpia'] = fechas_dt.dt.date
        else:
            df['Mes_Num'] = 99
            df['Mes'] = 'Desconocido'
            df['Fecha_Limpia'] = pd.NaT

        return df
    except Exception as e:
        st.error(f"Error procesando el archivo de Capacitaciones. Detalle: {e}")
        return None

layout_oscuro = dict(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0', size=14))

# --- PESTANAS PRINCIPALES ---
tab_global, tab_analisis, tab_sla, tab_capacitaciones = st.tabs([
    "Vision Global (Reclamos)", 
    "Analisis Grafico (Reclamos)", 
    "Seguimiento (SLA)", 
    "Capacitaciones (Calidad)"
])

# ==========================================
# LOGICA DE RECLAMOS Y SLA
# ==========================================
if file_capa is not None:
    df = procesar_sfs(file_capa)
    if df is not None and not df.empty:
        with tab_global:
            st.markdown("### Filtros Generales (Reclamos)")
            f1, f2, f3, f4 = st.columns(4)
            meses_unicos = df[['Mes_Num', 'Mes']].drop_duplicates().sort_values('Mes_Num')['Mes'].tolist()
            
            filtro_mes = f1.pills("Mes", options=meses_unicos, selection_mode="multi")
            filtro_origen = f2.pills("Origen", options=df['Origen_Clasificado'].unique(), selection_mode="multi")
            filtro_clase = f3.pills("Clasificacion", options=df['Clasificacion_General'].unique(), selection_mode="multi")
            filtro_estado = f4.pills("Estado", options=df['Estado_Simplificado'].unique(), selection_mode="multi")
            
            mes_val = filtro_mes if filtro_mes else meses_unicos
            origen_val = filtro_origen if filtro_origen else df['Origen_Clasificado'].unique()
            clase_val = filtro_clase if filtro_clase else df['Clasificacion_General'].unique()
            estado_val = filtro_estado if filtro_estado else df['Estado_Simplificado'].unique()
            
            df_temp = df[
                (df['Mes'].isin(mes_val)) & 
                (df['Origen_Clasificado'].isin(origen_val)) & 
                (df['Clasificacion_General'].isin(clase_val)) & 
                (df['Estado_Simplificado'].isin(estado_val))
            ]

            sel_inv, sel_cli = [], []
            if 'Proveedor' in origen_val or 'Cliente' in origen_val:
                st.markdown("#### Sub-Filtros Dinamicos")
                if 'Proveedor' in origen_val:
                    inv_opts = [x for x in df_temp[df_temp['Origen_Clasificado'] == 'Proveedor']['Investigador Asignado'].unique() if str(x).strip() != '']
                    if inv_opts: 
                        sel_inv = st.pills("Investigador (Proveedores)", options=inv_opts, selection_mode="multi")
                if 'Cliente' in origen_val:
                    cli_opts = [x for x in df_temp[df_temp['Origen_Clasificado'] == 'Cliente']['Entidad_Asociada'].unique() if str(x).strip() != '']
                    if cli_opts: 
                        sel_cli = st.pills("Clientes Especificos", options=cli_opts, selection_mode="multi")

            df_f = df_temp.copy()
            
            if sel_inv: 
                condicion_prov = (df_f['Origen_Clasificado'] == 'Proveedor') & (~df_f['Investigador Asignado'].isin(sel_inv))
                df_f = df_f[~condicion_prov]
                
            if sel_cli: 
                condicion_cli = (df_f['Origen_Clasificado'] == 'Cliente') & (~df_f['Entidad_Asociada'].isin(sel_cli))
                df_f = df_f[~condicion_cli]

            df_unicos = df_f.drop_duplicates(subset=['Incident Number'], keep='first')

            st.markdown("### Resumen General Operativo (Folios Unicos)")
            k1, k2, k3 = st.columns(3)
            k1.metric("Total de Hallazgos (Unicos)", len(df_unicos))
            k2.metric("Eventos Calidad vs Inocuidad", f"{len(df_unicos[df_unicos['Clasificacion_General'] == 'Calidad'])} / {len(df_unicos[df_unicos['Clasificacion_General'] == 'Inocuidad'])}")
            k3.metric("Tasa de Cierre", f"{(len(df_unicos[df_unicos['Estado_Simplificado'] == 'Cerrado'])/len(df_unicos)*100):.1f}%" if len(df_unicos)>0 else "0%")
            
            columnas_mostrar_unicos = [
                'Incident Number', 'Fecha', 'Mes', 'Origen_Clasificado', 'Entidad_Asociada', 
                'Investigador Asignado', 'Producto_Afectado', 'Lote_Materia_Prima', 
                'Causa_Motivo', 'Clasificacion_General', 'Estado_SLA'
            ]
            st.dataframe(df_unicos[columnas_mostrar_unicos], width="stretch", hide_index=True)
            
            with st.expander("Ver Historial Completo de Casos (Incluye sub-filas de investigacion y detalles CA/PA)"):
                columnas_mostrar_completo = ['Incident Number', 'Fecha', 'Descripción', 'Causa_Motivo', 'Estado_Simplificado']
                st.dataframe(df_f[columnas_mostrar_completo], width="stretch", hide_index=True)

        with tab_analisis:
            if df_unicos.empty:
                st.warning("No hay datos de reclamos con los filtros actuales.")
            else:
                st.markdown("*(Todos los graficos estan calculados en base a Folios Unicos, evitando duplicidades)*")
                st.markdown("#### 1. Evolucion Mensual")
                df_mes_a = df_unicos.groupby(['Mes_Num', 'Mes']).size().reset_index(name='Cantidad').sort_values('Mes_Num')
                fig_mes_a = px.bar(df_mes_a, x='Mes', y='Cantidad', text='Cantidad', color_discrete_sequence=['#00f3ff'])
                fig_mes_a.update_traces(textposition='outside', textfont=dict(size=14, color='white'))
                fig_mes_a.update_layout(**layout_oscuro, margin=dict(t=20, b=0))
                st.plotly_chart(fig_mes_a, width="stretch")
                
                c_a, c_b = st.columns(2)
                with c_a:
                    st.markdown("#### 2. Clasificacion")
                    fig_class = px.pie(df_unicos, names='Clasificacion_General', hole=0, color_discrete_sequence=['#00f3ff', '#ff6a00'])
                    fig_class.update_traces(textinfo='label+percent+value')
                    fig_class.update_layout(**layout_oscuro, margin=dict(t=20, b=0))
                    st.plotly_chart(fig_class, width="stretch")
                
                with c_b:
                    st.markdown("#### 3. Top Motivos")
                    df_mot = df_unicos['Causa_Motivo'].value_counts().reset_index().head(5)
                    fig_mot = px.bar(df_mot.sort_values('count', ascending=True), x='count', y='Causa_Motivo', orientation='h', color_discrete_sequence=['#00f3ff'])
                    fig_mot.update_layout(**layout_oscuro, margin=dict(t=20, b=0))
                    st.plotly_chart(fig_mot, width="stretch")
                
                st.markdown("#### 4. Top Materiales/Productos Afectados")
                df_prod = df_unicos['Producto_Afectado'].value_counts().reset_index().head(10)
                fig_prod = px.bar(df_prod.sort_values('count', ascending=True), x='count', y='Producto_Afectado', orientation='h', color_discrete_sequence=['#ff6a00'])
                fig_prod.update_layout(**layout_oscuro, margin=dict(t=20, b=0))
                st.plotly_chart(fig_prod, width="stretch")

        with tab_sla:
            if df_unicos.empty:
                st.warning("No hay datos para medir Tiempos de Respuesta.")
            else:
                df_abiertos = df_unicos[df_unicos['Estado_Simplificado'] == 'Abierto']
                
                st.markdown("### Indicadores de Seguimiento y Tiempos de Respuesta")
                s1, s2, s3 = st.columns(3)
                s1.metric("Folios Abiertos (Pendientes)", len(df_abiertos))
                
                atrasados = len(df_unicos[df_unicos['Estado_SLA'].str.contains('Atrasado', na=False)])
                s2.metric("Total Casos Atrasados", atrasados, "Fuera de Plazo" if atrasados > 0 else "Al Dia", delta_color="inverse")
                
                promedio_dias = round(df_abiertos['Dias_Pendientes'].mean()) if len(df_abiertos) > 0 else 0
                s3.metric("Promedio de Dias Pendientes (Casos Abiertos)", f"{promedio_dias} dias")
                
                st.markdown("---")
                c_s1, c_s2 = st.columns(2)
                
                with c_s1:
                    st.markdown("#### Cumplimiento de Plazos (SLA General)")
                    fig_sla_pie = px.pie(
                        df_unicos, names='Estado_SLA', hole=0.3, color='Estado_SLA', 
                        color_discrete_map={
                            'Cerrado a Tiempo': '#39ff14', 
                            'Pendiente a Tiempo': '#00f3ff', 
                            'Cerrado Atrasado': '#ffb300', 
                            'Pendiente Atrasado': '#ff0000',
                            'Cerrado': '#39ff14',
                            'Pendiente (Sin Plazo)': '#888888'
                        }
                    )
                    fig_sla_pie.update_traces(textinfo='label+percent')
                    fig_sla_pie.update_layout(**layout_oscuro, margin=dict(t=20, b=0))
                    st.plotly_chart(fig_sla_pie, width="stretch")

                with c_s2:
                    st.markdown("#### Dias Pendientes por Proveedor/Responsable")
                    st.markdown("*(Muestra a quienes se debe presionar para cerrar los reclamos)*")
                    if not df_abiertos.empty:
                        df_s_ab = df_abiertos.groupby('Entidad_Grafico')['Dias_Pendientes'].mean().reset_index().sort_values('Dias_Pendientes', ascending=False).head(10)
                        df_s_ab['Dias_Pendientes'] = df_s_ab['Dias_Pendientes'].round(0)
                        fig_s_ab = px.bar(df_s_ab.sort_values('Dias_Pendientes', ascending=True), x='Dias_Pendientes', y='Entidad_Grafico', text='Dias_Pendientes', orientation='h', color_discrete_sequence=['#ff0000'])
                        fig_s_ab.update_layout(**layout_oscuro, margin=dict(t=20, b=0), xaxis_title="Promedio de Dias sin Responder")
                        st.plotly_chart(fig_s_ab, width="stretch")
                    else:
                        st.success("No hay casos abiertos pendientes de seguimiento!")
                
                st.markdown("#### Detalle de Casos Criticos Pendientes")
                columnas_criticos = ['Incident Number', 'Fecha', 'Entidad_Grafico', 'Producto_Afectado', 'Dias_Pendientes', 'Estado_SLA']
                df_criticos = df_abiertos[columnas_criticos].sort_values('Dias_Pendientes', ascending=False)
                st.dataframe(df_criticos, width="stretch", hide_index=True)

else:
    with tab_global: st.info("Sube el archivo 'Base Calidad' para ver los Reclamos.")
    with tab_analisis: st.info("Sube el archivo 'Base Calidad' para ver los Analisis.")
    with tab_sla: st.info("Sube el archivo 'Base Calidad' para ver los Tiempos de Respuesta.")


# ==========================================
# LOGICA DE CAPACITACIONES
# ==========================================
with tab_capacitaciones:
    if file_train is not None:
        df_tr = procesar_capacitaciones(file_train)
        if df_tr is not None and not df_tr.empty:
            st.markdown("### Filtros de Capacitaciones")
            
            meses_tr = df_tr[['Mes_Num', 'Mes']].drop_duplicates().sort_values('Mes_Num')['Mes'].tolist()
            sel_mes_tr = st.pills("Mes (Capacitaciones)", options=meses_tr, selection_mode="multi")
            sel_curso_tr = st.pills("Curso", options=df_tr['Curso'].unique(), selection_mode="multi")
            sel_relator_tr = st.pills("Relator", options=df_tr['Relator'].unique(), selection_mode="multi")
            
            mes_tr_val = sel_mes_tr if sel_mes_tr else meses_tr
            curso_tr_val = sel_curso_tr if sel_curso_tr else df_tr['Curso'].unique()
            relator_tr_val = sel_relator_tr if sel_relator_tr else df_tr['Relator'].unique()
            
            df_tr_f = df_tr[
                (df_tr['Mes'].isin(mes_tr_val)) & 
                (df_tr['Curso'].isin(curso_tr_val)) & 
                (df_tr['Relator'].isin(relator_tr_val))
            ]
            
            if df_tr_f.empty:
                st.warning("No hay asistencias con los filtros seleccionados.")
            else:
                total_sesiones = df_tr_f['Registro_Id'].nunique()
                total_asistencias = len(df_tr_f)
                promedio = total_asistencias / total_sesiones if total_sesiones > 0 else 0
                
                st.markdown("### Indicadores de Capacitaciones (Calidad)")
                k1, k2, k3 = st.columns(3)
                k1.metric("Total Sesiones Dictadas", total_sesiones)
                k2.metric("Total Participantes Capacitados", total_asistencias)
                k3.metric("Promedio Asistentes x Sesion", f"{promedio:.1f}")
                
                st.markdown("---")
                
                c_t1, c_t2 = st.columns(2)
                with c_t1:
                    st.markdown("#### Desempeno por Relator (Nro Asistentes)")
                    df_relator = df_tr_f.groupby('Relator').agg(
                        Capacitaciones_Realizadas=('Registro_Id', 'nunique'), 
                        Total_Asistentes=('Participante', 'count')
                    ).reset_index().sort_values('Total_Asistentes', ascending=False)
                    
                    fig_relator = px.bar(
                        df_relator, x='Relator', y='Total_Asistentes', text='Total_Asistentes', 
                        hover_data=['Capacitaciones_Realizadas'], color_discrete_sequence=['#00f3ff']
                    )
                    fig_relator.update_traces(textposition='outside', textfont=dict(size=14, color='white'))
                    fig_relator.update_layout(**layout_oscuro, margin=dict(t=20, b=0), xaxis_title="Relator", yaxis_title="Total Asistentes")
                    st.plotly_chart(fig_relator, width="stretch")
                    
                with c_t2:
                    st.markdown("#### Asistencia por Sesion Cronologica")
                    df_sesiones = df_tr_f.groupby(['Fecha_Limpia', 'Curso', 'Relator', 'Registro_Id']).agg(
                        Asistentes=('Participante', 'count')
                    ).reset_index().sort_values('Fecha_Limpia', ascending=True)
                    
                    df_sesiones['Sesion_Label'] = df_sesiones['Fecha_Limpia'].astype(str) + " (" + df_sesiones['Relator'].str.split().str[0] + ")"
                    fig_sesiones = px.bar(
                        df_sesiones, x='Sesion_Label', y='Asistentes', text='Asistentes', 
                        hover_data=['Curso', 'Relator', 'Fecha_Limpia'], color_discrete_sequence=['#ff6a00']
                    )
                    fig_sesiones.update_traces(textposition='outside', textfont=dict(size=14, color='white'))
                    fig_sesiones.update_layout(**layout_oscuro, margin=dict(t=20, b=0), xaxis_title="Sesion (Fecha y Relator)", yaxis_title="Nro Asistentes")
                    st.plotly_chart(fig_sesiones, width="stretch")

                st.markdown("---")
                st.markdown("#### Auditoria Individual de Capacitaciones")
                
                lista_trab_raw = [str(x).strip() for x in
