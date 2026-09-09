
import streamlit as st
import pandas as pd
import os
import requests
import re
from datetime import date
from fpdf import FPDF
from supabase import create_client, Client

# =====================================
# CONFIGURACIÓN SUPABASE (Reemplaza con tus nuevos datos gratuitos)
# =====================================

SUPABASE_URL = "https://supabase.co"

SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRzaGxwZWllaWZldmJ2dWJhY21uIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkwNDg1NzUsImV4cCI6MjA5NDYyNDU3NX0.dExc9YVOEyBVxyNTJ9CYW3lM4cvQgEsPXpjXY1rhj6Y"

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# =====================================
# CONFIGURACIÓN SEGURIDAD
# =====================================

USUARIO_ADMIN = "Asistentes de maniobra"
PASSWORD_ADMIN = "Seguridad2026"

# =====================================
# ARCHIVOS
# =====================================

CHOFERES_EXTRAS_FILE = "choferes_extras.txt"

# =====================================
# FUNCIONES Y CACHÉ (SOLUCIÓN DE MEMORIA)
# =====================================

# El decorador cache_data almacena las consultas por 5 minutos (300 segundos).
# Esto soluciona de raíz el consumo masivo de memoria y transferencia de red.
@st.cache_data(ttl=300)
def consultar_infracciones_cache():
    return supabase.table("infracciones").select("*").execute()


def cargar_lista_txt(ruta_archivo, nombres_defecto):

    if os.path.exists(ruta_archivo):

        with open(
            ruta_archivo,
            "r",
            encoding="utf-8"
        ) as f:

            return [
                line.strip()
                for line in f.readlines()
                if line.strip()
            ]

    return nombres_defecto


def guardar_chofer_extra(nombre):

    with open(
        CHOFERES_EXTRAS_FILE,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(nombre + "\n")


def limpiar_nombre_archivo(texto):

    texto = texto.strip()

    texto = texto.replace(" ", "_")

    texto = re.sub(
        r'[^A-Za-z0-9_\-]',
        '',
        texto
    )

    return texto

# =====================================
# LISTAS
# =====================================

LISTA_T1 = cargar_lista_txt(
    "choferes_t1.txt",
    []
)

LISTA_T2 = cargar_lista_txt(
    "choferes_t2.txt",
    []
)

LISTA_T2_CATAMARCA = cargar_lista_txt(
    "choferes_t2_catamarca.txt",
    []
)

LISTA_T2_LARIOJA = cargar_lista_txt(
    "choferes_t2_larioja.txt",
    []
)

LISTA_T2_SANTIAGO = cargar_lista_txt(
    "choferes_t2_santiago.txt",
    []
)

# =====================================
# STREAMLIT
# =====================================

st.set_page_config(
    page_title="Control de Seguridad Industrial",
    layout="wide"
)

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

# =====================================
# LOGIN
# =====================================

def login():

    st.title("Acceso al Sistema de Seguridad")

    user = st.text_input("Usuario")

    password = st.text_input(
        "Contraseña",
        type="password"
    )

    if st.button("Ingresar"):

        if (
            user == USUARIO_ADMIN
            and password == PASSWORD_ADMIN
        ):

            st.session_state["autenticado"] = True
            st.rerun()

        else:

            st.error(
                "Credenciales incorrectas."
            )

# =====================================
# APP PRINCIPAL
# =====================================

if not st.session_state["autenticado"]:

    login()

else:

    st.sidebar.title("Navegación")

    if st.sidebar.button("Cerrar Sesión"):

        st.session_state["autenticado"] = False
        st.rerun()

    st.title(
        "Sistema de Gestión de Seguridad e Higiene"
    )

    # =====================================
    # ALERTAS (OPTIMIZADO CON CACHÉ)
    # =====================================

    try:
        # Usamos la nueva función con caché para no agotar tu plan gratuito
        response = consultar_infracciones_cache()

        df_alertas = pd.DataFrame(
            response.data
        )

        if not df_alertas.empty:

            conteo_faltas = (
                df_alertas["operario"]
                .value_counts()
            )

            reincidentes = (
                conteo_faltas[
                    conteo_faltas >= 3
                ]
            )

            if not reincidentes.empty:

                with st.container(border=True):

                    st.error(
                        "⚠️ ALERTA DE SEGURIDAD: CONTROL DE REINCIDENCIA CRÍTICA"
                    )

                    for chofer, total in reincidentes.items():

                        st.markdown(
                            f"* El conductor **{chofer}** ha acumulado **{total} informes**."
                        )

    except Exception as e:

        st.error(
            f"Error cargando alertas: {e}"
        )

    # =====================================
    # TABS
    # =====================================

    tab_reg, tab_hist = st.tabs([
        "Registro de Incidencias",
        "Historial de Informes"
    ])

    # =====================================
    # REGISTRO
    # =====================================

    with tab_reg:

        st.subheader(
            "Formulario de Registro"
        )

        opcion_seleccionada = st.radio(
            "Seleccione el grupo de personal:",
            [
                "Choferes de T1",
                "Choferes de T2",
                "Choferes de T2 Catamarca",
                "Choferes de T2 La Rioja",
                "Choferes de T2 Santiago Del Estero",
                "Cargar nombres apartes"
            ]
        )

        operario = ""
        grupo_pertenencia = ""  # Variable para guardar a qué lista pertenece

        if opcion_seleccionada == "Choferes de T1":

            operario = st.selectbox(
                "Personal de T1 Involucrado",
                LISTA_T1
            )
            grupo_pertenencia = "T1"

        elif opcion_seleccionada == "Choferes de T2":

            operario = st.selectbox(
                "Personal de T2 Involucrado",
                LISTA_T2
            )
            grupo_pertenencia = "T2"

        elif opcion_seleccionada == "Choferes de T2 Catamarca":

            operario = st.selectbox(
                "Choferes de T2 Catamarca",
                LISTA_T2_CATAMARCA
            )
            grupo_pertenencia = "T2 Catamarca"

        elif opcion_seleccionada == "Choferes de T2 La Rioja":

            operario = st.selectbox(
                "Choferes de T2 La Rioja",
                LISTA_T2_LARIOJA
            )
            grupo_pertenencia = "T2 La Rioja"

        elif opcion_seleccionada == "Choferes de T2 Santiago Del Estero":

            operario = st.selectbox(
                "Choferes de T2 Santiago Del Estero",
                LISTA_T2_SANTIAGO
            )
            grupo_pertenencia = "T2 Santiago Del Estero"

        elif opcion_seleccionada == "Cargar nombres apartes":

            st.info(
                "Módulo para registrar choferes fuera de T1/T2."
            )
            grupo_pertenencia = "Carga Aparte / Extra"

            with st.expander(
                "➕ Registrar nuevo chofer"
            ):

                nuevo_nombre = st.text_input(
                    "Nombre completo del nuevo chofer"
                )

                if st.button(
                    "Guardar nombre en el sistema"
                ):

                    if nuevo_nombre.strip() != "":

                        guardar_chofer_extra(
                            nuevo_nombre.strip()
                        )

                        st.success(
                            f"{nuevo_nombre} agregado con éxito."
                        )

                        st.rerun()

                    else:

                        st.error(
                            "El nombre no puede estar vacío."
                        )

            lista_extras = cargar_lista_txt(
                CHOFERES_EXTRAS_FILE,
                []
            )

            if lista_extras:

                operario = st.selectbox(
                    "Seleccione el chofer",
                    lista_extras
                )

            else:

                st.warning(
                    "No hay choferes cargados."
                )

        # =====================================
        # FORMULARIO
        # =====================================
        
        st.write("---")
        st.markdown(f"**Conductor:** {operario} | **Lista de Origen:** {grupo_pertenencia}")

        # Se agregaron los nuevos desvíos solicitados al listado
        faltas = st.multiselect(
            "Tipos de Incumplimiento",
            [
                "No utiliza Cuñas/Calzas",
                "Situacion de riesgo",
                "Falta de E.P.P",
                "Uso del celular",
                "Comportamiento indebido",
                "No cumple con el punto seguro",
                "Estaciona en zona prohibida",
                "No posee alarma de retroceso",
                "Exceso de velocidad"
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
                # El diccionario incluye la columna 'grupo_lista' para guardar el origen
                datos_informe = {
                    "operario": operario,
                    "grupo_lista": grupo_pertenencia,
                    "faltas": faltas,
