import streamlit as st
import pandas as pd
import requests
import datetime
import plotly.express as px

# Configuració de la pàgina web
st.set_page_config(page_title="Visor de Tarifa Elèctrica Indexada", layout="wide", page_icon="⚡")
st.title("⚡ Visor Horari per a Tarifes Indexades de la Llum")
st.write("Consulta el preu real de l'energia hora a hora adaptat exactament al teu contracte del mercat lliure.")

# ---------------------------------------------------------
# BARRA LATERAL - ENTRADA DEL MARGE DE LA COMERCIALITZADORA
# ---------------------------------------------------------
st.sidebar.header("🔧 Paràmetres del teu Contracte")

# El marge comercial se sol cobrar per kWh consumit (habitualment entre 0.003 i 0.02 €/kWh)
marge_comercializadora = st.sidebar.number_input(
    "Marge de la teva comercialitzadora (€/kWh)", 
    min_value=0.000, 
    max_value=0.100, 
    value=0.010, 
    step=0.001,
    format="%.3f"
)
st.sidebar.info("💡 Mira la teva última factura de la llum. El marge sol aparèixer com a 'gastos de gestión', 'pass-through' o 'margen' sumat al cost de l'energia.")

# ---------------------------------------------------------
# DESCARGA DE DADES EN TEMPS REAL (API Pública sense Claus)
# ---------------------------------------------------------
@st.cache_data(ttl=3600)  # Desa en memòria 1 hora per anar ràpid
def obtenir_preus_llum():
    # Utilitzem l'API oberta d'api.preciodelaluz.org que no requereix registre ni tokens
    url = "https://preciodelaluz.org"
    try:
        resposta = requests.get(url, timeout=10)
        if resposta.status_code == 200:
            dades_json = resposta.json()
            llista_hores = []
            for clau, info in dades_json.items():
                # L'API torna el preu en €/MWh o MWh, ho passem a €/kWh dividint per 1000
                preu_base_kwh = info['price'] / 1000
                hora_text = info['hour']
                llista_hores.append({
                    "Hora": f"{hora_text}",
                    "Preu Base Mercat (€/kWh)": preu_base_kwh,
                    "Franja": info['zone']
                })
            # El JSON no ve ordenat per hores, ho ordenem nosaltres
            df = pd.DataFrame(llista_hores)
            df['Hora_Num'] = df['Hora'].apply(lambda x: int(x.split('-')[0]))
            df = df.sort_values(by='Hora_Num').drop(columns=['Hora_Num']).reset_index(drop=True)
            return df
        return None
    except Exception:
        return None

# Cridem la funció per carregar la graella de dades
df_preus = obtenir_preus_llum()

if df_preus is not None:
    # ---------------------------------------------------------
    # CÀLCUL DEL PREU FINAL (Preu Mercat + Marge Usuari)
    # ---------------------------------------------------------
    df_preus["El teu Preu Final (€/kWh)"] = df_preus["Preu Base Mercat (€/kWh)"] + marge_comercializadora
    
    # Afegim una columna per facilitar la lectura visual a la taula
    df_preus["Preu Final (cèntims/kWh)"] = df_preus["El teu Preu Final (€/kWh)"] * 100

    # Detectar l'hora actual per donar una resposta ràpida
    hora_actual = datetime.datetime.now().hour
    fila_actual = df_preus.iloc[hora_actual]
    preu_ara = fila_actual["El teu Preu Final (€/kWh)"]
    franja_ara = fila_actual["Franja"]
    
    # Càlculs de referència del dia
    preu_minim = df_preus["El teu Preu Final (€/kWh)"].min()
    hora_minima = df_preus.iloc[df_preus["El teu Preu Final (€/kWh)"].idxmin()]["Hora"]
    
    preu_maxim = df_preus["El teu Preu Final (€/kWh)"].max()
    hora_maxima = df_preus.iloc[df_preus["El teu Preu Final (€/kWh)"].idxmax()]["Hora"]

    # ---------------------------------------------------------
    # METRIQUES PRINCIPALS (KPIs)
    # ---------------------------------------------------------
    st.subheader("📌 Estat actual del mercat")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label=f"Preu ARA mateix ({hora_actual}:00h)", 
            value=f"{preu_ara:.4f} €/kWh",
            delta=f"{(preu_ara * 100):.2f} cts/kWh"
        )
    with col2:
        st.metric(
            label=f"🟢 Hora més BARATA ({hora_minima})", 
            value=f"{preu_minim:.4f} €/kWh"
        )
    with col3:
        st.metric(
            label=f"🔴 Hora més CARA ({hora_maxima})", 
            value=f"{preu_maxim:.4f} €/kWh"
        )
        
    st.markdown("---")

    # ---------------------------------------------------------
    # GRÀFIC INTERACTIU DE FRANGES HORÀRIES
    # ---------------------------------------------------------
    st.subheader("📈 Corba de Preus per a la teva Tarifa Indexada")
    st.write("Fes passat el ratolí pel gràfic per veure el preu exacte de cada hora (inclou el marge configurat).")
    
    # Crear gràfic de barres de color depenent de la franja horària
    fig = px.bar(
        df_preus, 
        x="Hora", 
        y="El teu Preu Final (€/kWh)", 
        color="Franja",
        color_discrete_map={"VALLEY": "#2ca02c", "FLAT": "#ff7f0e", "PEAK": "#d62728"},
        labels={"El teu Preu Final (€/kWh)": "Preu total amb marge (€/kWh)"},
        title="Preu del kWh al llarg de les 24 hores d'avui"
    )
    
    fig.update_layout(hovermode="x unified", yaxis_tickformat=".4f")
    st.plotly_chart(fig, use_container_width=True)

    # ---------------------------------------------------------
    # TAULA DETALLADA
    # ---------------------------------------------------------
    if st.checkbox("🔍 Veure la taula de dades completa (amb decimals de cèntim)"):
        st.dataframe(
            df_preus[["Hora", "Preu Base Mercat (€/kWh)", "El teu Preu Final (€/kWh)", "Preu Final (cèntims/kWh)"]],
            use_container_width=True
        )
else:
    st.error("❌ No s'han pogut carregar els preus de l'energia en aquest moment. Verifica la teva connexió a internet o torna-ho a provar més tard.")
