import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, time

st.set_page_config(page_title="Sistema-Citas", layout="centered")
st.title("💅 Agenda de Citas - [Nombre del Negocio]")

# ----------------------
# BASE (simulación BD local -> luego Google Sheets)
# ----------------------

if "horarios" not in st.session_state:
    st.session_state.horarios = {}

# ----------------------
# CONEXIÓN GOOGLE SHEETS
# ----------------------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

import json
from google.oauth2.service_account import Credentials

creds_dict = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

sheet = client.open("Agenda Beauty").sheet1

# ----------------------
# CONFIGURAR HORARIOS
# ----------------------
st.subheader("🕒 Configurar horarios")

admin_mode = st.checkbox("Modo administrador")

if admin_mode:
    with st.expander("Configurar horarios por día"):
        fecha_conf = st.date_input("Fecha", min_value=datetime.today(), key="fecha_config")
        horas_base = [time(h, 0) for h in range(8, 20)]
        horas = st.multiselect(
            "Seleccionar horas",
            horas_base,
            key=f"horas_{fecha_conf}"
)

        if st.button("Guardar horarios"):
            st.session_state.horarios[fecha_conf.strftime("%Y-%m-%d")] = [h.strftime("%H:%M") for h in horas]
            st.success("Horarios guardados")
            #st.write("DEBUG horarios:", st.session_state.horarios)

# ----------------------
# AGENDAR CITA
# ----------------------
st.subheader("📆 Agendar cita")

fecha = st.date_input("Fecha", min_value=datetime.today(), key="fecha_cita")

with st.form("form_cita", clear_on_submit=True):
    nombre = st.text_input("Nombre usuario")
    telefono = st.text_input("Teléfono")

    if telefono:
        if not telefono.isdigit():
            st.warning("El teléfono solo debe contener números")

    servicio = st.selectbox("Servicio", ["Manicure", "Pedicure", "Manos y Pies", "Otros"])
    profesional = st.text_input("Profesional (opcional)")
    fecha_str = fecha.strftime("%Y-%m-%d")
    horarios = st.session_state.horarios.get(fecha_str, [])
    data = sheet.get_all_records()
    if data:
        df_temp = pd.DataFrame(data)
        ocupados = df_temp[df_temp["Fecha"] == fecha_str]["Hora"].tolist()
    else:
        ocupados = []
    libres = [h for h in horarios if h not in ocupados]

    if libres:
        hora = st.selectbox("Hora", libres)
    else:
        st.warning("Sin horarios disponibles para la fecha elegida.")
        hora = None

    observaciones = st.text_area("Observaciones (mínimo 5 caracteres)")

    st.caption("Complete los campos y presione el botón Agendar")

    guardar = st.form_submit_button("Agendar", key="btn_agendar")

    if guardar:
        if not nombre or not telefono:
            st.error("Nombre y teléfono obligatorios")
        elif not telefono.isdigit():
            st.error("El teléfono solo debe contener números")
        elif len(observaciones) < 5:
            st.error("Observaciones mínimo 5 caracteres")
        elif not hora:
            st.error("No hay horarios disponibles para esta fecha")
        else:
            # Validación simple (ya controlada por horarios disponibles)

            sheet.append_row([
                nombre,
                telefono,
                servicio,
                profesional,
                fecha_str,
                hora,
                observaciones,
                "Pendiente"
            ])
        st.success("Cita creada")

# ----------------------
# GESTIÓN DE CITAS
# ----------------------
st.subheader("📋 Gestión de citas")

data = sheet.get_all_records()

if data:
    df = pd.DataFrame(data) 
else:
    df = pd.DataFrame(columns=[
        "Usuario", "Teléfono", "Servicio", "Profesional",
        "Fecha", "Hora", "Observaciones", "Estado"
    ])

if not df.empty:
    ultima_fecha = df["Fecha"].max()
    filtro_fecha = st.date_input(
        "Ver agenda por día",
        value=datetime.strptime(ultima_fecha, "%Y-%m-%d"),
        key="filtro"
    )
else:
    filtro_fecha = st.date_input(
        "Ver agenda por día",
        value=datetime.today(),
        key="filtro"
    )

if not df.empty and "Fecha" in df.columns:
    df["Fecha"] = df["Fecha"].astype(str)
    df_filtrado = df[df["Fecha"] == filtro_fecha.strftime("%Y-%m-%d")].sort_values(by="Hora")
else:
    df_filtrado = pd.DataFrame()

if not df_filtrado.empty:
    st.dataframe(df_filtrado)
    st.write(f"Citas del día: {len(df_filtrado)}")
else:
    st.info("No hay citas registradas aún")

# EXPORTAR
st.download_button("📥 Descargar agenda", df_filtrado.to_csv(index=False), "agenda.csv")

# BOTONES ACCIONES
if not df_filtrado.empty:
        opciones = [
            f"{i} - {row['Usuario']} ({row['Hora']})"
            for i, row in df_filtrado.iterrows()
        ]

        seleccion = st.selectbox("Selecciona una cita", opciones)

        idx = int(seleccion.split(" - ")[0])
        fila_sheet = idx + 2

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("Confirmar"):
                sheet.update_cell(fila_sheet, 8, "Confirmada")
                st.success("Cita confirmada")

        with col2:
            if st.button("Cancelar"):
                sheet.update_cell(fila_sheet, 8, "Cancelada")
                st.success("Cita cancelada")

        with col3:
            if st.button("Editar"):
                st.info("Edición en próxima versión")

else:
    st.info("Sin citas")

# ----------------------
# LINK PARA CLIENTES
# ----------------------
st.subheader("📲 Compartir con clientes")
link = st.text_input("Link de la app", "")
st.code(link)
st.write("Comparte este link por WhatsApp para que agenden")
