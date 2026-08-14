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
        ara = datetime.now()
        # Si és abans de les 20:15, demanem avui
        if ara.hour < 20 or (ara.hour == 20 and ara.minute < 15):
            data_consulta = ara.strftime("%Y-%m-%d")
            st.info(f"📅 Comprovant amb els preus d'AVUI ({data_consulta})")
        else:
            data_consulta = (ara + timedelta(days=1)).strftime("%Y-%m-%d")
            st.info(f"📅 Comprovant amb els preus de DEMÀ ({data_consulta})")

        url = "https://api.esios.ree.es/indicators/1001"
        
        # CAPÇALERES CORREGIDES: Evitem que el tallafocs bloquegi la petició
        headers = {
            "Accept": "application/json; application/vnd.esios-api.v2+json", # Forçat a V2
            "Content-Type": "application/json",
            "Host": "api.esios.ree.es",
            "Authorization": f'Token token="{token}"', # Format exacte requerit per ESIOS
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        params = {
            "start_date": f"{data_consulta}T00:00:00",
            "end_date": f"{data_consulta}T23:59:59"
        }

        with st.spinner("Connectant amb l'API de Red Eléctrica..."):
            try:
                res = requests.get(url, headers=headers, params=params, timeout=10)
                
                if res.status_code == 200:
                    try:
                        dades = res.json()
                        valors = dades.get('indicator', {}).get('values', [])
                        
                        if valors:
                            st.success("🎉 Connexió amb èxit! El teu token funciona perfectament.")
                            st.write("### Mostra de les primeres 3 hores detectades:")
                            for hora in valors[:3]:
                                preu_kwh = hora['value'] / 1000
                                h = hora['datetime'][11:16]
                                st.write(f"⏰ Hora {h} -> **{preu_kwh:.5f} €/kWh**")
                        else:
                            st.warning("Connexió correcta, però l'API ha retornat una llista buida per a aquesta data.")
                    except ValueError:
                        st.error("❌ El servidor ha respòs, però el contingut continua sense ser un JSON vàlid.")
                        st.text_area("Inici de la resposta rebuda:", res.text[:300])
                        
                elif res.status_code in [401, 403]:
                    st.error("❌ Error d'autenticació (401/403): El token és incorrecte o ha caducat.")
                    st.info("💡 Recorda que si el teu token té força temps, ESIOS els sol desactivar per inactivitat. En pots demanar un de nou a consultasios@ree.es.")
                else:
                    st.error(f"❌ Error de l'API (Codi HTTP {res.status_code})")
                    st.text_area("Detall de la resposta:", res.text[:300])
                    
            except Exception as e:
                st.error(f"Error de xarxa o connexió: {e}")
