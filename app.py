import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

st.set_page_config(page_title="Dashboard Integral", layout="wide")

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
        if 'Número de Incidente' in df.columns:
            if 'Incident Number' not in df.columns:
                df.rename(columns={'Número de Incidente': 'Incident Number'}, inplace=True)
        
        if 'Fecha de finalización' in df.columns:
            if 'Fecha de Finalización' not in df.columns:
                df.rename(columns={'Fecha de finalización': 'Fecha de Finalización'}, inplace=True)
        
        c_base = [
            'Incident Number', 'Recibido De', 'Organización', 
            'Investigador Asignado', 'Nombre del Material de Empaque', 
            'Nombre de la Materia Prima', 'Product Name', 
            'Nombre del Trabajo en Progreso', 'Código de Lote', 
            'Descripción', 'Fecha de Creación', 
            'Fecha Límite de Finalización', 
            'Fecha Límite de la Investigación', 'Fecha de Finalización'
        ]
        for c in c_base:
            if c not in df.columns: 
                df[c] = ''
            
        df['Incident Number'] = df['Incident Number'].fillna('Sin Folio')
        df['Incident Number'] = df['Incident Number'].astype(str).str.strip()
        
        meses = {
            1:'Ene', 2:'Feb', 3:'Mar', 4:'Abr', 5:'May', 6:'Jun', 
            7:'Jul', 8:'Ago', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dic'
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
                if 'seguridad' in v:
                    return 'Inocuidad'
                return 'Calidad'
            df['Clasificacion_General'] = df[c_tipo].apply(f_cla)
        else:
            df['Clasificacion_General'] = 'Calidad'
            
        if 'Estado' in df.columns:
            def f_est(x):
                if 'Cerrado' in str(x):
                    return 'Cerrado'
                return 'Abierto'
            df['Estado_Simplificado'] = df['Estado'].apply(f_est)
        else:
            df['Estado_Simplificado'] = 'Abierto'

        lim_col = 'Fecha Límite de Finalización'
        ul = 0
        if lim_col in df.columns:
            ul = df[lim_col].astype(str).str.strip().nunique()
            
        if ul <= 1:
            lim_col = 'Fecha Límite de la Investigación'
        
        df['F_Lim'] = pd.to_datetime(df[lim_col], errors='coerce')
        fc = 'Fecha de Finalización'
        df['F_Cie'] = pd.to_datetime(df[fc], errors='coerce')
        hoy = pd.to_datetime(datetime.today())
        
        def c_dias(r):
            if r['Estado_Simplificado'] == 'Abierto':
                if pd.notna(r['Fecha_Real']):
                    return (hoy - r['Fecha_Real']).days
            return 0
        df['Dias_Pendientes'] = df.apply(c_dias, axis=1)

        def c_sla(r):
            if r['Estado_Simplificado'] == 'Cerrado':
                if pd.notna(r['F_Cie']) and pd.notna(r['F_Lim']):
                    if r['F_Cie'] <= r['F_Lim']:
                        return 'A Tiempo'
                    return 'Atrasado'
                return 'Cerrado'
            else:
                if pd.notna(r['F_Lim']):
                    if hoy <= r['F_Lim']:
                        return 'A Tiempo'
                    return 'Atrasado'
                return 'Pendiente'
        df['Estado_SLA'] = df.apply(c_sla, axis=1)

        def a_prod(r):
            cols = [
                'Nombre del Producto Terminado',
                'Nombre de la Materia Prima', 
                'Nombre del Material de Empaque', 
                'Product Name', 
                'Nombre del Trabajo en Progreso'
            ]
            for c in cols:
                if c in df.columns:
                    v = str(r[c]).replace('nan', '').strip()
                    if v != '': return v
            
            desc = str(r['Descripción']).lower()
            prods = [
                'mix fiesta', 'granola', 'stick maní', 
                'mix cajuna', 'castaña', 'ciruela', 
                'huesillo', 'nuez', 'almendra', 'maní'
            ]
            for p in prods:
                if p in desc: 
                    return p.title()
            return 'No Especificado'

        def a_lote(r):
            l = str(r['Código de Lote']).replace('nan', '').strip()
            if r['Clasificacion_General'] == 'Inocuidad':
                return l if l != '' else 'Sin Lote'
            return '-'

        df['Producto_Afectado'] = df.apply(a_prod, axis=1)
        df['Lote_Materia_Prima'] = df.apply(a_lote, axis=1)
        
        c_sub = 'Subcategoría del Incidente'
        if c_sub not in df.columns: 
            c_sub = 'Subcategoría'
            
        c_cat = 'Categoría del Incidente'
        if c_cat not in df.columns: 
            c_cat = 'Categoría'
            
        if c_sub not in df.columns: df[c_sub] = ''
        if c_cat not in df.columns: df[c_cat] = ''
        
        df['Causa_Raw'] = df[c_sub].replace('', pd.NA)
        df['Causa_Raw'] = df['Causa_Raw'].fillna(df[c_cat])
        df['Causa_Raw'] = df['Causa_Raw'].fillna('No Definido')
        
        dic_mot = {
            'bitter': 'Sabor Amargo',
