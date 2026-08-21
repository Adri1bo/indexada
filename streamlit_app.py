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

INDICATOR = 1013  # Codi fix del PVPC
TIPUS_RUTA = "indicators"  # Tipus de ruta per al PVPC (comprovat al teu cercador)

# Funció d'emergència per actualitzar dades d'un dia en concret
def actualitzar_dia_esios(data_objecte):
    data_str = data_objecte.strftime("%Y-%m-%d")
    
    # LA TEVA URL EXACTA QUE FUNCIONA:
    url_dades = f"https://api.esios.ree.es/{TIPUS_RUTA}/{INDICATOR}"
    
    params_dades = {
        "start_date": f"{data_str}T00:00:00",
        "end_date": f"{data_str}T23:59:59"
    }
    
    try:
        res = requests.get(url_dades, headers=headers, params=params_dades, timeout=12)
        if res.status_code == 200:
            dades_finals = res.json()
            # L'API pot respondre sota 'indicator' o 'offer_indicator' segons la ruta
            clau_principal = 'indicator' if 'indicator' in dades_finals else 'offer_indicator'
            valors = dades_finals.get(clau_principal, {}).get('values', [])
            
            if valors:
                files_a_guardar = []
                for v in valors:
                    # Gestionem que useu 'value' o 'price' segons l'indicador
                    valor_real = v.get('value') if v.get('value') is not None else v.get('price')
                    
                    files_a_guardar.append({
                        "datetime": v.get('datetime'),
                        "indicator_id": INDICATOR,
                        "value": valor_real
                    })
                
                # Inserció massiva amb upsert a Supabase
                supabase.table("esios_data").upsert(
                    files_a_guardar, 
                    on_conflict="datetime,indicator_id"
                ).execute()
                return len(files_a_guardar)
    except Exception as e:
        st.sidebar.error(f"Error actualitzant el dia {data_str}: {e}")
    return 0

# --- FLUX PRINCIPAL DE L'APP ---

st.sidebar.header("⚙️ Estat de la Sincronització")

avui = date.today()
dema = avui + timedelta(days=1)
necessita_recargar_app = False

# A. Llegir totes les dades de Supabase
resposta_db = supabase.table("esios_data").select("*").eq("indicator_id", INDICATOR).order("datetime", desc=False).execute()
df_base = pd.DataFrame(resposta_db.data)

# B. Comprovació intel·ligent per a bases de dades buides o incompletes
if df_base.empty:
    st.sidebar.warning(f"🚨 Base de dades buida. Inicialitzant dades d'avui ({avui})...")
    registres_nous = actualitzar_dia_esios(avui)
    if registres_nous > 0:
        st.sidebar.success(f"✅ S'han guardat els primers {registres_nous} registres d'avui.")
        necessita_recargar_app = True
else:
    df_base['datetime'] = pd.to_datetime(df_base['datetime'])
    dies_guardats = df_base['datetime'].dt.date.unique()
    
    # Comprovar si avui té les 24 hores completes
    dades_avui = df_base[df_base['datetime'].dt.date == avui]
    if avui not in dies_guardats or len(dades_avui) < 24:
        st.sidebar.warning(f"⚠️ Falten dades d'avui ({avui}). Actualitzant...")
        registres_nous = actualitzar_dia_esios(avui)
        if registres_nous > 0:
            st.sidebar.success(f"✅ S'han afegit {registres_nous} hores d'avui.")
            necessita_recargar_app = True

# Comprovació de demà (només si ja s'han publicat els preus després de les 20:15h)
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
            st.sidebar.success(f"✅ S'han desat {registres_nous_dema} hores de demà.")
            necessita_recargar_app = True
else:
    st.sidebar.info("ℹ️ Els preus de demà es publicen a partir de les 20:15h.")

# C. Recarregar dades de la base de dades si s'ha fet cap descàrrega
if necessita_recargar_app:
    resposta_db = supabase.table("esios_data").select("*").eq("indicator_id", INDICATOR).order("datetime", desc=False).execute()
    df_base = pd.DataFrame(resposta_db.data)
    if not df_base.empty:
        df_base['datetime'] = pd.to_datetime(df_base['datetime'])

# D. Visualització final del panell de control
if not df_base.empty:
    st.subheader(f"📊 Evolució de Preus del PVPC (Indicador {INDICATOR})")
    
    # Mètriques clau resumides dalt del gràfic
    col_m1, col_m2 = st.columns(2)
    col_m1.metric("Total dades emmagatzemades", f"{len(df_base)} hores")
    col_m2.metric("Última hora registrada", str(df_base['datetime'].max())[:16])
    
    # Creació del gràfic de línies de Streamlit
    df_grafic = df_base.set_index('datetime')[['value']]
    st.line_chart(df_grafic)
    
    with st.expander("🔎 Obrir l'inspector de la taula de Supabase"):
        st.dataframe(df_base, use_container_width=True)
else:
    st.error("❌ No s'ha pogut inicialitzar l'aplicació. Verifica les teves claus de Supabase.")
