import streamlit as st
import pandas as pd
import os
import requests
import re
from datetime import date
from fpdf import FPDF
from supabase import create_client, Client

# =====================================
# CONFIGURACIÓN SUPABASE
# =====================================

SUPABASE_URL = "https://zwchdpugmqturznuxntc.supabase.co"

SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp3Y2hkcHVnbXF0dXJ6bnV4bnRjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg5OTM0MjYsImV4cCI6MjEwNDU2OTQyNn0.3ZPaWLTh2rWcnGvK_Cg5USgAOGxrB0dRd-AwYhEPK6s"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================================
# CONFIGURACIÓN SEGURIDAD
# =====================================

USUARIO_ADMIN = "Asistentes de maniobra"
PASSWORD_ADMIN = "Seguridad2026"

# =====================================
# ARCHIVOS LOCALES
# =====================================

CHOFERES_EXTRAS_FILE = "choferes_extras.txt"

# =====================================
# FUNCIONES Y CACHÉ
# =====================================

@st.cache_data(ttl=300)
def consultar_infracciones_cache():
    try:
        response = supabase.table("infracciones").select("*").execute()
        return response.data
    except Exception as e:
        st.error(f"Error de conexión con la base de datos: {e}")
        return []


def cargar_lista_txt(ruta_archivo, nombres_defecto):
    if os.path.exists(ruta_archivo):
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return nombres_defecto


def guardar_chofer_extra(nombre):
    with open(CHOFERES_EXTRAS_FILE, "a", encoding="utf-8") as f:
        f.write(nombre + "\n")


def limpiar_nombre_archivo(texto):
    texto = texto.strip()
    texto = texto.replace(" ", "_")
    texto = re.sub(r'[^A-Za-z0-9_\-]', '', texto)
    return texto


def generar_pdf_informe(row):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    
    pdf.cell(200, 10, "Reporte de Incumplimiento de Seguridad e Higiene", ln=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(200, 10, f"Fecha del Registro: {row.get('fecha', row.get('Fecha', 'N/A'))}", ln=True)
    pdf.cell(200, 10, f"Conductor/Operario: {row.get('operario', row.get('Operario', 'N/A'))}", ln=True)
    pdf.cell(200, 10, f"Lista de Origen: {row.get('grupo_lista', row.get('Grupo_lista', 'N/A'))}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, "Desvios Detectados:", ln=True)
    pdf.set_font("Arial", "", 12)
    
    # Soporta que la columna se llame 'faltas' o 'Faltas'
    faltas_data = row.get('faltas', row.get('Faltas', ''))
    if isinstance(faltas_data, list):
        for falta in faltas_data:
            pdf.cell(200, 8, f"- {falta}", ln=True)
    else:
        pdf.cell(200, 8, f"- {faltas_data}", ln=True)
        
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, "Observaciones / Sancion:", ln=True)
    pdf.set_font("Arial", "", 12)
    
    obs_data = row.get('observaciones', row.get('Sancion', 'Sin observaciones adicionales.'))
    pdf.multi_cell(0, 10, str(obs_data))
    
    return pdf.output(dest="S").encode("latin-1", errors="ignore")

# =====================================
# CARGA DE LISTAS
# =====================================

LISTA_T1 = cargar_lista_txt("choferes_t1.txt", [])
LISTA_T2 = cargar_lista_txt("choferes_t2.txt", [])
LISTA_T2_CATAMARCA = cargar_lista_txt("choferes_t2_catamarca.txt", [])
LISTA_T2_LARIOJA = cargar_lista_txt("choferes_t2_larioja.txt", [])
LISTA_T2_SANTIAGO = cargar_lista_txt("choferes_t2_santiago.txt", [])

# =====================================
# CONFIGURACIÓN STREAMLIT
# =====================================

st.set_page_config(page_title="Control de Seguridad Industrial", layout="wide")

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

# =====================================
# LOGIN
# =====================================

def login():
    st.title("Acceso al Sistema de Seguridad")
    user = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        if user == USUARIO_ADMIN and password == PASSWORD_ADMIN:
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Credenciales incorrectas.")

# =====================================
# APLICACIÓN PRINCIPAL
# =====================================

if not st.session_state["autenticado"]:
    login()
else:
    st.sidebar.title("Navegación")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state["autenticado"] = False
        st.rerun()

    st.title("Sistema de Gestión de Seguridad e Higiene")

    # PANEL DE ALERTAS
    datos_alertas = consultar_infracciones_cache()
    if datos_alertas:
        df_alertas = pd.DataFrame(datos_alertas)
        # Buscamos 'operario' tolerando mayúsculas 'Operario'
        col_op = "operario" if "operario" in df_alertas.columns else ("Operario" if "Operario" in df_alertas.columns else None)
        
        if not df_alertas.empty and col_op:
            conteo_faltas = df_alertas[col_op].value_counts()
            reincidentes = conteo_faltas[conteo_faltas >= 3]

            if not reincidentes.empty:
                with st.container(border=True):
                    st.error("⚠️ ALERTA DE SEGURIDAD: CONTROL DE REINCIDENCIA CRÍTICA")
                    for chofer, total in reincidentes.items():
                        st.markdown(f"* El conductor **{chofer}** ha acumulado **{total} informes**.")

    # PESTAÑAS
    tab_reg, tab_hist = st.tabs(["Registro de Incidencias", "Historial de Informes"])

    # REGISTRO
    with tab_reg:
        st.subheader("Formulario de Registro")
        opcion_seleccionada = st.radio(
            "Seleccione el grupo de personal:",
            [
                "Choferes de T1", "Choferes de T2", "Choferes de T2 Catamarca",
                "Choferes de T2 La Rioja", "Choferes de T2 Santiago Del Estero", "Cargar nombres apartes"
            ]
        )

        operario = ""
        grupo_pertenencia = ""

        if opcion_seleccionada == "Choferes de T1":
            operario = st.selectbox("Personal de T1 Involucrado", LISTA_T1)
            grupo_pertenencia = "T1"
        elif opcion_seleccionada == "Choferes de T2":
            operario = st.selectbox("Personal de T2 Involucrado", LISTA_T2)
            grupo_pertenencia = "T2"
        elif opcion_seleccionada == "Choferes de T2 Catamarca":
            operario = st.selectbox("Choferes de T2 Catamarca", LISTA_T2_CATAMARCA)
            grupo_pertenencia = "T2 Catamarca"
        elif opcion_seleccionada == "Choferes de T2 La Rioja":
            operario = st.selectbox("Choferes de T2 La Rioja", LISTA_T2_LARIOJA)
            grupo_pertenencia = "T2 La Rioja"
        elif opcion_seleccionada == "Choferes de T2 Santiago Del Estero":
            operario = st.selectbox("Choferes de T2 Santiago Del Estero", LISTA_T2_SANTIAGO)
            grupo_pertenencia = "T2 Santiago Del Estero"
        elif opcion_seleccionada == "Cargar nombres apartes":
            st.info("Módulo para registrar choferes fuera de T1/T2.")
            grupo_pertenencia = "Carga Aparte / Extra"
            with st.expander("➕ Registrar nuevo chofer"):
                nuevo_nombre = st.text_input("Nombre completo del nuevo chofer")
                if st.button("Guardar nombre en el sistema"):
                    if nuevo_nombre.strip() != "":
                        guardar_chofer_extra(nuevo_nombre.strip())
                        st.success(f"{nuevo_nombre} agregado con éxito.")
                        st.rerun()
                    else:
                        st.error("El nombre no puede estar vacío.")

            lista_extras = cargar_lista_txt(CHOFERES_EXTRAS_FILE, [])
            if lista_extras:
                operario = st.selectbox("Seleccione el chofer", lista_extras)
            else:
                st.warning("No hay choferes cargados.")

        st.write("---")
        st.markdown(f"**Conductor:** {operario} | **Lista de Origen:** {grupo_pertenencia}")

        faltas = st.multiselect(
            "Tipos de Incumplimiento",
            [
                "No utiliza Cuñas/Calzas", "Situacion de riesgo", "Falta de E.P.P",
                "Uso del celular", "Comportamiento indebido", "No cumple con el punto seguro",
                "Estaciona en zona prohibida", "No posee alarma de retroceso", "Exceso de velocidad"
            ]
        )

        observaciones = st.text_area("Observaciones adicionales / Detalles")
        fecha_registro = st.date_input("Fecha del Evento", date.today())

        if st.button("Guardar Informe"):
            if not operario:
                st.error("Por favor, seleccione un operario/chofer válido.")
            elif not faltas:
                st.error("Debe seleccionar al menos un tipo de incumplimiento.")
            else:
                # Mapeamos a minúsculas para mantener orden interno
                datos_informe = {
                    "operario": operario,
                    "grupo_lista": grupo_pertenencia,
                    "faltas": faltas,
                    "observaciones": observaciones,
                    "fecha": str(fecha_registro)
                }
                try:
                    supabase.table("infracciones").insert(datos_informe).execute()
                    st.success("¡Informe registrado exitosamente!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as error_db:
                    st.error(f"Error al guardar en la base de datos: {error_db}")

    # HISTORIAL
    with tab_hist:
        st.subheader("Historial de Registros")
        
        datos_historial = consultar_infracciones_cache()
        if not datos_historial:
            st.info("No hay informes registrados todavía en esta base de datos.")
        else:
            df_historial = pd.DataFrame(datos_historial)
            if df_historial.empty:
