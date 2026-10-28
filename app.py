import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# --- CONFIGURACION ---
st.set_page_config(
    page_title="Dashboard Integral",
    layout="wide"
)

st.markdown("""
<style>
.stApp { background-color: #0a0e17; }
.stMarkdown p:not(div[data-testid="stPills"] p) { color: #e2e8f0; }
label:not(div[data-testid="stPills"] label) { color: #e2e8f0; }
.stTab { color: #e2e8f0 !important; }
h1, h2, h3, h4 { color: #ff6a00 !important; }
[data-testid="stMetricValue"] { color: #39ff14 !important; }
[data-testid="stMetricLabel"] { color: #00f3ff !important; }
hr { border-bottom: 1px solid #ff6a00; }
.stAlert { background-color: #111827; border: 1px solid #ff6a00; }
div[data-testid="stPills"] button { 
    background-color: #ffffff !important; 
    border: 1px solid #d1d5db !important; 
}
div[data-testid="stPills"] button p { 
    color: #000000 !important; font-weight: 800 !important; 
}
div[data-testid="stPills"] button[aria-pressed="true"] { 
    background-color: #ff0000 !important; 
}
div[data-testid="stPills"] button[aria-pressed="true"] p { 
    color: #ffffff !important; 
}
</style>
""", unsafe_allow_html=True)

col_logo, col_tit = st.columns([1, 10])
with col_logo:
    if os.path.exists("LOGO.webp"):
        st.image("LOGO.webp", width="stretch")
with col_tit:
    st.title("Dashboard Integral - Tribu Food")
st.markdown("---")

c_up1, c_up2 = st.columns(2)
with c_up1:
    f_capa = st.file_uploader("Reclamos SFS", type=['xlsx', 'xls'])
with c_up2:
    f_train = st.file_uploader("Capacitaciones", type=['xlsx', 'xls'])

@st.cache_data(show_spinner=False)
def procesar_sfs(file):
    try:
        df = pd.read_excel(file)
        c_base = [
            'Incident Number', 'Recibido De', 'Organización', 
            'Investigador Asignado', 'Nombre del Material de Empaque', 
            'Nombre de la Materia Prima', 'Product Name', 
            'Nombre del Trabajo en Progreso', 'Código de Lote', 
            'Descripción', 'Fecha de Creación', 
            'Fecha Límite de Finalización', 
            'Fecha Límite de la Investigación', 
            'Fecha de Finalización'
        ]
        for c in c_base:
            if c not in df.columns: 
                df[c] = ''
            
        df['Incident Number'] = df['Incident Number'].fillna('Sin Folio')
        df['Incident Number'] = df['Incident Number'].astype(str).str.strip()
        
        meses = {
            1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 
            5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 
            9:'Sept', 10:'Oct', 11:'Nov', 12:'Dic'
        }
        
        fd = pd.to_datetime(df['Fecha de Creación'], errors='coerce')
        df['Fecha_Real'] = fd
        df['Fecha'] = fd.dt.date
        df['Mes_Num'] = fd.dt.month
        df['Mes'] = df['Mes_Num'].map(meses).fillna('Desc')

        df['Recibido De'] = df['Recibido De'].fillna('')
        df['Organización'] = df['Organización'].fillna('')
        df['Investigador Asignado'] = df['Investigador Asignado'].fillna('')
        df['Código de Lote'] = df['Código de Lote'].fillna('')

        def f_ori(x):
            v = str(x).strip()
            return v.capitalize() if v != '' else 'Interno'
        df['Origen_Clasificado'] = df['Recibido De'].apply(f_ori)

        def f_ent(x):
            v = str(x).strip()
            return v if v != '' else 'No Especificado'
        df['Entidad_Asociada'] = df['Organización'].apply(f_ent)

        def f_eg(r):
            if r['Origen_Clasificado'] == 'Proveedor':
                return r['Investigador Asignado']
            return r['Entidad_Asociada']
        df['Entidad_Grafico'] = df.apply(f_eg, axis=1)

        c_tipo = 'Tipo de Incidente'
        if c_tipo not in df.columns:
            c_tipo = 'Categoría del Incidente'
            
        if c_tipo in df.columns:
            def f_cla(x):
                v = str(x).strip().lower()
                return 'Inocuidad' if 'seguridad' in v else 'Calidad'
            df['Clasificacion_General'] = df[c_tipo].apply(f_cla)
        else:
            df['Clasificacion_General'] = 'Calidad'
            
        if 'Estado' in df.columns:
            def f_est(x):
                return 'Cerrado' if 'Cerrado' in str(x) else 'Abierto'
            df['Estado_Simplificado'] = df['Estado'].apply(f_est)
        else:
            df['Estado_Simplificado'] = 'Abierto'

        lim_col = 'Fecha Límite de Finalización'
        ul = df[lim_col].astype(str).str.strip().nunique() if lim_col in df.columns else 0
        if ul <= 1:
            lim_col = 'Fecha Límite de la Investigación'
        
        df['F_Lim'] = pd.to_datetime(df[lim_col], errors='coerce')
        df['F_Cie'] = pd.to_datetime(df['Fecha de Finalización'], errors='coerce')
        hoy = pd.to_datetime(datetime.today())
        
        def c_dias(r):
            if r['Estado_Simplificado'] == 'Abierto' and pd.notna(r['Fecha_Real']):
                return (hoy - r['Fecha_Real']).days
            return 0
        df['Dias_Pendientes'] = df.apply(c_dias, axis=1)

        def c_sla(r):
            if r['Estado_Simplificado'] == 'Cerrado':
                if pd.notna(r['F_Cie']) and pd.notna(r['F_Lim']):
                    return 'A Tiempo' if r['F_Cie'] <= r['F_Lim'] else 'Atrasado'
                return 'Cerrado'
            else:
                if pd.notna(r['F_Lim']):
                    return 'A Tiempo' if hoy <= r['F_Lim'] else 'Atrasado'
                return 'Pendiente'
        df['Estado_SLA'] = df.apply(c_sla, axis=1)

        def a_prod(r):
            cols = [
                'Nombre de la Materia Prima', 
                'Nombre del Material de Empaque', 
                'Product Name', 
                'Nombre del Trabajo en Progreso'
            ]
            for c in cols:
                v = str(r[c]).replace('nan', '').strip()
                if v != '': return v
            
            desc = str(r['Descripción']).lower()
            prods = [
                'mix fiesta', 'granola', 'stick maní', 'mix cajuna', 
                'castaña', 'ciruela', 'huesillo', 'nuez', 'almendra', 'maní'
            ]
            for p in prods:
                if p in desc: return p.title()
            return 'No Especificado'

        def a_lote(r):
            l = str(r['Código de Lote']).replace('nan', '').strip()
            if r['Clasificacion_General'] == 'Inocuidad':
                return l if l != '' else 'Sin Lote'
            return '-'

        df['Producto_Afectado'] = df.apply(a_prod, axis=1)
        df['Lote_Materia_Prima'] = df.apply(a_lote, axis=1)
        
        c_sub = 'Subcategoría del Incidente'
        if c_sub not in df.columns: c_sub = 'Subcategoría'
        c_cat = 'Categoría del Incidente'
        if c_cat not in df.columns: c_cat = 'Categoría'
            
        if c_sub not in df.columns: df[c_sub] = ''
        if c_cat not in df.columns: df[c_cat] = ''
        
        df['Causa_Raw'] = df[c_sub].replace('', pd.NA).fillna(df[c_cat])
        df['Causa_Raw'] = df['Causa_Raw'].fillna('No Definido')
        
        dic_mot = {
            'bitter': 'Sabor Amargo', 
            'color': 'Problemas de Color', 
            'metal': 'Presencia de Metal',
            'plastic': 'Presencia de Plástico'
        }
        
        def trad(x):
            v = str(x).strip().lower()
            return dic_mot.get(v, str(x).strip())
            
        df['Causa_Motivo'] = df['Causa_Raw'].apply(trad)
        return df
    except Exception as e:
        st.error(f"Error Reclamos: {e}")
        return None

@st.cache_data(show_spinner=False)
def procesar_capacitaciones(file):
    try:
        df = pd.read_excel(file)
        if 'Nombre curso' not in df.columns:
            df = pd.read_excel(file, skiprows=3)
        
        p_col = None
        for c in df.columns:
            if 'participante' in c.lower(): p_col = c
                
        if p_col:
            df['Participante'] = df[p_col].astype(str).str.title()
        else:
            df['Participante'] = 'Desconocido'

        inv = ['Nan', 'None', '', 'Na', 'Nat', 'NaT']
        df = df[~df['Participante'].isin(inv)]

        df['Curso'] = df.get('Nombre curso', pd.Series(dtype=str))
        df['Curso'] = df['Curso'].astype(str).str.capitalize()
        
        df['Relator'] = df.get('Nombre relator', pd.Series(dtype=str))
        df['Relator'] = df['Relator'].astype(str).str.title()
        
        df['Temas'] = df.get('Temas', pd.Series(dtype=str))
        df['Registro_Id'] = df.get('Registro Id', pd.Series(dtype=str))
        
        df['Curso'] = df['Curso'].replace('Nan', 'Sin Esp')
        df['Relator'] = df['Relator'].replace('Nan', 'Sin Esp')

        meses = {1:'Ene', 2:'Feb', 3:'Mar', 4:'Abr', 5:'May', 6:'Jun'}
        
        if 'Fecha' in df.columns:
            fd = pd.to_datetime(df['Fecha'], errors='coerce')
            df['Mes_Num'] = fd.dt.month
            df['Mes'] = df['Mes_Num'].map(meses).fillna('Desc')
            df['Fecha_Limpia'] = fd.dt.date
        else:
            df['Mes_Num'], df['Mes'], df['Fecha_Limpia'] = 99, 'Desc', pd.NaT

        return df
    except Exception as e:
        st.error(f"Error Cap: {e}")
        return None

lo = {
    "template": "plotly_dark", 
    "paper_bgcolor": "rgba(0,0,0,0)", 
    "plot_bgcolor": "rgba(0,0,0,0)", 
    "font": {"color": "#e2e8f0"}
}

t_g, t_a, t_s, t_c = st.tabs([
    "Global", "Graficos", "SLA", "Capacitaciones"
])

if f_capa is not
