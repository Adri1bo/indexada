import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta, date
from supabase import create_client, Client

st.set_page_config(page_title="ESIOS + Supabase Dashboard", page_icon="📈", layout="wide")
st.title("📈 Quadre de Comandament ESIOS + Supabase")

# 1. Connexió Segura utilitzant els Secrets nets
SUPABASE_URL = st.secrets["supabase"]["url"].strip().rstrip("/")
SUPABASE_KEY = st.secrets["supabase"]["key"].strip()
TOKEN_ESIOS = st.secrets["esios"]["token"].strip()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

headers = {
    "Accept": "application/json; application/vnd.esios-api-v1+json",
    "Content-Type": "application/json",
    "x-api-key": TOKEN_ESIOS,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# --- SELECCIÓ DINÀMICA DE L'INDICADOR AL MENÚ LATERAL ---
st.sidebar.header("🎯 Selecció de l'Indicador")

# Diccionari amb indicadors habituals per fer la interfície més humana
indicadors_habituals = {
    "Mercat Diari OMIE (10211)": {"id": 10211, "ruta": "indicators"},
    "Componentes precio energía cierre desglose (10229)": {"id": 10229, "ruta": "indicators"},
    "Precio Mercado Diario España (1011)": {"id": 1011, "ruta": "indicators"},
    "Otro indicador (Introducir ID manual)": {"id": None, "ruta": "indicators"}
}

opcio_triada = st.sidebar.selectbox(
    "Tria quin indicador vols analitzar:",
    options=list(indicadors_habituals.keys())
)

# Gestió de l'ID segons la selecció de l'usuari
if opcio_triada == "Otro indicador (Introducir ID manual)":
    INDICATOR = st.sidebar.number_input("Introdueix l'ID de l'indicador d'ESIOS:", min_value=1, value=10211, step=1)
    TIPUS_RUTA = st.sidebar.selectbox("Tipus de ruta d'API:", ["indicators", "offer_indicators"])
else:
    INDICATOR = indicadors_habituals[opcio_triada]["id"]
    TIPUS_RUTA = indicadors_habituals[opcio_triada]["ruta"]

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Estat de la Sincronització")

# Funció d'emergència per actualitzar dades d'un dia en concret
# Funció d'emergència per actualitzar dades d'un dia en concret
def actualitzar_dia_esios(data_objecte):
    data_str = data_objecte.strftime("%Y-%m-%d")
    
    # Construcció de la URL
    url_dades = f"https://api.esios.ree.es/{TIPUS_RUTA}/{INDICATOR}"
    
    # MOSTRAM LA URL A LA PANTALLA PER INSPECCIONAR-LA
    st.sidebar.info(f"🔍 URL trucada: {url_dades}")
    
    params_dades = {
        "start_date": f"{data_str}T00:00:00",
        "end_date": f"{data_str}T23:59:59"
    }
    
    try:
        res = requests.get(url_dades, headers=headers, params=params_dades, timeout=12)
        
        # Mostrem també el codi de resposta real de la API al costat
        st.sidebar.text(f"📡 Codi resposta: {res.status_code}")
        
        if res.status_code == 200:
            dades_finals = res.json()
            clau_principal = 'indicator' if 'indicator' in dades_finals else 'offer_indicator'
            valors = dades_finals.get(clau_principal, {}).get('values', [])
            
            if valors:
                files_a_guardar = []
                for v in valors:
                    valor_real = v.get('value') if v.get('value') is not None else v.get('price')
                    files_a_guardar.append({
                        "datetime": v.get('datetime'),
                        "indicator_id": INDICATOR,
                        "value": valor_real
                    })
                
                try:
                    supabase.table("esios_data").upsert(
                        files_a_guardar, 
                        on_conflict="datetime,indicator_id"
                    ).execute()
                    return len(files_a_guardar)
                except Exception as error_sb:
                    st.sidebar.error(f"❌ Error de Supabase al desar: {error_sb}")
                    return 0
            else:
                st.sidebar.warning(f"⚠️ ESIOS ha respost buit per al dia {data_str}.")
        else:
            st.sidebar.error(f"❌ Error ESIOS Codi: {res.status_code}")
    except Exception as e:
        st.sidebar.error(f"❌ Error de xarxa: {e}")
    return 0


# --- FLUX PRINCIPAL DE L'APP ---

avui = date.today()
dema = avui + timedelta(days=1)
necessita_recargar_app = False

# A. Llegir totes les dades de Supabase de l'indicador seleccionat actualment
try:
    resposta_db = supabase.table("esios_data").select("*").eq("indicator_id", INDICATOR).order("datetime", desc=False).execute()
    df_base = pd.DataFrame(resposta_db.data)
except Exception as error_lectura:
    st.error(f"❌ No s'ha pogut llegir de Supabase: {error_lectura}")
    df_base = pd.DataFrame()

# B. Comprovació intel·ligent automàtica dels buits de dades d'aquest indicador
if df_base.empty:
    st.sidebar.warning(f"🚨 Taula buida per al {INDICATOR}. Inicialitzant avui ({avui})...")
    registres_nous = actualitzar_dia_esios(avui)
    if registres_nous > 0:
        st.sidebar.success(f"✅ Guardats els primers {registres_nous} registres.")
        necessita_recargar_app = True
else:
    df_base['datetime'] = pd.to_datetime(df_base['datetime'])
    dies_guardats = df_base['datetime'].dt.date.unique()
    
    # Comprovem la integritat del dia d'avui (mínim 24 hores guardades)
    dades_avui = df_base[df_base['datetime'].dt.date == avui]
    if avui not in dies_guardats or len(dades_avui) < 24:
        st.sidebar.warning(f"⚠️ Falten dades d'avui ({avui}). Actualitzant...")
        registres_nous = actualitzar_dia_esios(avui)
        if registres_nous > 0:
            st.sidebar.success(f"✅ Afegits {registres_nous} registres d'avui.")
            necessita_recargar_app = True

# Comprovació de demà (només si ja s'han publicat dades després de les 20:15h)
ara = datetime.now()
if ara.hour > 20 or (ara.hour == 20 and ara.minute >= 15):
    if not df_base.empty:
        df_base['datetime'] = pd.to_datetime(df_base['datetime'])
        dies_guardats = df_base['datetime'].dt.date.unique()
        dades_dema = df_base[df_base['datetime'].dt.date == dema]
    else:
        dies_guardats = []
        dades_dema = []
        
    if dema not in dies_guardats or len(dades_dema) < 24:
        st.sidebar.warning(f"⚠️ Preus de demà disponibles. Baixant...")
        registres_nous_dema = actualitzar_dia_esios(dema)
        if registres_nous_dema > 0:
            st.sidebar.success(f"✅ Desats els registres de demà.")
            necessita_recargar_app = True
else:
    st.sidebar.info("ℹ️ Els preus de demà es publicaran a partir de les 20:15h.")

# C. Recarregar dades de la base de dades si s'ha fet cap descàrrega sobre la marxa
if necessita_recargar_app:
    resposta_db = supabase.table("esios_data").select("*").eq("indicator_id", INDICATOR).order("datetime", desc=False).execute()
    df_base = pd.DataFrame(resposta_db.data)
    if not df_base.empty:
        df_base['datetime'] = pd.to_datetime(df_base['datetime'])

# D. Visualització final del panell de control filtrat pel selector
if not df_base.empty:
    st.subheader(f"📊 Anàlisi de l'Indicador Seleccionat: {INDICATOR}")
    
    # Disseny de mètriques d'informació general
    col_m1, col_m2 = st.columns(2)
    col_m1.metric("Total dades emmagatzemades a Supabase", f"{len(df_base)} registres")
    col_m2.metric("Últim registre temporal actiu", str(df_base['datetime'].max())[:16])
    
    # Creació del gràfic de línies de Streamlit
    df_grafic = df_base.set_index('datetime')[['value']]
    st.line_chart(df_grafic)
    
    with st.expander("🔎 Obrir l'inspector de la taula de Supabase"):
        st.dataframe(df_base, use_container_width=True)
else:
    st.info("ℹ️ No hi ha registres emmagatzemats per a aquest indicador ni s'han pogut extreure valors d'ESIOS de la data d'avui.")
