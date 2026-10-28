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

if f_capa is not None:
    df = procesar_sfs(f_capa)
    if df is not None and not df.empty:
        with t_g:
            f1, f2, f3, f4 = st.columns(4)
            
            dm = df[['Mes_Num', 'Mes']].drop_duplicates()
            dm = dm.sort_values('Mes_Num')
            m_uni = dm['Mes'].tolist()
            
            f_mes = f1.pills("Mes", options=m_uni, selection_mode="multi")
            
            o_uni = df['Origen_Clasificado'].unique()
            f_ori = f2.pills("Origen", options=o_uni, selection_mode="multi")
            
            c_uni = df['Clasificacion_General'].unique()
            f_cla = f3.pills("Clase", options=c_uni, selection_mode="multi")
            
            e_uni = df['Estado_Simplificado'].unique()
            f_est = f4.pills("Estado", options=e_uni, selection_mode="multi")
            
            v_mes = f_mes if f_mes else m_uni
            v_ori = f_ori if f_ori else o_uni
            v_cla = f_cla if f_cla else c_uni
            v_est = f_est if f_est else e_uni
            
            c1 = df['Mes'].isin(v_mes)
            c2 = df['Origen_Clasificado'].isin(v_ori)
            c3 = df['Clasificacion_General'].isin(v_cla)
            c4 = df['Estado_Simplificado'].isin(v_est)
            
            df_t = df[c1 & c2 & c3 & c4]

            s_inv, s_cli = [], []
            if 'Proveedor' in v_ori or 'Cliente' in v_ori:
                if 'Proveedor' in v_ori:
                    i_r = df_t[df_t['Origen_Clasificado'] == 'Proveedor']
                    i_o = [x for x in i_r['Investigador Asignado'].unique() if x]
                    if i_o: 
                        s_inv = st.pills("Inv", options=i_o, selection_mode="multi")
                if 'Cliente' in v_ori:
                    c_r = df_t[df_t['Origen_Clasificado'] == 'Cliente']
                    c_o = [x for x in c_r['Entidad_Asociada'].unique() if x]
                    if c_o: 
                        s_cli = st.pills("Cli", options=c_o, selection_mode="multi")

            df_f = df_t.copy()
            
            if s_inv: 
                cp = (df_f['Origen_Clasificado'] == 'Proveedor')
                cp = cp & (~df_f['Investigador Asignado'].isin(s_inv))
                df_f = df_f[~cp]
                
            if s_cli: 
                cc = (df_f['Origen_Clasificado'] == 'Cliente')
                cc = cc & (~df_f['Entidad_Asociada'].isin(s_cli))
                df_f = df_f[~cc]

            df_u = df_f.drop_duplicates(subset=['Incident Number'])

            k1, k2, k3 = st.columns(3)
            
            t_u = len(df_u)
            k1.metric("Hallazgos", t_u)
            
            t_cal = len(df_u[df_u['Clasificacion_General'] == 'Calidad'])
            t_ino = len(df_u[df_u['Clasificacion_General'] == 'Inocuidad'])
            k2.metric("Calidad / Inocuidad", f"{t_cal} / {t_ino}")
            
            t_cer = len(df_u[df_u['Estado_Simplificado'] == 'Cerrado'])
            tc = (t_cer / t_u * 100) if t_u > 0 else 0
            k3.metric("Tasa Cierre", f"{tc:.1f}%")
            
            cm = [
                'Incident Number', 'Fecha', 'Mes', 'Origen_Clasificado', 
                'Entidad_Asociada', 'Investigador Asignado', 'Producto_Afectado', 
                'Lote_Materia_Prima', 'Causa_Motivo', 'Estado_SLA'
            ]
            st.dataframe(df_u[cm], width="stretch", hide_index=True)
            
            with st.expander("Ver Historial Completo"):
                cc = ['Incident Number', 'Fecha', 'Descripción', 'Causa_Motivo']
                st.dataframe(df_f[cc], width="stretch", hide_index=True)

        with t_a:
            if df_u.empty:
                st.warning("Sin datos.")
            else:
                d_m = df_u.groupby(['Mes_Num', 'Mes']).size().reset_index(name='C')
                d_m = d_m.sort_values('Mes_Num')
                fg_m = px.bar(
                    d_m, x='Mes', y='C', text='C', 
                    color_discrete_sequence=['#00f3ff']
                )
                fg_m.update_traces(textposition='outside')
                fg_m.update_layout(**lo, margin=dict(t=20, b=0))
                st.plotly_chart(fg_m, width="stretch")
                
                ca, cb = st.columns(2)
                with ca:
                    fg_c = px.pie(
                        df_u, names='Clasificacion_General', hole=0, 
                        color_discrete_sequence=['#00f3ff', '#ff6a00']
                    )
                    fg_c.update_traces(textinfo='label+percent')
                    fg_c.update_layout(**lo, margin=dict(t=20, b=0))
                    st.plotly_chart(fg_c, width="stretch")
                
                with cb:
                    d_mo = df_u['Causa_Motivo'].value_counts().reset_index().head(5)
                    fg_mo = px.bar(
                        d_mo.sort_values('count', ascending=True), 
                        x='count', y='Causa_Motivo', orientation='h', 
                        color_discrete_sequence=['#00f3ff']
                    )
                    fg_mo.update_layout(**lo, margin=dict(t=20, b=0))
                    st.plotly_chart(fg_mo, width="stretch")
                
                d_pr = df_u['Producto_Afectado'].value_counts().reset_index().head(10)
                fg_pr = px.bar(
                    d_pr.sort_values('count', ascending=True), 
                    x='count', y='Producto_Afectado', orientation='h', 
                    color_discrete_sequence=['#ff6a00']
                )
                fg_pr.update_layout(**lo, margin=dict(t=20, b=0))
                st.plotly_chart(fg_pr, width="stretch")

        with t_s:
            if df_u.empty:
                st.warning("Sin datos SLA.")
            else:
                d_ab = df_u[df_u['Estado_Simplificado'] == 'Abierto']
                
                s1, s2, s3 = st.columns(3)
                s1.metric("Abiertos", len(d_ab))
                
                atr = len(df_u[df_u['Estado_SLA'].str.contains('Atrasado', na=False)])
                s2.metric("Atrasados", atr)
                
                pm = round(d_ab['Dias_Pendientes'].mean()) if len(d_ab) > 0 else 0
                s3.metric("Promedio Dias", pm)
                
                c_s1, c_s2 = st.columns(2)
                
                with c_s1:
                    cs = {
                        'A Tiempo': '#39ff14', 
                        'Atrasado': '#ff0000',
                        'Cerrado': '#39ff14',
                        'Pendiente': '#888888'
                    }
                    fg_s = px.pie(
                        df_u, names='Estado_SLA', hole=0.3, 
                        color='Estado_SLA', color_discrete_map=cs
                    )
                    fg_s.update_traces(textinfo='label+percent')
                    fg_s.update_layout(**lo, margin=dict(t=20, b=0))
                    st.plotly_chart(fg_s, width="stretch")

                with c_s2:
                    if not d_ab.empty:
                        da = d_ab.groupby('Entidad_Grafico')['Dias_Pendientes']
                        da = da.mean().reset_index()
                        da = da.sort_values('Dias_Pendientes', ascending=False).head(10)
                        
                        f_ab = px.bar(
                            da.sort_values('Dias_Pendientes', ascending=True), 
                            x='Dias_Pendientes', y='Entidad_Grafico', 
                            text='Dias_Pendientes', orientation='h', 
                            color_discrete_sequence=['#ff0000']
                        )
                        f_ab.update_layout(**lo, margin=dict(t=20, b=0))
                        st.plotly_chart(f_ab, width="stretch")
                
                cols_c = [
                    'Incident Number', 'Entidad_Grafico', 
                    'Producto_Afectado', 'Dias_Pendientes'
                ]
                dc = d_ab[cols_c].sort_values('Dias_Pendientes', ascending=False)
                st.dataframe(dc, width="stretch", hide_index=True)

with t_c:
    if f_train is not None:
        d_tr = procesar_capacitaciones(f_train)
        if d_tr is not None and not d_tr.empty:
            
            d_mt = d_tr[['Mes_Num', 'Mes']].drop_duplicates()
            d_mt = d_mt.sort_values('Mes_Num')
            mt = d_mt['Mes'].tolist()
            
            s_mt = st.pills("Mes", options=mt, selection_mode="multi")
            cu = d_tr['Curso'].unique()
            s_cu = st.pills("Curso", options=cu, selection_mode="multi")
            ru = d_tr['Relator'].unique()
            s_ru = st.pills("Relator", options=ru, selection_mode="multi")
            
            v_mt = s_mt if s_mt else mt
            v_cu = s_cu if s_cu else cu
            v_ru = s_ru if s_ru else ru
            
            c1t = d_tr['Mes'].isin(v_mt)
            c2t = d_tr['Curso'].isin(v_cu)
            c3t = d_tr['Relator'].isin(v_ru)
            
            dtf = d_tr[c1t & c2t & c3t]
            
            if dtf.empty:
                st.warning("Sin asistencias.")
            else:
                ts = dtf['Registro_Id'].nunique()
                ta = len(dtf)
                
                k1, k2, k3 = st.columns(3)
                k1.metric("Sesiones", ts)
                k2.metric("Participantes", ta)
                k3.metric("Promedio Asistentes", f"{(ta/ts if ts>0 else 0):.1f}")
                
                ct1, ct2 = st.columns(2)
                with ct1:
                    dr = dtf.groupby('Relator').agg(
                        CR=('Registro_Id', 'nunique'), 
                        TA=('Participante', 'count')
                    ).reset_index().sort_values('TA', ascending=False)
                    
                    fr = px.bar(
                        dr, x='Relator', y='TA', text='TA', 
                        color_discrete_sequence=['#00f3ff']
                    )
                    fr.update_traces(textposition='outside')
                    fr.update_layout(**lo, margin=dict(t=20, b=0))
                    st.plotly_chart(fr, width="stretch")
                    
                with ct2:
                    ds = dtf.groupby(['Fecha_Limpia', 'Curso', 'Relator']).agg(
                        A=('Participante', 'count')
                    ).reset_index().sort_values('Fecha_Limpia')
                    
                    def c_lb(r):
                        f = str(r['Fecha_Limpia'])
                        rl = str(r['Relator']).split()[0]
                        return f"{f} ({rl})"
                        
                    ds['L'] = ds.apply(c_lb, axis=1)
                    fs = px.bar(
                        ds, x='L', y='A', text='A', 
                        color_discrete_sequence=['#ff6a00']
                    )
                    fs.update_traces(textposition='outside')
                    fs.update_layout(**lo, margin=dict(t=20, b=0))
                    st.plotly_chart(fs, width="stretch")

                ltr_raw = [str(x).strip() for x in dtf['Participante'].unique()]
                ltr = sorted([x for x in ltr_raw if len(x)>2 and x.lower()!='nan'])
                
                tsel = st.selectbox("Trabajador:", ltr)
                
                if tsel:
                    tc = set(dtf['Curso'].unique())
                    ctr = set(dtf[dtf['Participante'] == tsel]['Curso'].unique())
                    cf = tc - ctr
                    
                    cw1, cw2 = st.columns(2)
                    with cw1:
                        st.success(f"Realizados ({len(ctr)})")
                        for c in sorted(list(ctr)): st.write(f"- {c}")
                    with cw2:
                        if len(cf) > 0:
                            st.error(f"Pendientes ({len(cf)})")
                            for c in sorted(list(cf)): st.write(f"- {c}")
                        else: st.info("Al dia!")

                mb = (pd.crosstab(dtf['Participante'], dtf['Curso']) > 0)
                mi = mb.replace({True: "OK", False: "Falta"})
                
                tcol = len(mb.columns)
                def cpct(r):
                    return f"{(r.sum()/tcol*100):.1f}%"
                    
                mi.insert(0, 'Cumplimiento', mb.apply(cpct, axis=1))
                st.dataframe(mi, width="stretch")
