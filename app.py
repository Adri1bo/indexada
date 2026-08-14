import streamlit as st
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="Test ESIOS", page_icon="⚡")
st.title("⚡ Comprovador Token ESIOS")

# Input per posar el teu token de forma oculta
token = st.text_input("Introdueix el teu Token d'ESIOS:", type="password")

if st.button("Validar Token"):
    if not token:
        st.warning("Si us plau, introdueix un token.")
    else:
        # Decidim quina data demanar segons l'hora actual
        ara = datetime.now()
        # Si és abans de les 20:15, demanem avui (perquè demà encara no estarà publicat)
        if ara.hour < 20 or (ara.hour == 20 and ara.minute < 15):
            data_consulta = ara.strftime("%Y-%m-%d")
            st.info(f"📅 Comprovant amb els preus d'AVUI ({data_consulta})")
        else:
            data_consulta = (ara + timedelta(days=1)).strftime("%Y-%m-%d")
            st.info(f"📅 Comprovant amb els preus de DEMÀ ({data_consulta})")

        url = "https://ree.es"
        headers = {
            "Accept": "application/json; application/vnd.esios-api.v1+json",
            "Authorization": f"Token token={token}"
        }
        params = {
            "start_date": f"{data_consulta}T00:00:00",
            "end_date": f"{data_consulta}T23:59:59"
        }

        with st.spinner("Connectant amb l'API..."):
            try:
                res = requests.get(url, headers=headers, params=params, timeout=10)
                
                if res.status_code == 200:
                    st.success("🎉 Connexió un èxit! El teu token funciona perfectament.")
                    
                    dades = res.json()
                    valors = dades.get('indicator', {}).get('values', [])
                    
                    if valors:
                        st.write("### Mostra de les primeres 3 hores detectades:")
                        for hora in valors[:3]:
                            preu_kwh = hora['value'] / 1000
                            h = hora['datetime'][11:16]
                            st.write(f"⏰ Hora {h} -> **{preu_kwh:.5f} €/kWh**")
                    else:
                        st.warning("Connexió correcta, però l'API ha retornat una llista buida per a aquesta data.")
                        
                elif res.status_code == 401:
                    st.error("❌ Error 401: El token és incorrecte o ha caducat.")
                else:
                    st.error(f"❌ Error de l'API (Codi {res.status_code})")
                    
            except Exception as e:
                st.error(f"Error de xarxa: {e}")
