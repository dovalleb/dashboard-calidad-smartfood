import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Dashboard Calidad - Tribu Food", page_icon="📊", layout="wide")

# --- ESTILOS VISUALES: MODO OSCURO Y NEÓN (TRIBU FOOD) ---
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
</style>
""", unsafe_allow_html=True)

# --- ENCABEZADO CON LOGO Y TÍTULO ---
col_logo, col_tit = st.columns([1, 10])
with col_logo:
    # Verifica si el logo existe para evitar errores si cambia de nombre
    if os.path.exists("LOGO.webp"):
        st.image("LOGO.webp", use_column_width=True)
with col_tit:
    st.title("Dashboard Calidad - No conformidades")
st.markdown("---")

file_capa = st.file_uploader("📥 Arrastra aquí tu Excel 'Base Calidad' exportado desde SFS", type=['xlsx', 'xls'])
