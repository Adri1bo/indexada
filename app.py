import streamlit as st
import pandas as pd
import datetime
from fpdf import FPDF
import io

# Configuració de la pàgina
st.set_page_config(page_title="Mini ERP de Facturació", layout="wide", page_icon="💼")
st.title("💼 Mini ERP de Facturació i Gestió")
st.write("Gestiona clients, productes i genera factures en PDF a l'acte.")

# ---------------------------------------------------------
# 1. BASE DE DADES EN MEMÒRIA (Simulada amb Streamlit Session State)
# ---------------------------------------------------------
if 'clients' not in st.session_state:
    st.session_state.clients = [
        {"Nom": "Empresa Alfa SL", "NIF": "B12345678", "Direcció": "Carrer Major 15, Barcelona"},
        {"Nom": "Joan Garcia (Autònom)", "NIF": "45678901X", "Direcció": "Av. Diagonal 400, Girona"}
    ]

if 'productes' not in st.session_state:
    st.session_state.productes = [
        {"Concepte": "Consultoria Tecnològica (Hora)", "Preu": 60.0},
        {"Concepte": "Desenvolupament Web Compleu", "Preu": 1500.0},
        {"Concepte": "Manteniment Mensual Servidors", "Preu": 150.0}
    ]

# ---------------------------------------------------------
# INTERFÍCIE PER PESTANYES
# ---------------------------------------------------------
pestanya_factura, pestanya_clients, pestanya_productes = st.tabs([
    "📄 Crear Factura", "👥 Gestió de Clients", "📦 Catàleg de Productes"
])

# ---------------------------------------------------------
# PESTANYA 2: GESTIÓ DE CLIENTS
# ---------------------------------------------------------
with pestanya_clients:
    st.subheader("👥 Afegir Nou Client")
    with st.form("form_client", clear_on_submit=True):
        c_nom = st.text_input("Nom de l'empresa o client")
        c_nif = st.text_input("NIF / CIF")
        c_dir = st.text_input("Direcció Fiscal")
        if st.form_submit_button("Guardar Client") and c_nom and c_nif:
            st.session_state.clients.append({"Nom": c_nom, "NIF": c_nif, "Direcció": c_dir})
            st.success(f"Client '{c_nom}' afegit correctament!")
    
    st.write("### Llista de Clients actuals")
    st.dataframe(pd.DataFrame(st.session_state.clients), use_container_width=True)

# ---------------------------------------------------------
# PESTANYA 3: CATÀLEG DE PRODUCTES
# ---------------------------------------------------------
with pestanya_productes:
    st.subheader("📦 Afegir Nou Producte o Servei")
    with st.form("form_producte", clear_on_submit=True):
        p_concepte = st.text_input("Concepte / Descripció")
        p_preu = st.number_input("Preu Unitari (€)", min_value=0.0, step=10.0)
        if st.form_submit_button("Guardar Producte") and p_concepte:
            st.session_state.productes.append({"Concepte": p_concepte, "Preu": p_preu})
            st.success(f"Producte '{p_concepte}' afegit al catàleg!")
            
    st.write("### Catàleg de Productes actual")
    st.dataframe(pd.DataFrame(st.session_state.productes), use_container_width=True)

# ---------------------------------------------------------
# PESTANYA 1: CREAR FACTURA
# ---------------------------------------------------------
with pestanya_factura:
    col_esquerra, col_dreta = st.columns([1, 1])
    
    with col_esquerra:
        st.subheader("🛠️ Dades de la Factura")
        
        # Dades de l'emissor (Tu)
        st.markdown("**Les teves dades (Emissor):**")
        meu_nom = st.text_input("El teu nom o empresa", "El Teu Nom / Empresa SL")
        meu_nif = st.text_input("El teu NIF", "A99999999")
        
        # Selecció de client i dates
        df_clients = pd.DataFrame(st.session_state.clients)
        client_seleccionat = st.selectbox("Selecciona el Client", df_clients["Nom"].tolist())
        dades_client = df_clients[df_clients["Nom"] == client_seleccionat].iloc[0]
        
        num_factura = st.text_input("Número de Factura", f"F-{datetime.datetime.now().year}-001")
        data_factura = st.date_input("Data d'emissió", datetime.date.today())
        
        st.markdown("---")
        st.markdown("**Línies de la factura:**")
        
        # Selecció de productes per a la factura
        df_prod = pd.DataFrame(st.session_state.productes)
        prod_seleccionat = st.selectbox("Selecciona un concepte del catàleg", df_prod["Concepte"].tolist())
        preu_suggerit = df_prod[df_prod["Concepte"] == prod_seleccionat].iloc[0]["Preu"]
        
        quantitat = st.number_input("Quantitat", min_value=1, value=1)
        preu_final = st.number_input("Preu (€)", value=float(preu_suggerit), step=5.0)
        
        # Impostos
        iva_tipus = st.selectbox("IVA (%)", [21, 10, 4, 0], index=0)
        irpf_tipus = st.selectbox("IRPF (%) - Retenció autònoms", [0, 7, 15], index=0)

    with col_dreta:
        st.subheader("👀 Vista prèvia i Càlculs")
        
        # Càlculs econòmics
        base_imposable = quantitat * preu_final
        import_iva = base_imposable * (iva_tipus / 100)
        import_irpf = base_imposable * (irpf_tipus / 100)
        total_factura = base_imposable + import_iva - import_irpf
        
        # Mostrar el resum de la factura de forma visual
        st.info(f"""
        **CLIENT:** {client_seleccionat} ({dades_client['NIF']})  
        **CONCEPTE:** {prod_seleccionat} (x{quantitat})
        """)
        
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Base Imposable", f"{base_imposable:,.2f} €")
            st.metric(f"IVA ({iva_tipus}%)", f"{import_iva:,.2f} €")
        with c2:
            st.metric(f"IRPF (-{irpf_tipus}%)", f"{import_irpf:,.2f} €")
            st.metric("TOTAL A COBRAR", f"{total_factura:,.2f} €")
            
        # ---------------------------------------------------------
        # GENERACIÓ DEL PDF AMB FPDF2
        # ---------------------------------------------------------
        def generar_pdf():
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            # Estils de lletra estàndard (Helvetica)
            pdf.set_font("Helvetica", "B", 20)
            pdf.cell(0, 10, "FACTURE", ln=True, align="R")
            pdf.ln(5)
            
            # Bloc Emissor i Receptor en dues columnes simulades
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(95, 6, "EMISSOR:", ln=False)
            pdf.cell(95, 6, "CLIENT / RECEPTOR:", ln=True)
            
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(95, 5, meu_nom, ln=False)
            pdf.cell(95, 5, str(dades_client['Nom']), ln=True)
            
            pdf.cell(95, 5, f"NIF: {meu_nif}", ln=False)
            pdf.cell(95, 5, f"NIF: {str(dades_client['NIF'])}", ln=True)
            
            pdf.cell(95, 5, "", ln=False)
            pdf.cell(95, 5, f"Dir: {str(dades_client['Direcció'])}", ln=True)
            pdf.ln(10)
            
            # Metadades Factura
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(50, 6, f"Num. Factura: {num_factura}", ln=True)
            pdf.cell(50, 6, f"Data: {data_factura.strftime('%d/%m/%Y')}", ln=True)
            pdf.ln(10)
            
            # Taula de Conceptes
            pdf.set_fill_color(230, 230, 230)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(100, 8, " Concepte", border=1, fill=True)
            pdf.cell(25, 8, "Unitats", border=1, fill=True, align="C")
            pdf.cell(30, 8, "Preu Unit.", border=1, fill=True, align="R")
            pdf.cell(35, 8, "Total", border=1, fill=True, align="R")
            pdf.ln()
            
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(100, 8, f" {prod_seleccionat}", border=1)
            pdf.cell(25, 8, str(quantitat), border=1, align="C")
            pdf.cell(30, 8, f"{preu_final:,.2f} EUR", border=1, align="R")
            pdf.cell(35, 8, f"{base_imposable:,.2f} EUR", border=1, align="R")
            pdf.ln(12)
            
            # Totals
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(130, 6, "", ln=False)
            pdf.cell(25, 6, "Base Imposable:", ln=False)
            pdf.cell(35, 6, f"{base_imposable:,.2f} EUR", ln=True, align="R")
            
            pdf.cell(130, 6, "", ln=False)
            pdf.cell(25, 6, f"IVA ({iva_tipus}%):", ln=False)
            pdf.cell(35, 6, f"{import_iva:,.2f} EUR", ln=True, align="R")
            
            if irpf_tipus > 0:
                pdf.cell(130, 6, "", ln=False)
                pdf.cell(25, 6, f"IRPF (-{irpf_tipus}%):", ln=False)
                pdf.cell(35, 6, f"-{import_irpf:,.2f} EUR", ln=True, align="R")
            
            pdf.ln(5)
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(130, 8, "", ln=False)
            pdf.cell(25, 8, "TOTAL:", ln=False)
            pdf.cell(35, 8, f"{total_factura:,.2f} EUR", border="T", ln=True, align="R")
            
            # Retornar el PDF en bytes
            return pdf.output()

        # Botó de descàrrega del PDF
        st.markdown("### 🖨️ Accions")
        try:
            pdf_bytes = generar_pdf()
            st.download_button(
                label="Descargar Factura en PDF",
                data=bytes(pdf_bytes),
                file_name=f"Factura_{num_factura}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Error generant el PDF: {e}")
