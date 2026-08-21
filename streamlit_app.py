import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client

st.set_page_config(page_title="ESIOS to Supabase", page_icon="⚡", layout="wide")
st.title("⚡ Enviament de dades d'ESIOS a Supabase")

# 1. Validar configuració de Secrets (Supabase + ESIOS)
credencials_ok = True
if "supabase" not in st.secrets or "url" not in st.secrets["supabase"] or "key" not in st.secrets["supabase"]:
    st.error("❌ Falten les credencials de Supabase als Secrets.")
    credencials_ok = False
if "esios" not in st.secrets or "token" not in st.secrets["esios"]:
    st.error("❌ Falta el token d'ESIOS als Secrets.")
    credencials_ok = False

if credencials_ok:
    # Inicialitzar clients de forma neta
    SUPABASE_URL = st.secrets["supabase"]["url"].strip()
    SUPABASE_KEY = st.secrets["supabase"]["key"].strip()
    TOKEN_ESIOS = st.secrets["esios"]["token"].strip()
    
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    headers = {
        "Accept": "application/json; application/vnd.esios-api-v1+json",
        "Content-Type": "application/json",
        "x-api-key": TOKEN_ESIOS,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    # 2. Controls de la pantalla principal
    st.subheader("📥 Pas 1: Configura la descàrrega")
    col1, col2 = st.columns(2)
    with col1:
        id_indicador = st.number_input("ID de l'indicador (1013 = PVPC):", min_value=1, value=817)
    with col2:
        data_a_demanar = st.date_input("Tria el dia a processar:", value=datetime.now().date())

    data_str = data_a_demanar.strftime("%Y-%m-%d")

    # 3. Acció: Baixar d'ESIOS i Desar a Supabase
    if st.button("🚀 Executar: Descarregar i Desar a Supabase"):
        url_dades = f"https://api.esios.ree.es/indicators/{id_indicador}"
        params_dades = {
            "start_date": f"{data_str}T00:00:00",
            "end_date": f"{data_str}T23:59:59"
        }
        
        with st.spinner("Descarregant de la API d'ESIOS..."):
            try:
                res = requests.get(url_dades, headers=headers, params=params_dades, timeout=12)
                
                if res.status_code == 200:
                    dades_json = res.json()
                    valors = dades_json.get('indicator', {}).get('values', [])
                    
                    if valors:
                        st.success(f"📥 Rebuts {len(valors)} registres d'ESIOS.")
                        
                        # Preparem el format de files que demana Supabase
                        files_a_guardar = []
                        for v in valors:
                            files_a_guardar.append({
                                "datetime": v.get('datetime'),
                                "indicator_id": id_indicador,
                                "value": v.get('value')
                            })
                        
                        # --- ENVIAMENT A SUPABASE ---
                        with st.spinner("Pujant les dades a la taula de Supabase..."):
                            # on_conflict indica que si coincideix datetime i indicator_id apliqui un UPDATE en lloc de donar error
                            resposta_db = supabase.table("esios_data").upsert(
                                files_a_guardar, 
                                on_conflict="datetime,indicator_id"
                            ).execute()
                            
                            st.balloons()
                            st.success(f"🎉 Èxit Total! S'han guardat/actualitzat els {len(files_a_guardar)} registres a Supabase.")
                            
                            # Mostrem una vista prèvia del que s'ha guardat
                            df_guardat = pd.DataFrame(files_a_guardar)
                            st.dataframe(df_guardat, use_container_width=True)
                    else:
                        st.warning("No s'han trobat dades a ESIOS per a aquesta data.")
                else:
                    st.error(f"Error d'ESIOS. Codi: {res.status_code}")
                    
            except Exception as e:
                st.error(f"S'ha produït un error en el circuit: {e}")

