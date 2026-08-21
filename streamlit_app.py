import streamlit as st
from supabase import create_client, Client
import requests
import pandas as pd
from datetime import datetime, date

# 1. Connexió amb Supabase
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

ESIOS_TOKEN = st.secrets["esios"]["token"]
INDICATOR = 1013  # Codi per al PVPC (poti canviar-lo o fer-lo dinàmic)

st.title("⚡ Monitor d'Energia ESIOS + Supabase")

# Funció per demanar dades a ESIOS i desar-les a Supabase
def actualitzar_dades_esios():
    st.info("🔄 Descarregant dades d'ESIOS d'avui...")
    
    # Demanem les dades d'avui a ESIOS
    avui_str = date.today().isoformat()
    url = f"https://ree.es{INDICATOR}?start_date={avui_str}T00:00&end_date={avui_str}T23:59"
    headers = {
        "Accept": "application/json; application/vnd.esios-api.v2+json",
        "Content-Type": "application/json",
        "Authorization": f"Token token=\"{ESIOS_TOKEN}\""
    }
    
    resposta = requests.get(url, headers=headers)
    
    if resposta.status_code == 200:
        dades = resposta.json()
        valors = dades['indicator']['values']
        
        files_a_inserir = []
        for v in valors:
            files_a_inserir.append({
                "datetime": v['datetime'],
                "indicator_id": INDICATOR,
                "value": v['value']
            })
        
        if files_a_inserir:
            # Usem un UPSERT basat en l'índex únic per evitar duplicats
            resposta_db = supabase.table("esios_data").upsert(
                files_a_inserir, 
                on_conflict="datetime,indicator_id"
            ).execute()
            st.success(f"✅ S'han desat {len(files_a_inserir)} registres a Supabase!")
        else:
            st.warning("No s'han trobat dades noves a la API d'ESIOS.")
    else:
        st.error(f"Error en la crida a ESIOS: {resposta.status_code}")

# --- FLUX PRINCIPAL DE L'APP ---

# A. Llegir dades existents a Supabase per a l'indicador seleccionat
resposta_supabase = supabase.table("esios_data").select("*").eq("indicator_id", INDICATOR).order("datetime", ascending=True).execute()
dades_guardades = resposta_supabase.data

df = pd.DataFrame(dades_guardades)

# B. Comprovar si tenim dades suficients per a avui
avui = date.today().isoformat()
necessita_actualitzar = True

if not df.empty:
    # Convertim la columna datetime a format data per comprovar si tenim registres d'avui
    df['datetime'] = pd.to_datetime(df['datetime'])
    dades_avui = df[df['datetime'].dt.date == date.today()]
    
    # El PVPC té 24 registres diaris. Si en falten molts (ex. tenim menys de 20), actualitzem.
    if len(dades_avui) >= 20:
        necessita_actualitzar = False

# C. Si falten dades, fem la crida puntual i tornem a carregar la base de dades
if necessita_actualitzar:
    actualitzar_dades_esios()
    # Tornem a llegir un cop actualitzat
    resposta_supabase = supabase.table("esios_data").select("*").eq("indicator_id", INDICATOR).order("datetime", ascending=True).execute()
    df = pd.DataFrame(resposta_supabase.data)
    if not df.empty:
        df['datetime'] = pd.to_datetime(df['datetime'])

# D. Graficar les dades si la taula conté alguna cosa
if not df.empty:
    st.subheader(f"📈 Gràfic de l'indicador {INDICATOR}")
    
    # Preparem el DataFrame per al gràfic de Streamlit
    df_grafic = df.set_index('datetime')[['value']]
    st.line_chart(df_grafic)
    
    # Mostrar taula de dades opcionalment
    with st.expander("Veure dades en format taula"):
        st.dataframe(df)
else:
    st.warning("No hi ha dades disponibles a la base de dades ni s'han pogut descarregar.")
