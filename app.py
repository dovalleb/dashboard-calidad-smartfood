import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# --- CONFIGURACION ---
st.set_page_config(
    page_title="Dashboard Integral - Tribu Food", 
    layout="wide"
)

# --- ESTILOS VISUALES ---
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

div[data-testid="stPills"] button { 
    background-color: #ffffff !important; 
    border: 1px solid #d1d5db !important; 
}
div[data-testid="stPills"] button p, 
div[data-testid="stPills"] button span, 
div[data-testid="stPills"] button div { 
    color: #000000 !important; font-weight: 800 !important; 
}
div[data-testid="stPills"] button[aria-pressed="true"] { 
    background-color: #ff0000 !important; border: 1px solid #ff0000 !important; 
}
div[data-testid="stPills"] button[aria-pressed="true"] p, 
div[data-testid="stPills"] button[aria-pressed="true"] span, 
div[data-testid="stPills"] button[aria-pressed="true"] div { 
    color: #ffffff !important; 
}
</style>
""", unsafe_allow_html=True)

# --- ENCABEZADO ---
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

# --- PROCESAMIENTO DE RECLAMOS ---
@st.cache_data(show_spinner=False)
def procesar_sfs(file):
    try:
        df = pd.read_excel(file)
        
        columnas_base = [
            'Incident Number', 
            'Recibido De', 
            'Organización', 
            'Investigador Asignado', 
            'Nombre del Material de Empaque', 
            'Nombre de la Materia Prima', 
            'Product Name', 
            'Nombre del Trabajo en Progreso', 
            'Código de Lote', 
            'Descripción',
            'Fecha de Creación', 
            'Fecha Límite de Finalización', 
            'Fecha Límite de la Investigación', 
            'Fecha de Finalización'
        ]
        
        for c in columnas_base:
            if c not in df.columns: 
                df[c] = ''
            
        df['Incident Number'] = df['Incident Number'].fillna('Sin Folio')
        df['Incident Number'] = df['Incident Number'].astype(str).str.strip()
        
        meses_es = {
            1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 
            5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 
            9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'
        }
        
        fechas_dt = pd.to_datetime(df['Fecha de Creación'], errors='coerce', dayfirst=True)
        df['Fecha_Real'] = fechas_dt
        df['Fecha'] = fechas_dt.dt.date
        df['Mes_Num'] = fechas_dt.dt.month
        df['Mes'] = df['Mes_Num'].map(meses_es).fillna('Desconocido')

        df['Recibido De'] = df['Recibido De'].fillna('')
        df['Organización'] = df['Organización'].fillna('')
        df['Investigador Asignado'] = df['Investigador Asignado'].fillna('Sin Asignar')
        df['Código de Lote'] = df['Código de Lote'].fillna('')

        def fix_origen(x):
            val = str(x).strip()
            return val.capitalize() if val != '' else 'Interno'
        
        df['Origen_Clasificado'] = df['Recibido De'].apply(fix_origen)

        def fix_entidad(x):
            val = str(x).strip()
            return val if val != '' else 'No Especificado'
            
        df['Entidad_Asociada'] = df['Organización'].apply(fix_entidad)

        def fix_entidad_grafico(r):
            if r['Origen_Clasificado'] == 'Proveedor':
                return r['Investigador Asignado']
            return r['Entidad_Asociada']
            
        df['Entidad_Grafico'] = df.apply(fix_entidad_grafico, axis=1)

        col_tipo = 'Tipo de Incidente' 
        if col_tipo not in df.columns:
            col_tipo = 'Categoría del Incidente'
            
        if col_tipo in df.columns:
            def fix_clase(x):
                val = str(x).strip().lower()
                if 'seguridad alimentaria' in val:
                    return 'Inocuidad'
                return 'Calidad'
            df['Clasificacion_General'] = df[col_tipo].apply(fix_clase)
        else:
            df['Clasificacion_General'] = 'Calidad'
            
        if 'Estado' in df.columns:
            def fix_estado(x):
                if 'Cerrado' in str(x):
                    return 'Cerrado'
                return 'Abierto'
            df['Estado_Simplificado'] = df['Estado'].apply(fix_estado)
        else:
            df['Estado_Simplificado'] = 'Abierto'

        # SLA LOGIC
        unicos_limite = df['Fecha Límite de Finalización'].astype(str).str.strip().replace('', 'nan').nunique()
        if unicos_limite > 1:
            limite_col = 'Fecha Límite de Finalización'
        else:
            limite_col = 'Fecha Límite de la Investigación'
        
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
                    if r['Fecha_Cierre_SLA'] <= r['Fecha_Limite_SLA']:
                        return 'Cerrado a Tiempo'
                    else:
                        return 'Cerrado Atrasado'
                return 'Cerrado'
            else:
                if pd.notna(r['Fecha_Limite_SLA']):
                    if hoy <= r['Fecha_Limite_SLA']:
                        return 'Pendiente a Tiempo'
                    else:
                        return 'Pendiente Atrasado'
                return 'Pendiente (Sin Plazo)'
                
        df['Estado_SLA'] = df.apply(calcular_estado_sla, axis=1)

        def asignar_producto_afectado(r):
            cols_producto = [
                'Nombre de la Materia Prima', 
                'Nombre del Material de Empaque', 
                'Product Name', 
                'Nombre del Trabajo en Progreso'
            ]
            for c in cols_producto:
                val = str(r[c]).replace('nan', '').strip()
                if val != '': 
                    return val
            
            desc = str(r['Descripción']).lower()
            productos_conocidos = [
                'mix fiesta', 'granola berries', 'granola', 
                'stick maní', 'mix cajuna', 'mix frutos del bosque', 
                'castaña de cajú', 'castaña', 'ciruelas sin carozo', 
                'ciruela', 'huesillo', 'nuez', 'almendra', 'maní'
            ]
            for prod in productos_conocidos:
                if prod in desc: 
                    return prod.title()
            return 'No Especificado'

        def asignar_lote(r):
            lote = str(r['Código de Lote']).replace('nan', '').strip()
            if r['Clasificacion_General'] == 'Inocuidad': 
                if lote != '':
                    return lote
                return 'Sin Lote'
            return '-'

        df['Producto_Afectado'] = df.apply(asignar_producto_afectado, axis=1)
        df['Lote_Materia_Prima'] = df.apply(asignar_lote, axis=1)
        
        col_subcat = 'Subcategoría del Incidente' 
        if col_subcat not in df.columns:
            col_subcat = 'Subcategoría'
            
        col_cat = 'Categoría del Incidente' 
        if col_cat not in df.columns:
            col_cat = 'Categoría'
            
        if col_subcat not in df.columns: df[col_subcat] = ''
        if col_cat not in df.columns: df[col_cat] = ''
        
        df['Causa_Motivo_Raw'] = df[col_subcat].replace('', pd.NA).fillna(df[col_cat])
        df['Causa_Motivo_Raw'] = df['Causa_Motivo_Raw'].fillna('No Definido')
        
        diccionario_motivos = {
            'extraneous vegetable material': 'Material Vegetal Extraño', 
            'bitter': 'Sabor Amargo', 
            'other appearance': 'Otra Apariencia', 
            'unexpected ingredient': 'Ingrediente Inesperado', 
            'exploded bag': 'Bolsa Explotada', 
            'open and close issues': 'Problemas de Apertura y Cierre',
            'yeast and mold': 'Levaduras y Mohos', 
            'plastic': 'Presencia de Plástico', 
            'metal': 'Presencia de Metal', 
            'color': 'Problemas de Color', 
            'cuerpos extraños origen vegetal': 'Cuerpos Extraños (Vegetal)', 
            'salmonella spp.': 'Presencia de Salmonella spp.'
        }
        
        def traducir(x):
            val = str(x).strip().lower()
            return diccionario_motivos.get(val, str(x).strip())
            
        df['Causa_Motivo'] = df['Causa_Motivo_Raw'].apply(traducir)
        return df
    except Exception as e:
        st.error(f"Error procesando el archivo de Reclamos. Detalle: {e}")
        return None

# --- PROCESAMIENTO DE CAPACITACIONES ---
@st.cache_data(show_spinner=False)
def procesar_capacitaciones(file):
    try:
        df = pd.read_excel(file)
        if 'Nombre curso' not in df.columns:
            df = pd.read_excel(file, skiprows=3)
        
        part_col = None
        for c in df.columns:
            if 'participante' in c.lower():
                part_col = c
                
        if part_col:
            df['Participante'] = df[part_col].astype(str).str.strip().str.title()
        else:
            df['Participante'] = 'Desconocido'

        # Limpieza de nulos
        df = df[~df['Participante'].isin(['Nan', 'None', '', 'Na', 'Nan Nan', 'Nat', 'NaT'])]

        df['Curso'] = df.get('Nombre curso', pd.Series(dtype=str))
        df['Curso'] = df['Curso'].astype(str).str.strip().str.capitalize()
        
        df['Relator'] = df.get('Nombre relator', pd.Series(dtype=str))
        df['Relator'] = df['Relator'].astype(str).str.strip().str.title()
        
        df['Temas'] = df.get('Temas', pd.Series(dtype=str)).fillna('Sin Especificar')
        df['Registro_Id'] = df.get('Registro Id', pd.Series(dtype=str)).fillna('Sin ID')
        
        df['Curso'] = df['Curso'].replace('Nan', 'Sin Especificar')
        df['Relator'] = df['Relator'].replace('Nan', 'Sin Especificar')

        meses_es = {
            1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 
            5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 
            9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'
        }
        
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
        st.error(f"Error procesando Capacitaciones. Detalle: {e}")
        return None

layout_oscuro = dict(
    template='plotly_dark', 
    paper_bgcolor='rgba(0,0,0,0)', 
    plot_bgcolor='rgba(0,0,0,0)', 
    font=dict(color='#e2e8f0', size=14)
