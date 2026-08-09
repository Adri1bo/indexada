
import streamlit as st
import pandas as pd
import requests
import datetime
import plotly.express as px

st.set_page_config(page_title="API Llum Indexada", layout="wide", page_icon="⚡")
st.title("⚡ Connexió Directa a l'API de Red Eléctrica")

# 1. Input de l'usuari
st.sidebar.header("🔧 Configuració")
marge = st.sidebar.number_input("Marge de la comercialitzadora (€/kWh)", min_value=0.000, value=0.010, format="%.3f")

# 2. Extracció de dades amb capçaleres de seguretat (Evita el bucle de càrrega)
@st.cache_data(ttl=1800)
def carregar_api_ree():
    avui = datetime.date.today().strftime("%Y-%m-%d")
    url = f"https://ree.es{avui}T00:00&end_date={avui}T23:59&time_trunc=hour"
    
    # Afegim User-Agent perquè el servidor del ministeri no bloquegi la connexió de Streamlit
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        resposta = requests.get(url, headers=headers, timeout=10)
        if resposta.status_code == 200:
            dades_json = resposta.json()
            valors = dades_json['included']['attributes']['values']
            
            llista_hores = []
            for i, info in enumerate(valors):
                preu_base_kwh = info['value'] / 1000  # Convertim de MWh a kWh
                llista_hores.append({
                    "Hora": f"{i:02d}:00",
                    "Preu Base (€/kWh)": preu_base_kwh,
                    "Num_Hora": i
                })
            return pd.DataFrame(llista_hores)
        else:
            st.error(f"Error de l'API: Codi d'estat {resposta.status_code}")
            return None
    except Exception as e:
        st.error(f"Error de connexió: {e}")
        return None

# Executar la funció
df = carregar_api_ree()

# 3. Processar i mostrar gràfic si l'API respon
if df is not None:
    # Sumem el marge independent de l'usuari i l'IVA (21%) al preu base traat de l'API
    df["Preu Final (€/kWh)"] = (df["Preu Base (€/kWh)"] + marge) * 1.21
    
    # Determinar hora actual per a la mètrica
    hora_ara = datetime.datetime.now().hour
    if hora_ara >= len(df): hora_ara = len(df) - 1
    preu_ara = df.iloc[hora_ara]["Preu Final (€/kWh)"]
    
    st.metric(label=f"Preu Factura ARA ({hora_ara}:00h)", value=f"{preu_ara:.4f} €/kWh")
    st.markdown("---")
    
    # Gràfic de barres
    fig = px.bar(df, x="Hora", y="Preu Final (€/kWh)", title="Cost total per hores rebut de l'API (Amb IVA)")
    fig.update_layout(yaxis_tickformat=".3f")
    st.plotly_chart(fig, use_container_width=True)
    
    # Taula de comprovació de dades pures
    if st.checkbox("Veure taula de dades pures de l'API"):
        st.dataframe(df)
