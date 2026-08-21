import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import calendar

st.set_page_config(page_title="ESIOS Monthly Fetcher", page_icon="⚡", layout="wide")
st.title("⚡ Descàrrega Mensual de Components de Preu (ESIOS)")

# 1. Llegir el token dels Secrets
if "esios" not in st.secrets or "token" not in st.secrets["esios"]:
    st.error("❌ Falta el token d'ESIOS als Secrets de Streamlit Cloud.")
else:
    token_esios = st.secrets["esios"]["token"].strip()

    headers = {
        "Accept": "application/json; application/vnd.esios-api-v1+json",
        "Content-Type": "application/json",
        "x-api-key": token_esios,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    st.subheader("🗓️ Filtre Temporal Mensual")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Permetem triar l'indicador (per defecte 10229, molt comú en desglossaments de tancament)
        id_indicador = st.number_input("ID de l'indicador de components:", min_value=1, value=10229)
        
    with col2:
        anys = [r for r in range(datetime.now().year - 4, datetime.now().year + 1)]
        any_triat = st.selectbox("Selecciona l'Any:", anys, index=len(anys)-1)
        
    with col3:
        mesos = list(calendar.month_name)[1:] # Llista de noms de mesos en anglès/local
        mes_triat = st.selectbox("Selecciona el Mes:", mesos, index=datetime.now().month - 1)

    # Convertim el nom del mes al seu número corresponent (1-12)
    num_mes = mesos.index(mes_triat) + 1
    
    # Calculem automàticament el primer i l'últim dia d'aquell mes concret
    primer_dia = f"{any_triat}-{num_mes:02d}-01"
    ultim_dia_num = calendar.monthrange(any_triat, num_mes)[1]
    ultim_dia = f"{any_triat}-{num_mes:02d}-{ultim_dia_num:02d}"

    st.info(f"📅 Es demanaran les dades des del **{primer_dia}** fins al **{ultim_dia}**")

    if st.button("🚀 Descarregar Mes Sencer d'ESIOS"):
        # Utilitzem la ruta que has esmenat i que et funciona bé
        url_dades = f"https://api.esios.ree.es/indicators/{id_indicador}"
        
        params_dades = {
            "start_date": f"{primer_dia}T00:00:00",
            "end_date": f"{ultim_dia}T23:59:59"
        }
        
        with st.spinner(f"Sol·licitant dades mensuals a ESIOS..."):
            try:
                res = requests.get(url_dades, headers=headers, params=params_dades, timeout=15)
                
                if res.status_code == 200:
                    dades_finals = res.json()
                    valors = dades_finals.get('indicator', {}).get('values', [])
                    
                    if valors:
                        st.success(f"🎉 Èxit! S'han rebut {len(valors)} registres horaris d'aquest mes.")
                        
                        # Processar el volum mensual de dades
                        llista_taula = []
                        for v in valors:
                            llista_taula.append({
                                "Data i Hora": v.get('datetime'),
                                "Preu (€/MWh)": v.get('value')
                            })
                        
                        df = pd.DataFrame(llista_taula)
                        
                        # Netegem la visualització de la data perquè el gràfic quedi més net
                        df['Data i Hora'] = pd.to_datetime(df['Data i Hora'])
                        
                        st.subheader(f"📈 Evolució del Preu de l'Indicador {id_indicador} durant el mes")
                        df_grafic = df.set_index("Data i Hora")
                        st.line_chart(df_grafic)
                        
                        with st.expander("🔎 Veure i analitzar la taula de dades completa"):
                            st.dataframe(df, use_container_width=True)
                    else:
                        st.warning("L'API ha respost correctament, però no hi ha registres per a aquest mes o indicador.")
                else:
                    st.error(f"❌ Error HTTP {res.status_code} provinent d'ESIOS.")
                    st.text(res.text[:300])
                    
            except Exception as e:
                st.error(f"Error de xarxa o de temps d'espera (Timeout): {e}")



