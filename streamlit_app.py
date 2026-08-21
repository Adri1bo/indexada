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

INDICATOR = 1013  # Codi fix de l'indicador del PVPC per defecte

# Funció d'emergència per actualitzar dades d'un dia en concret
def actualitzar_dia_esios(data_objecte):
    data_str = data_objecte.strftime("%Y-%m-%d")
    url_dades = f"https://ree.es{INDICATOR}"
    params_dades = {
        "start_date": f"{data_str}T00:00:00",
        "end_date": f"{data_str}T23:59:59"
    }
    
    try:
        res = requests.get(url_dades, headers=headers, params=params_dades, timeout=12)
        if res.status_code == 200:
            valors = res.json().get('indicator', {}).get('values', [])
            if valors:
                files_a_guardar = []
                for v in valors:
                    files_a_guardar.append({
                        "datetime": v.get('datetime'),
                        "indicator_id": INDICATOR,
                        "value": v.get('value')
                    })
                
                # Inserció / Actualització massiva a Supabase
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

# Calculem quins dies hem de revisar de forma proactiva
avui = date.today()
dema = avui + timedelta(days=1)

# A. Llegir totes les dades existents a Supabase per a aquest indicador
resposta_db = supabase.table("esios_data").select("*").eq("indicator_id", INDICATOR).order("datetime", desc=False).execute()
df_base = pd.DataFrame(resposta_db.data)

# B. Comprovació intel·ligent automàtica dels buits de dades
necessita_recargar_app = False

if not df_base.empty:
    df_base['datetime'] = pd.to_datetime(df_base['datetime'])
    # Extraiem només la data sense hora per comprovar els dies que tenim guardats
    dies_guardats = df_base['datetime'].dt.date.unique()
else:
    dies_guardats = []

# Comprovació 1: Tenim les dades d'avui guardades (mínim 24 registres per si és horari)?
dades_avui = df_base[df_base['datetime'].dt.date == avui] if not df_base.empty else []
if avui not in dies_guardats or len(dades_avui) < 24:
    st.sidebar.warning(f"⚠️ Falten dades d'avui ({avui}). Actualitzant...")
    registres_nous = actualitzar_dia_esios(avui)
    if registres_nous > 0:
        st.sidebar.success(f"✅ S'han desat {registres_nous} hores d'avui.")
        necessita_recargar_app = True

# Comprovació 2: Són més de les 20:15h? Si és que sí, ESIOS ja publica el PVPC de demà.
ara = datetime.now()
if ara.hour > 20 or (ara.hour == 20 and ara.minute >= 15):
    dades_dema = df_base[df_base['datetime'].dt.date == dema] if not df_base.empty else []
    if dema not in dies_guardats or len(dades_dema) < 24:
        st.sidebar.warning(f"⚠️ Preus de demà disponibles. Baixant...")
        registres_nous_dema = actualitzar_dia_esios(dema)
        if registres_nous_dema > 0:
            st.sidebar.success(f"✅ S'han desat {registres_nous_dema} hores de demà.")
            necessita_recargar_app = True
else:
    st.sidebar.info("ℹ️ Els preus de demà es publicaran a partir de les 20:15h.")

# C. Si hem hagut d'actualitzar algun dia sobre la marxa, tornem a llegir la base de dades actualitzada
if necessita_recargar_app:
    resposta_db = supabase.table("esios_data").select("*").eq("indicator_id", INDICATOR).order("datetime", desc=False).execute()
    df_base = pd.DataFrame(resposta_db.data)
    if not df_base.empty:
        df_base['datetime'] = pd.to_datetime(df_base['datetime'])

# D. Visualització de dades a l'usuari
if not df_base.empty:
    st.subheader(f"📊 Evolució de Preus de l'Indicador {INDICATOR} (Dades de Supabase)")
    
    # Preparem un DataFrame net optimitzat per al gràfic de línies de Streamlit
    df_grafic = df_base.set_index('datetime')[['value']]
    st.line_chart(df_grafic)
    
    # Afegim algunes mètriques d'interès dalt del gràfic
    col_m1, col_m2 = st.columns(2)
    col_m1.metric("Total registres emmagatzemats", f"{len(df_base)} hores")
    col_m2.metric("Última actualització detectada", str(df_base['datetime'].max())[:16])

    with st.expander("🔎 Obrir l'inspector de dades de la taula"):
        st.dataframe(df_base, use_container_width=True)
else:
    st.info("La base de dades està completament buida i encara no hi ha dades disponibles a ESIOS.")
