import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Dashboard CAPA - Smart Food Safe", page_icon="🛡️", layout="wide")

# --- ESTILOS VISUALES: MODO OSCURO Y NEÓN (TRIBU FOOD) ---
st.markdown("""
<style>
/* Fondo oscuro para toda la aplicación */
.stApp {
    background-color: #0a0e17;
}

/* Color de texto general */
.stMarkdown, p, label {
    color: #e2e8f0 !important;
}

/* Títulos con brillo Naranja Tribu Neón */
h1, h2, h3 {
    color: #ff6a00 !important;
    text-shadow: 0px 0px 12px rgba(255, 106, 0, 0.8);
}

/* KPIs y Métricas - Valores en Verde Neón */
[data-testid="stMetricValue"] {
    color: #39ff14 !important; 
    text-shadow: 0px 0px 12px rgba(57, 255, 20, 0.8);
}

/* KPIs y Métricas - Etiquetas en Cian Neón */
[data-testid="stMetricLabel"] {
    color: #00f3ff !important;
    text-shadow: 0px 0px 8px rgba(0, 243, 255, 0.5);
}

/* Líneas separadoras con brillo naranja */
hr {
    border-bottom: 1px solid #ff6a00;
    box-shadow: 0px 0px 8px #ff6a00;
}

/* Cajas de alerta o información */
.stAlert {
    background-color: #111827;
    border: 1px solid #ff6a00;
}
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Panel de Control - No Conformidades (CAPA)")
st.markdown("Plataforma de análisis dinámico conectado a Smart Food Safe")
st.markdown("---")

# --- ZONA DE CARGA ---
st.markdown("### 📥 Carga de Reporte SFS")
file_capa = st.file_uploader("Arrastra aquí tu Excel 'Base Calidad' exportado desde SFS", type=['xlsx', 'xls'])

# --- PROCESAMIENTO DE DATOS ---
@st.cache_data(show_spinner=False)
def procesar_sfs(file):
    try:
        df = pd.read_excel(file)
        
        # 1. Estandarización de Fecha
        if 'Fecha de Creación' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha de Creación'], format='%d-%m-%Y', errors='coerce').dt.date
        else:
            df['Fecha'] = pd.NaT

        # 2. Consolidación de Entidad
        df['Organización'] = df['Organización'].fillna('')
        df['Nombre del Proveedor'] = df['Nombre del Proveedor'].fillna('')
        
        def determinar_entidad(row):
            if row['Nombre del Proveedor'] != '': return row['Nombre del Proveedor']
            if row['Organización'] != '': return row['Organización']
            return 'Interno / Planta'
            
        df['Entidad_Asociada'] = df.apply(determinar_entidad, axis=1)

        # 3. Determinar Origen
        def determinar_origen(row):
            if row['Nombre del Proveedor'] != '': return 'Proveedor'
            if row['Organización'] != '': return 'Cliente'
            return 'Interno'
            
        df['Origen_Clasificado'] = df.apply(determinar_origen, axis=1)

        # 4. Calidad vs Inocuidad
        def clasificar_severidad(tipo):
            tipo = str(tipo).lower()
            if 'seguridad alimentaria' in tipo or 'inocuidad' in tipo or 'microbiológica' in tipo:
                return 'Inocuidad'
            return 'Calidad'
            
        col_tipo = 'Tipo de Incidente' if 'Tipo de Incidente' in df.columns else 'Categoría del Incidente'
        df['Clasificacion_General'] = df[col_tipo].apply(clasificar_severidad)

        # 5. Estado Simplificado
        df['Estado_Simplificado'] = df['Estado'].apply(lambda x: 'Cerrado' if 'Cerrado' in str(x) else 'Abierto')

        # 6. Limpieza Producto y Motivo
        df['Producto_Afectado'] = df['Product Name'].fillna(df['Origin Type']).fillna('No Especificado')
        df['Causa_Motivo'] = df['Subcategoría del Incidente'].fillna(df['Categoría del Incidente']).fillna('No Definido')

        cols_finales = ['Incident Number', 'Fecha', 'Origen_Clasificado', 'Entidad_Asociada', 
                        'Producto_Afectado', 'Causa_Motivo', 'Clasificacion_General', 
                        'Estado_Simplificado', 'Severidad']
        
        cols_existentes = [c for c in cols_finales if c in df.columns]
        return df[cols_existentes]

    except Exception as e:
        st.error(f"Error procesando el archivo: {e}")
        return None

# --- LÓGICA DE INTERFAZ Y GRÁFICOS ---
if file_capa is not None:
    df = procesar_sfs(file_capa)
    
    if df is not None and not df.empty:
        # --- FILTROS GLOBALES ---
        st.markdown("---")
        st.markdown("### 🔍 Filtros")
        
        f1, f2, f3, f4 = st.columns(4)
        filtro_origen = f1.multiselect("Origen", df['Origen_Clasificado'].unique(), default=df['Origen_Clasificado'].unique())
        filtro_clase = f2.multiselect("Clasificación", df['Clasificacion_General'].unique(), default=df['Clasificacion_General'].unique())
        filtro_estado = f3.multiselect("Estado", df['Estado_Simplificado'].unique(), default=df['Estado_Simplificado'].unique())
        
        df_f = df[
            (df['Origen_Clasificado'].isin(filtro_origen)) &
            (df['Clasificacion_General'].isin(filtro_clase)) &
            (df['Estado_Simplificado'].isin(filtro_estado))
        ]

        # --- KPIs ---
        st.markdown("---")
        total = len(df_f)
        calidad_count = len(df_f[df_f['Clasificacion_General'] == 'Calidad'])
        inocuidad_count = len(df_f[df_f['Clasificacion_General'] == 'Inocuidad'])
        cerrados = len(df_f[df_f['Estado_Simplificado'] == 'Cerrado'])
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total de Hallazgos", total)
        k2.metric("Eventos de Calidad", calidad_count)
        k3.metric("Eventos de Inocuidad", inocuidad_count)
        k4.metric("Tasa de Cierre", f"{(cerrados/total*100):.1f}%" if total > 0 else "0%")

        # --- GRÁFICOS CON THEMA OSCURO Y NEÓN ---
        st.markdown("---")
        c1, c2 = st.columns(2)
        
        # Opciones comunes para gráficos oscuros de Plotly para que el fondo sea transparente
        layout_oscuro = dict(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e2e8f0')
        )
        
        with c1:
            st.markdown("**Calidad vs Inocuidad**")
            # Naranja Neón y Cian Neón
            fig_pie = px.pie(df_f, names='Clasificacion_General', hole=0.5, color_discrete_sequence=['#00f3ff', '#ff6a00'])
            fig_pie.update_layout(**layout_oscuro)
            st.plotly_chart(fig_pie, use_container_width=True, theme=None)
            
        with c2:
            st.markdown("**Estado de Reclamos (Abierto vs Cerrado)**")
            df_est = df_f['Estado_Simplificado'].value_counts().reset_index()
            df_est.columns = ['Estado', 'Cantidad']
            # Verde Neón (Cerrado) y Rojo/Magenta Neón (Abierto)
            fig_est = px.bar(df_est, x='Cantidad', y='Estado', orientation='h', color='Estado', color_discrete_map={'Cerrado':'#39ff14', 'Abierto':'#ff0055'})
            fig_est.update_layout(**layout_oscuro)
            st.plotly_chart(fig_est, use_container_width=True, theme=None)

        c3, c4 = st.columns(2)
        
        with c3:
            st.markdown("**Top 10: Motivos de Reclamo / Hallazgos**")
            df_motivos = df_f['Causa_Motivo'].value_counts().head(10).reset_index()
            df_motivos.columns = ['Motivo', 'Cantidad']
            # Cian Neón
            fig_mot = px.bar(df_motivos, x='Cantidad', y='Motivo', orientation='h', color_discrete_sequence=['#00f3ff'])
            fig_mot.update_layout(**layout_oscuro, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_mot, use_container_width=True, theme=None)

        with c4:
            st.markdown("**Top 10: Entidades (Clientes y Proveedores)**")
            df_ent = df_f[df_f['Entidad_Asociada'] != 'Interno / Planta']['Entidad_Asociada'].value_counts().head(10).reset_index()
            df_ent.columns = ['Entidad', 'Cantidad']
            # Naranja Neón Tribu
            fig_ent = px.bar(df_ent, x='Cantidad', y='Entidad', orientation='h', color_discrete_sequence=['#ff6a00'])
            fig_ent.update_layout(**layout_oscuro, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_ent, use_container_width=True, theme=None)

        # --- TABLA INFERIOR ---
        st.markdown("---")
        st.markdown("**Registro Detallado (Exportable)**")
        st.dataframe(df_f, use_container_width=True, hide_index=True)

else:
    st.info("💡 Arrastra el archivo 'Base Calidad.xlsx' de Smart Food Safe para generar tu Dashboard.")
