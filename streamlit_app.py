import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="ESIOS Data Fetcher", page_icon="⚡", layout="wide")
st.title("⚡ Connexió i Descàrrega de dades d'ESIOS")

# 1. Llegir el token directament dels Secrets de Streamlit Cloud
if "esios" not in st.secrets or "token" not in st.secrets["esios"]:
    st.error("❌ Falta el token d'ESIOS als Secrets de Streamlit Cloud.")
    st.info("Recorda afegir-lo així a la configuració dels teus Secrets:\n\n```toml\n[esios]\ntoken = \"el-teu-token\"\n```")
else:
    token_esios = st.secrets["esios"]["token"].strip()

    # 2. Configuració de capçaleres de l'API (Ruta v1 de REE)
    headers = {
        "Accept": "application/json; application/vnd.esios-api-v1+json",
        "Content-Type": "application/json",
        "x-api-key": token_esios,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    # 3. Formulari a la pantalla principal
    st.subheader("Configuració de la descàrrega puntual")
    
    col1, col2 = st.columns(2)
    with col1:
        # Indicador 1013 és el PVPC actual
        id_indicador = st.number_input("ID de l'indicador a provar (1013 = PVPC):", min_value=1, value=1013)
    with col2:
        data_a_demanar = st.date_input("Tria el dia que vols descarregar:", value=datetime.now().date())

    # Format de data necessari per a ESIOS (YYYY-MM-DD)
    data_str = data_a_demanar.strftime("%Y-%m-%d")

    if st.button("🚀 Trucar a la API d'ESIOS"):
        url_dades = f"https://ree.es{id_indicador}"
        
        # Paràmetres del rang temporal de tot el dia seleccionat
        params_dades = {
            "start_date": f"{data_str}T00:00:00",
            "end_date": f"{data_str}T23:59:59"
        }
        
        with st.spinner(f"Connectant amb ESIOS per al dia {data_str}..."):
            try:
                res = requests.get(url_dades, headers=headers, params=params_dades, timeout=10)
                
                if res.status_code == 200:
                    dades_finals = res.json()
                    valors = dades_finals.get('indicator', {}).get('values', [])
                    
                    if valors:
                        st.success(f"🎉 Èxit! S'han rebut {len(valors)} registres d'ESIOS.")
                        
                        # Processar les dades i mostrar-les en una taula i gràfic
                        llista_taula = []
                        for v in valors:
                            llista_taula.append({
                                "Data i Hora": v.get('datetime'),
                                "Valor (Preu)": v.get('value')
                            })
                        
                        df = pd.DataFrame(llista_taula)
                        
                        st.subheader("📈 Gràfic generat des de la API")
                        df_grafic = df.set_index("Data i Hora")
                        st.line_chart(df_grafic)
                        
                        with st.expander("🔎 Veure els registres complets en format taula"):
                            st.dataframe(df, use_container_width=True)
                    else:
                        st.warning("La connexió ha estat correcta, però ESIOS diu que encara no té valors per a aquesta data.")
                
                elif res.status_code in [401, 403]:
                    st.error("❌ Token rebutjat per ESIOS (Error 401/403). Revisa el token dels teus Secrets.")
                else:
                    st.error(f"❌ Error HTTP {res.status_code} provinent d'ESIOS.")
                    st.text(res.text[:300])
                    
            except Exception as e:
                st.error(f"Error físic de connexió o de xarxa: {e}")


