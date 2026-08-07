import streamlit as st
import requests
import time
import random

# Configuració estètica de la pàgina
st.set_page_config(page_title="Creador d'Avatars amb IA", layout="wide", page_icon="🧙‍♂️")

st.title("🔮 Creador de Personatges i Històries amb IA")
st.write("Configura el teu personatge i deixa que diferents models d'Intel·ligència Artificial en generin la descripció i la seva imatge en temps real.")

# ---------------------------------------------------------
# BARRA LATERAL: CONFIGURACIÓ DEL PERSONATGE
# ---------------------------------------------------------
st.sidebar.header("🛠️ Defineix el teu Heroi/Heroïna")

nom = st.sidebar.text_input("Nom del personatge", "Aelion el Savi")
arquetip = st.sidebar.selectbox(
    "Arquetip / Classe",
    ["Mag de l'espai", "Ciberpunk Rebel", "Guerrer Medieval", "Detectiu Noir", "Explorador de l'Atlàntida"]
)

personalitat = st.sidebar.select_slider(
    "Personalitat",
    options=["Molt Dolent", "Impulsiu", "Neutral", "Savi", "Heroic"],
    value="Savi"
)

element_magic = st.sidebar.selectbox("Element o Habilitat clau", ["Foc / Plasma", "Temps", "Ombres", "Tecnologia", "Naturalesa"])

st.sidebar.markdown("---")
generar = st.sidebar.button("✨ GENERAR AMB IA", use_container_width=True)

# ---------------------------------------------------------
# LÒGICA DE GENERACIÓ SENSE CLAUS (Models de Codi Obert Gratuïts)
# ---------------------------------------------------------
if generar:
    st.toast("Invocant les IA...", icon="⚡")
    
    # Creem un prompt (instruccions) de text i un per a la imatge
    descripcio_prompt = f"Crea una biografia breu i èpica en català per a un personatge anomenat {nom}. És un {arquetip} amb una personalitat {personalitat} i el seu poder és {element_magic}. Fes-ho en un sol paràgraf impactant de 4 línies."
    imatge_prompt = f"Detailed portrait of a {arquetip}, professional digital art, fantasy concept art, cinematic lighting, masterwork, looking at camera, elemental power of {element_magic} visible"

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📜 Història d'Origen (IA de Text)")
        with st.spinner("La IA està escrivint la història..."):
            try:
                # Cridem a una API de text de codi obert (Llama-3 via l'API gratuïta de DuckDuckGo/Pollinations)
                url_text = f"https://pollinations.ai{requests.utils.quote(descripcio_prompt)}"
                resposta_text = requests.get(url_text)
                
                if resposta_text.status_code == 200:
                    historia_català = resposta_text.text
                    # Un petit efecte d'escriptura a màquina per fer-ho xulo
                    placeholder = st.empty()
                    text_efecte = ""
                    for caracter in historia_català:
                        text_efecte += caracter
                        placeholder.markdown(f"*{text_efecte}*")
                        time.sleep(0.01)
                else:
                    st.error("La IA de text està saturada. Aquí tens una alternativa digital:")
                    st.write(f"En {nom} és un llegendari {arquetip} conegut a tot l'univers pel seu domini sobre el {element_magic}.")
            except Exception:
                st.write(f"En {nom} camina solitari controlant el poder de {element_magic} amb el seu tarannà {personalitat}.")

        # Generació d'Estadístiques aleatòries estil RPG simulades pel sistema per donar color
        st.markdown("### 📊 Atributs del Personatge")
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Atac / Poder", f"{random.randint(70, 99)} pts")
        with c2: st.metric("Defensa / Astúcia", f"{random.randint(50, 89)} pts")
        with c3: st.metric("Sincronització", f"{random.randint(80, 100)}%")

    with col2:
        st.subheader("🖼️ Retrat Generat (IA d'Imatge - Flux)")
        with st.spinner("La IA està dibuixant el personatge de zero..."):
            # Cridem al model de generació d'imatges FLUX (el més potent actualment en codi obert)
            url_imatge = f"https://pollinations.ai{requests.utils.quote(imatge_prompt)}?width=512&height=512&seed={random.randint(1,99999)}"
            
            # Mostrem la imatge directament des de la URL generada en temps real
            st.image(url_imatge, caption=f"Retrat oficial de {nom}", use_container_width=True)
            
            # Botó per descarregar el teu avatar de fusta
            st.caption("Aquesta imatge s'ha creat completament de zero en aquest moment mitjançant xarxes neuronals.")

else:
    # Pantalla de benvinguda quan l'app s'obre per primera vegada
    st.info("👈 Tria com vols que sigui el teu personatge a la barra lateral i prem el botó **GENERAR AMB IA** per veure la màgia.")
    
    # Afegim una galeria d'exemple de fons perquè la pantalla no quedi buida
    st.markdown("### 🗂️ Exemples del que pot fer aquesta IA:")
    cx1, cx2, cx3 = st.columns(3)
    with cx1:
        st.image("https://pollinations.aicyberpunk%20rebel%20neon%20portrait?width=300&height=300&seed=42", caption="Estil Ciberpunk")
    with cx2:
        st.image("https://pollinations.aimedieval%20wizard%20fire%20magic?width=300&height=300&seed=12", caption="Estil Mag Medieval")
    with cx3:
        st.image("https://pollinations.aispace%20astronaut%20explorer?width=300&height=300&seed=99", caption="Estil Explorador de l'Espai")

