
import streamlit as st
import pandas as pd
import requests
import datetime
import plotly.express as px

# Configuració inicial de l'aplicació web
st.set_page_config(page_title="Visor de Tarifa Indexada Exacta", layout="wide", page_icon="⚡")
st.title("⚡ Visor Oficial de Tarifes Indexades i Regulades")
st.write("Simulador horari que calcula el cost real de la teva energia sumant el Pool de mercat, costos comercials, peatges i impostos.")

# ---------------------------------------------------------
# BARRA LATERAL - ENTRADA INDEPENDENT DE TOTS ELS IMPORTS
# ---------------------------------------------------------
st.sidebar.header("🔧 1. Marge i Despeses de Gestió")

marge_comercializadora = st.sidebar.number_input(
    "Marge Comercial (€/kWh)", 
    min_value=0.000, max_value=0.100, value=0.005, step=0.001, format="%.3f"
)

cost_operatiu_financer = st.sidebar.number_input(
    "Fons d'Ocupació / Bono Social (€/kWh)", 
    min_value=0.0000, max_value=0.0200, value=0.0023, step=0.0005, format="%.4f"
)

st.sidebar.header("🛣️ 2. Peatges i Càrrecs Regulats (2.0TD)")
st.sidebar.caption("Components del terme d'energia activa per hores segons els calendaris oficials:")

peatge_punta = st.sidebar.number_input("Cost hora PUNTA (10h-14h, 18h-22h) (€/kWh)", value=0.046, step=0.002, format="%.3f")
peatge_plana = st.sidebar.number_input("Cost hora PLANA (08h-10h, 14h-18h, 22h-24h) (€/kWh)", value=0.015, step=0.001, format="%.3f")
peatge_vall = st.sidebar.number_input("Cost hora VALL (00h-08h, Caps de setmana) (€/kWh)", value=0.001, step=0.0005, format="%.4f")

st.sidebar.header("🏛️ 3. Marc Fiscal i Impostos")
impost_electric = st.sidebar.number_input("Impost Especial sobre l'Electricitat (IEE) (%)", value=5.11, step=0.01) / 100
iva = st.sidebar.selectbox("IVA de la Factura (%)", [21.0, 10.0, 5.0], index=0) / 100

# ---------------------------------------------------------
# DESCARGA DE DADES EN TEMPS REAL (API Red Eléctrica)
# ---------------------------------------------------------
@st.cache_data(ttl=1800)
def obtenir_dades_mercats_ree():
    avui = datetime.date.today().strftime("%Y-%m-%d")
    # Indicador 1013: Preu majorista de l'electricitat a Espanya (Mercat diari OMIE)
    url = f"https://ree.es{avui}T00:00&end_date={avui}T23:59&time_trunc=hour"
    try:
        resposta = requests.get(url, timeout=15)
        if resposta.status_code == 200:
            dades_json = resposta.json()
            valors = dades_json['included']['attributes']['values']
            llista_hores = []
            
            for i, info in enumerate(valors):
                preu_base_kwh = info['value'] / 1000  # Convertir d'€/MWh a €/kWh
                hora_text = f"{i:02d}:00 - {i+1:02d}:00"
                
                # Assignació estricta de franges horàries peninsulars (Dilluns-Divendres)
                # Caps de setmana complets haurien de ser VALL (es pot matisar amb el dia de la setmana)
                dia_setmana = datetime.date.today().weekday()
                
                if dia_setmana >= 5:  # Dissabte i Diumenge
                    franja = "VALL (Barata)"
                    peatge_aplicat = peatge_vall
                else:
                    if i in:
                        franja = "PUNTA (Cara)"
                        peatge_aplicat = peatge_punta
                    elif i in:
                        franja = "PLANA (Mitjana)"
                        peatge_aplicat = peatge_plana
                    else:
                        franja = "VALL (Barata)"
                        peatge_aplicat = peatge_vall
                    
                llista_hores.append({
                    "Hora": hora_text,
                    "Preu Pool OMIE (€/kWh)": preu_base_kwh,
                    "Franja": franja,
                    "Peatge Regulat (€/kWh)": peatge_aplicat,
                    "Num_Hora": i
                })
            return pd.DataFrame(llista_hores)
        return None
    except Exception:
        return None

df_preus = obtenir_dades_mercats_ree()

if df_preus is not None and not df_preus.empty:
    
    # ---------------------------------------------------------
    # OPERACIONS MATEMÀTIQUES DE SUMA D'IMPORTS MULTIPLES
    # ---------------------------------------------------------
    # Pas 1: Suma dels components bases de l'energia i peatges
    df_preus["Base Cost Energia (€/kWh)"] = (
        df_preus["Preu Pool OMIE (€/kWh)"] + 
        marge_comercializadora + 
        df_preus["Peatge Regulat (€/kWh)"] + 
        cost_operatiu_financer
    )
    
    # Pas 2: Aplicació de l'Impost Elèctric (IEE)
    df_preus["Amb Impost Elèctric (€/kWh)"] = df_preus["Base Cost Energia (€/kWh)"] * (1 + impost_electric)
    
    # Pas 3: Càlcul del cost final sumant l'IVA
    df_preus["El teu Preu Final (€/kWh)"] = df_preus["Amb Impost Elèctric (€/kWh)"] * (1 + iva)
    
    # Conversió a cèntims d'euro per visualització estàndard comercial (cts/kWh)
    df_preus["Preu Final (cts/kWh)"] = df_preus["El teu Preu Final (€/kWh)"] * 100

    # ---------------------------------------------------------
    # EXPOSICIÓ DE DADES ACTUALS (KPIs)
    # ---------------------------------------------------------
    hora_actual = datetime.datetime.now().hour
    if hora_actual >= len(df_preus):
        hora_actual = len(df_preus) - 1
        
    fila_actual = df_preus.iloc[hora_actual]
    preu_ara = fila_actual["El teu Preu Final (€/kWh)"]
    franja_ara = fila_actual["Franja"]
    
    preu_minim = df_preus["El teu Preu Final (€/kWh)"].min()
    hora_minima = df_preus.iloc[df_preus["El teu Preu Final (€/kWh)"].idxmin()]["Hora"]
    
    preu_maxim = df_preus["El teu Preu Final (€/kWh)"].max()
    hora_maxima = df_preus.iloc[df_preus["El teu Preu Final (€/kWh)"].idxmax()]["Hora"]

    st.subheader(f"📌 Estat del Mercat Indexat en Temps Real — Franja actual: {franja_ara}")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label=f"Preu Factura ARA ({hora_actual}:00h)", 
            value=f"{preu_ara:.4f} €/kWh", 
            delta=f"{(preu_ara * 100):.2f} cts/kWh"
        )
    with col2:
        st.metric(label=f"🟢 Mínim d'Avui ({hora_minima})", value=f"{preu_minim:.4f} €/kWh")
    with col3:
        st.metric(label=f"🔴 Màxim d'Avui ({hora_maxima})", value=f"{preu_maxim:.4f} €/kWh")
        
    st.markdown("---")

    # ---------------------------------------------------------
    # VISUALITZACIÓ GRÀFICA INTERACTIVA
    # ---------------------------------------------------------
    st.subheader("📈 Gràfic Horari Desglossat (Cost final per a l'usuari)")
    
    fig = px.bar(
        df_preus, x="Hora", y="El teu Preu Final (€/kWh)", color="Franja",
        color_discrete_map={"VALL (Barata)": "#2ca02c", "PLANA (Mitjana)": "#ff7f0e", "PUNTA (Cara)": "#d62728"},
        labels={"El teu Preu Final (€/kWh)": "Preu Factura Final (€/kWh)"},
        title="Evolució del preu final de l'energia al llarg del dia"
    )
    fig.update_layout(hovermode="x unified", yaxis_tickformat=".4f")
    st.plotly_chart(fig, use_container_width=True)

    # ---------------------------------------------------------
    # TAULA DETALLADA
    # ---------------------------------------------------------
    if st.checkbox("🔍 Veure la auditoria de costos i desglossament cèntim a cèntim"):
        st.write("Graella detallada d'imports abans i després de la repercussió fiscal:")
        st.dataframe(
            df_preus[["Hora", "Franja", "Preu Pool OMIE (€/kWh)", "Peatge Regulat (€/kWh)", "Base Cost Energia (€/kWh)", "El teu Preu Final (€/kWh)", "Preu Final (cts/kWh)"]],
            use_container_width=True
        )
else:
    st.error("❌ No s'han pogut extraure les dades de Red Eléctrica Española. S'estan actualitzant els indicadors del ministeri. Torna-ho a provar en un moment.")
