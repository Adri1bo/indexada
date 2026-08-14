import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="ESIOS Toolkit", page_icon="⚡", layout="wide")
st.title("⚡ ESIOS API: Cercador i Validador d'Indicadors")

# Panell lateral per a l'autenticació
st.sidebar.header("🔑 Autenticació")
token = st.sidebar.text_input("Introdueix el teu Token d'ESIOS:", type="password")

if not token:
    st.warning("👈 Si us plau, introdueix el teu token de l'API al panell lateral per començar.")
else:
    # Capçaleres comunes i fixes requerides per l'API v1 d'ESIOS
    headers = {
        "Accept": "application/json; application/vnd.esios-api-v1+json",
        "Content-Type": "application/json",
        "x-api-key": token.strip(),
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    # Creem pestanyes a la interfície
    pestanya1, pestanya2 = st.tabs(["🔍 Cercar Indicadors (Trobar IDs)", "📈 Consultar Dades d'un ID"])

    # --- PESTANYA 1: CERCADOR D'INDICADORS ---
    with pestanya1:
        st.subheader("Busca indicadors pel seu nom o descripció")
        text_cerca = st.text_input("Paraula clau a buscar (ex: 'precio', 'pvpc', 'eolica'):", value="pvpc")
        
        if st.button("Buscar Indicadors"):
            # Endpoint oficial de cerca per text
            url_cerca = "https://api.esios.ree.es/indicators"
            params_cerca = {"text": text_cerca}
            
            with st.spinner("Buscant a la base de dades d'ESIOS..."):
                try:
                    res = requests.get(url_cerca, headers=headers, params=params_cerca, timeout=10)
                    if res.status_code == 200:
                        dades_cerca = res.json()
                        indicadors = dades_cerca.get('indicators', [])
                        
                        if indicadors:
                            st.success(f"🎉 S'han trobat {len(indicadors)} indicadors associats a '{text_cerca}':")
                            
                            # Triem les dades clau per mostrar-les en una taula neta
                            llista_neteja = []
                            for ind in indicadors:
                                llista_neteja.append({
                                    "ID (Indicador)": ind.get('id'),
                                    "Nom": ind.get('name'),
                                    "Nom Curt": ind.get('short_name'),
                                    "Actualitzat el": ind.get('values_updated_at')
                                })
                            
                            df = pd.DataFrame(llista_neteja)
                            st.dataframe(df, use_container_width=True)
                        else:
                            st.warning("No s'ha trobat cap indicador amb aquest text.")
                    else:
                        st.error(f"Error {res.status_code} al cercador. Verifica el teu token.")
                except Exception as e:
                    st.error(f"Error de connexió: {e}")

    # --- PESTANYA 2: CONSULTAR DADES D'UN ID ---
    with pestanya2:
        st.subheader("Extraure valors d'un indicador específic")
        
        col1, col2 = st.columns(2)
        with col1:
            id_indicador = st.number_input("Introdueix l'ID de l'indicador (ex: 1001 per PVPC):", min_value=1, value=1001)
        with col2:
            tipus_ruta = st.selectbox("Tipus d'indicador (Ruta de la URL):", ["indicators", "offer_indicators"])
        
        # Gestió automàtica de la data
        ara = datetime.now()
        if ara.hour < 20 or (ara.hour == 20 and ara.minute < 15):
            data_defecte = ara.strftime("%Y-%m-%d")
            text_data = f"AVUI ({data_defecte})"
        else:
            data_defecte = (ara + timedelta(days=1)).strftime("%Y-%m-%d")
            text_data = f"DEMÀ ({data_defecte})"
            
        st.info(f"📅 Es demanaran les dades de: {text_data}")

        if st.button("Obtenir Valors"):
            # Generem la URL dinàmicament segons la ruta triada pel cercador
            url_dades = f"https://api.esios.ree.es/{tipus_ruta}/{id_indicador}"
            
            params_dades = {
                "start_date": f"{data_defecte}T00:00:00",
                "end_date": f"{data_defecte}T23:59:59"
            }
            
            with st.spinner("Descarregant dades del servidor..."):
                try:
                    res = requests.get(url_dades, headers=headers, params=params_dades, timeout=10)
                    
                    if res.status_code == 200:
                        dades_finals = res.json()
                        # L'API pot respondre sota la clau 'indicator' o 'offer_indicator'
                        clau_principal = 'indicator' if 'indicator' in dades_finals else 'offer_indicator'
                        valors = dades_finals.get(clau_principal, {}).get('values', [])
                        
                        if valors:
                            st.success(f"🎉 S'han rebut {len(valors)} registres correctament!")
                            
                            # Mostrem la llista dels primers valors convertits
                            st.write("### Mostra de dades obtingudes (Primers 5 registres):")
                            for v in valors[:5]:
                                hora_neta = v.get('datetime', '')[11:16]
                                # Algunes taules usen 'value' i les d'ofertes usen 'price'
                                valor_real = v.get('value') if v.get('value') is not None else v.get('price')
                                
                                st.write(f"⏰ Hora **{hora_neta}** ➔ Valor/Preu: `{valor_real}`")
                            
                            # Permet veure el JSON complet per inspecció tècnica
                            with st.expander("🔎 Veure resposta JSON completa de l'API"):
                                st.json(dades_finals)
                        else:
                            st.warning("La connexió ha estat correcta (200), però no hi ha valors per a aquesta data.")
                            with st.expander("Veure resposta buida"):
                                st.json(dades_finals)
                    elif res.status_code in [401, 403]:
                        st.error("❌ Token denegat (401/403). Comprova que no s'hagin colat cometes o espais.")
                    else:
                        st.error(f"❌ Codi HTTP d'error {res.status_code}")
                        st.text_area("Cos de la resposta:", res.text[:500])
                        
                except Exception as e:
                    st.error(f"Error de xarxa: {e}")

