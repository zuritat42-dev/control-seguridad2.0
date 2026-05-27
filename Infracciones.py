import streamlit as st
import pandas as pd
import os
import requests
from datetime import date
from fpdf import FPDF
from supabase import create_client, Client

# =====================================
# CONFIGURACIÓN SUPABASE
# =====================================

SUPABASE_URL = "https://dshlpeieifevbvubacmn.supabase.co"

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
# FUNCIONES
# =====================================

def cargar_lista_txt(ruta_archivo):

    try:

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

        return []

    except:
        return []


def guardar_chofer_extra(nombre):

    with open(
        CHOFERES_EXTRAS_FILE,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(nombre + "\n")


# =====================================
# LISTAS
# =====================================

LISTA_T1 = cargar_lista_txt(
    "choferes_t1.txt"
)

LISTA_T2 = cargar_lista_txt(
    "choferes_t2.txt"
)

LISTA_T2_CATAMARCA = cargar_lista_txt(
    "choferes_t2_catamarca.txt"
)

LISTA_T2_LARIOJA = cargar_lista_txt(
    "choferes_t2_larioja.txt"
)

LISTA_T2_SANTIAGO = cargar_lista_txt(
    "choferes_t2_santiago.txt"
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
    # ALERTAS
    # =====================================

    try:

        response = (
            supabase
            .table("infracciones")
            .select("*")
            .execute()
        )

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
                            f"* El conductor **{chofer}** acumula **{total} informes registrados**."
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

        if opcion_seleccionada == "Choferes de T1":

            operario = st.selectbox(
                "Personal de T1",
                LISTA_T1
            )

        elif opcion_seleccionada == "Choferes de T2":

            operario = st.selectbox(
                "Personal de T2",
                LISTA_T2
            )

        elif opcion_seleccionada == "Choferes de T2 Catamarca":

            operario = st.selectbox(
                "Choferes T2 Catamarca",
                LISTA_T2_CATAMARCA
            )

        elif opcion_seleccionada == "Choferes de T2 La Rioja":

            operario = st.selectbox(
                "Choferes T2 La Rioja",
                LISTA_T2_LARIOJA
            )

        elif opcion_seleccionada == "Choferes de T2 Santiago Del Estero":

            operario = st.selectbox(
                "Choferes T2 Santiago",
                LISTA_T2_SANTIAGO
            )

        else:

            with st.expander(
                "➕ Registrar nuevo chofer"
            ):

                nuevo_nombre = st.text_input(
                    "Nombre completo"
                )

                if st.button(
                    "Guardar nuevo chofer"
                ):

                    if nuevo_nombre.strip():

                        guardar_chofer_extra(
                            nuevo_nombre.strip()
                        )

                        st.success(
                            "Chofer agregado."
                        )

                        st.rerun()

            lista_extras = cargar_lista_txt(
                CHOFERES_EXTRAS_FILE
            )

            operario = st.selectbox(
                "Chofer",
                lista_extras
            )

        # =====================================
        # FORMULARIO
        # =====================================

        faltas = st.multiselect(
            "Tipos de Incumplimiento",
            [
                "No utiliza Cuñas/Calzas",
                "Situacion de riesgo",
                "Falta de E.P.P",
                "Uso del celular",
                "Comportamiento indebido",
                "No cumple con el punto seguro",
                "No espera asistencia en reversa",
                "Exceso de velocidad",
                "Interaccion Hombre-Maquina"
            ]
        )

        fecha = st.date_input(
            "Fecha del Reporte",
            date.today()
        )

        sancion = st.text_input(
            "Sanción Administrativa"
        )

        descripcion = st.text_area(
            "Descripción Técnica"
        )

        foto = st.file_uploader(
            "Adjuntar Evidencia",
            type=["jpg", "png", "jpeg"]
        )

        # =====================================
        # GUARDAR
        # =====================================

        if st.button(
            "Confirmar y Guardar Registro",
            type="primary",
            use_container_width=True
        ):

            if not operario:

                st.error(
                    "Debe seleccionar un chofer."
                )

            elif not faltas:

                st.error(
                    "Debe seleccionar una falta."
                )

            else:

                foto_url = "Sin Evidencia"

                # =====================================
                # SUBIR FOTO A SUPABASE
                # =====================================

                try:

                    if foto:

                        nombre_archivo = (
                            f"{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}_{foto.name}"
                        )

                        contenido = foto.getvalue()

                        supabase.storage.from_(
                            "fotos-infracciones"
                        ).upload(
                            nombre_archivo,
                            contenido
                        )

                        foto_url = supabase.storage.from_(
                            "fotos-infracciones"
                        ).get_public_url(
                            nombre_archivo
                        )

                except Exception as e:

                    st.error(
                        f"Error subiendo imagen: {e}"
                    )

                # =====================================
                # GUARDAR INFORME
                # =====================================

                try:

                    supabase.table(
                        "infracciones"
                    ).insert({

                        "fecha": str(fecha),
                        "operario": operario,
                        "faltas": ", ".join(faltas),
                        "descripcion": descripcion,
                        "sancion": sancion,
                        "foto_path": foto_url

                    }).execute()

                    st.success(
                        "Registro almacenado exitosamente."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Error guardando: {e}"
                    )

    # =====================================
    # HISTORIAL
    # =====================================

    with tab_hist:

        st.subheader(
            "Administración de Registros"
        )

        try:

            response = (
                supabase
                .table("infracciones")
                .select("*")
                .order("id", desc=True)
                .execute()
            )

            datos = pd.DataFrame(
                response.data
            )

            if not datos.empty:

                for i, fila in datos.iterrows():

                    with st.container(border=True):

                        st.markdown(
                            f"### Reporte: {fila['fecha']} | {fila['operario']}"
                        )

                        st.markdown(
                            f"**Infracción:** {fila['faltas']}"
                        )

                        st.markdown(
                            f"**Sanción:** {fila['sancion']}"
                        )

                        st.write(
                            fila['descripcion']
                        )

                        if fila['foto_path'] != "Sin Evidencia":

                            st.image(
                                fila['foto_path'],
                                width=300
                            )

                        # =====================================
                        # PDF
                        # =====================================

                        pdf = FPDF()

                        pdf.add_page()

                        pdf.set_font(
                            "Arial",
                            "B",
                            16
                        )

                        pdf.cell(
                            0,
                            10,
                            "INFORME DE SEGURIDAD",
                            ln=True,
                            align="C"
                        )

                        pdf.ln(10)

                        pdf.set_font(
                            "Arial",
                            "",
                            12
                        )

                        pdf.multi_cell(
                            0,
                            10,
                            f"Fecha: {fila['fecha']}"
                        )

                        pdf.multi_cell(
                            0,
                            10,
                            f"Operario: {fila['operario']}"
                        )

                        pdf.multi_cell(
                            0,
                            10,
                            f"Faltas: {fila['faltas']}"
                        )

                        pdf.multi_cell(
                            0,
                            10,
                            f"Sanción: {fila['sancion']}"
                        )

                        pdf.multi_cell(
                            0,
                            10,
                            f"Descripción: {fila['descripcion']}"
                        )

                        try:

                            if fila['foto_path'] != "Sin Evidencia":

                                response_img = requests.get(
                                    fila['foto_path']
                                )

                                with open(
                                    "temp_img.jpg",
                                    "wb"
                                ) as img:

                                    img.write(
                                        response_img.content
                                    )

                                pdf.image(
                                    "temp_img.jpg",
                                    w=120
                                )

                        except:
                            pass

                        # =====================================
                        # PDF CORREGIDO
                        # =====================================

                        pdf_output = pdf.output(
                            dest="S"
                        )

                        pdf_bytes = pdf_output.encode(
                            "latin-1"
                        )

                        st.download_button(
                            label="📥 Descargar PDF",
                            data=pdf_bytes,
                            file_name=f"informe_{fila['id']}.pdf",
                            mime="application/pdf",
                            key=f"pdf_{i}"
                        )

            else:

                st.warning(
                    "No existen registros todavía."
                )

        except Exception as e:

            st.error(
                f"Error cargando historial: {e}"
            )