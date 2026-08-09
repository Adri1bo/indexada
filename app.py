import streamlit as st
import pandas as pd
import requests
import datetime
import plotly.express as px

# Configuració de la pàgina web
st.set_page_config(page_title="Visor de Tarifa Elèctrica Indexada", layout="wide", page_icon="⚡")
st.title("⚡ Visor Horari per a Tarifes Indexades de la Llum")
st.write("Consulta el preu real de l'energia adaptat al teu contracte del mercat lliure utilitzant les dades oficials de Red Eléctrica.")

# ---------------------------------------------------------
# BARRA LATERAL - ENTRADA DEL MARGE DE LA COMERCIALITZADORA
# ---------------------------------------------------------
st.sidebar.header("🔧 Paràmetres del teu Contracte")

marge_comercializadora = st.sidebar.number_input(
    "Marge de la teva comercialitzadora (€/kWh)", 
    min_value=0.000, 
    max_value=0.100, 
    value=0.010, 
    step=0.001,
    format="%.3f"
)
st.sidebar.info("💡 Suma el marge (ex: 0.010 €) al cost oficial OMIE del mercat diari.")

# ---------------------------------------------------------
# DESCÀRREGA DE DADES EN TEMPS REAL DES DE RED ELÉCTRICA (API Oficial)
# ---------------------------------------------------------
@st.cache_data(ttl=1800)  # Guarda en memòria 30 minuts
def obtenir_preus_oficials_ree():
    avui = datetime.date.today().strftime("%Y-%m-%d")
    # Indicador 1013: Preu mitjà horari del mercat diari (base per a les indexades)
    url = f"https://ree.es{avui}T00:00&end_date={avui}T23:59&time_trunc=hour"
    
    try:
        resposta = requests.get(url, timeout=15)
        if resposta.status_code == 200:
            dades_json = resposta.json()
            # Busquem la sèrie de preus de mercat dins l'estructura de REE
            valors = dades_json['included'][0]['attributes']['values']
            
            llista_hores = []
            for i, info in enumerate(valors):
                # El preu de la REE ve en €/MWh, ho dividim per 1000 per passar a €/kWh
                preu_base_kwh = info['value'] / 1000
                hora_text = f"{i:02d}:00 - {i+1:02d}:00"
                
                # Calculem la franja horària estàndard (Punta, Plana, Vall) per a la gràfica
                if i in [10, 11, 12, 13, 18, 19, 20, 21]:
                    franja = "PEAK (Cara)"
                elif i in [8, 9, 14, 15, 16, 17, 22, 23]:
                    franja = "FLAT (Mitjana)"
                else:
                    franja = "VALLEY (Barata)"
                    
                llista_hores.append({
                    "Hora": hora_text,
                    "Preu Base Mercat (€/kWh)": preu_base_kwh,
                    "Franja": franja,
                    "Num_Hora": i
                })
            return pd.DataFrame(llista_hores)
        return None
    except Exception:
        return None

# Carreguem les dades oficials
df_preus = obtenir_preus_oficials_ree()

if df_preus is not None and not df_preus.empty:
    # ---------------------------------------------------------
    # CÀLCUL DEL PREU FINAL (Preu Mercat + Marge Usuari)
    # ---------------------------------------------------------
    df_preus["El teu Preu Final (€/kWh)"] = df_preus["Preu Base Mercat (€/kWh)"] + marge_comercializadora
    df_preus["Preu Final (cèntims/kWh)"] = df_preus["El teu Preu Final (€/kWh)"] * 100

    # Detectar l'hora actual per donar el resultat en viu
    hora_actual = datetime.datetime.now().hour
    # Ens assegurem de no demanar una hora fora de rang si l'API no s'ha actualitzat del tot
    if hora_actual >= len(df_preus):
        hora_actual = len(df_preus) - 1
        
    fila_actual = df_preus.iloc[hora_actual]
    preu_ara = fila_actual["El teu Preu Final (€/kWh)"]
    
    # Càlculs de màxims i mínims de la jornada
    idx_min = df_preus["El teu Preu Final (€/kWh)"].idxmin()
    idx_max = df_preus["El teu Preu Final (€/kWh)"].idxmax()
    
    preu_minim = df_preus.loc[idx_min, "El teu Preu Final (€/kWh)"]
    hora_minima = df_preus.loc[idx_min, "Hora"]
    
    preu_maxim = df_preus.loc[idx_max, "El teu Preu Final (€/kWh)"]
    hora_maxima = df_preus.loc[idx_max, "Hora"]

    # ---------------------------------------------------------
    # METRIQUES PRINCIPALS (KPIs)
    # ---------------------------------------------------------
    st.subheader("📌 Estat actual del mercat oficial (OMIE)")
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
    st.write("Passa el ratolí pel gràfic per veure la teva tarifa amb el marge sumat.")
    
    fig = px.bar(
        df_preus, 
        x="Hora", 
        y="El teu Preu Final (€/kWh)", 
        color="Franja",
        color_discrete_map={"VALLEY (Barata)": "#2ca02c", "FLAT (Mitjana)": "#ff7f0e", "PEAK (Cara)": "#d62728"},
        labels={"El teu Preu Final (€/kWh)": "Preu total amb marge (€/kWh)"},
        title="Cost del kWh al llarg d'avui"
    )
    
    fig.update_layout(hovermode="x unified", yaxis_tickformat=".4f")
    st.plotly_chart(fig, use_container_width=True)

    # ---------------------------------------------------------
    # TAULA DETALLADA
    # ---------------------------------------------------------
    if st.checkbox("🔍 Veure la taula completa de dades en cèntims de deute"):
        st.dataframe(
            df_preus[["Hora", "Preu Base Mercat (€/kWh)", "El teu Preu Final (€/kWh)", "Preu Final (cèntims/kWh)"]],
            use_container_width=True
        )
else:
    st.error("❌ Red Eléctrica no està enviant dades en aquest instant. Això pot ser degut a un manteniment del ministeri o a que encara no s'han publicat les hores d'avui. Torna-ho a provar en un moment.")
