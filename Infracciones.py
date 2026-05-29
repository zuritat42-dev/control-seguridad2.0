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

        if opcion_seleccionada == "Choferes de T1":

            operario = st.selectbox(
                "Personal de T1 Involucrado",
                LISTA_T1
            )

        elif opcion_seleccionada == "Choferes de T2":

            operario = st.selectbox(
                "Personal de T2 Involucrado",
                LISTA_T2
            )

        elif opcion_seleccionada == "Choferes de T2 Catamarca":

            operario = st.selectbox(
                "Choferes de T2 Catamarca",
                LISTA_T2_CATAMARCA
            )

        elif opcion_seleccionada == "Choferes de T2 La Rioja":

            operario = st.selectbox(
                "Choferes de T2 La Rioja",
                LISTA_T2_LARIOJA
            )

        elif opcion_seleccionada == "Choferes de T2 Santiago Del Estero":

            operario = st.selectbox(
                "Choferes de T2 Santiago Del Estero",
                LISTA_T2_SANTIAGO
            )

        elif opcion_seleccionada == "Cargar nombres apartes":

            st.info(
                "Módulo para registrar choferes fuera de T1/T2."
            )

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

        faltas = st.multiselect(
            "Tipos de Incumplimiento",
            [
                "No utiliza Cuñas/Calzas",
                "Situacion de riesgo",
                "Falta de E.P.P",
                "Uso del celular",
                "Comportamiento indebido",
                "No cumple con el punto seguro",
                "No espera a ser asistido en la Maniobra de reversa",
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
            "Descripción Técnica de los Hechos"
        )

        foto = st.file_uploader(
            "Adjuntar Evidencia Fotográfica",
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
                    "Debe seleccionar al menos una falta."
                )

            else:

                f_nombre = "Sin Evidencia"

                # =====================================
                # FOTO EN STORAGE
                # =====================================

                if foto:

                    try:

                        nombre_limpio = limpiar_nombre_archivo(
                            operario
                        )

                        extension = (
                            foto.name
                            .split(".")[-1]
                            .lower()
                        )

                        nombre_archivo = (
                            f"{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
                            f"_{nombre_limpio}.{extension}"
                        )

                        contenido = foto.getvalue()

                        supabase.storage.from_(
                            "fotos-infracciones"
                        ).upload(
                            path=nombre_archivo,
                            file=contenido,
                            file_options={
                                "content-type": foto.type
                            }
                        )

                        f_nombre = supabase.storage.from_(
                            "fotos-infracciones"
                        ).get_public_url(
                            nombre_archivo
                        )

                    except Exception as e:

                        st.error(
                            f"Error subiendo imagen: {e}"
                        )

                # =====================================
                # GUARDAR EN SUPABASE
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
                        "foto_path": f_nombre

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
                .execute()
            )

            datos = pd.DataFrame(
                response.data
            )

            if not datos.empty:

                for i, fila in (
                    datos.iloc[::-1]
                    .iterrows()
                ):

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
                            f"**Detalles:** {fila['descripcion']}"
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

                        pdf.set_auto_page_break(
                            auto=True,
                            margin=15
                        )

                        # Fondo

                        pdf.set_fill_color(
                            245,
                            245,
                            245
                        )

                        pdf.rect(
                            0,
                            0,
                            210,
                            297,
                            style='F'
                        )

                        # Título

                        pdf.set_text_color(
                            220,
                            0,
                            0
                        )

                        pdf.set_font(
                            "Helvetica",
                            "B",
                            18
                        )

                        pdf.cell(
                            0,
                            15,
                            "INFORME DE INCIDENCIA DE SEGURIDAD INDUSTRIAL",
                            ln=True,
                            align="C"
                        )

                        pdf.set_text_color(
                            80,
                            80,
                            80
                        )

                        pdf.set_font(
                            "Helvetica",
                            "I",
                            10
                        )

                        pdf.cell(
                            0,
                            5,
                            "Control de Gestion de Seguridad e Higiene",
                            ln=True,
                            align="C"
                        )

                        pdf.ln(10)

                        # Línea roja

                        pdf.set_draw_color(
                            220,
                            0,
                            0
                        )

                        pdf.line(
                            10,
                            pdf.get_y(),
                            200,
                            pdf.get_y()
                        )

                        pdf.ln(10)

                        # Datos

                        datos_pdf = [
                            ("Fecha del Reporte:", fila['fecha']),
                            ("Conductor / Operario:", fila['operario']),
                            ("Infracciones / Faltas:", fila['faltas']),
                            ("Sanción Administrativa:", fila['sancion'])
                        ]

                        for titulo, valor in datos_pdf:

                            pdf.set_font(
                                "Helvetica",
                                "B",
                                11
                            )

                            pdf.cell(
                                55,
                                10,
                                str(titulo),
                                border=0
                            )

                            pdf.set_font(
                                "Helvetica",
                                "",
                                11
                            )

                            pdf.multi_cell(
                                120,
                                10,
                                str(valor)
                            )

                            pdf.line(
                                10,
                                pdf.get_y(),
                                190,
                                pdf.get_y()
                            )

                            pdf.ln(2)

                        # Descripción

                        pdf.ln(5)

                        pdf.set_font(
                            "Helvetica",
                            "B",
                            12
                        )

                        pdf.cell(
                            0,
                            10,
                            "Descripción Técnica de los Hechos:",
                            ln=True
                        )

                        pdf.set_font(
                            "Helvetica",
                            "",
                            11
                        )

                        pdf.multi_cell(
                            180,
                            8,
                            str(fila['descripcion']),
                            border=1
                        )

                        pdf.ln(10)

                        # Evidencia

                        pdf.set_font(
                            "Helvetica",
                            "B",
                            12
                        )

                        pdf.cell(
                            0,
                            10,
                            "Evidencia Fotográfica:",
                            ln=True
                        )

                        pdf.ln(5)

                        if fila['foto_path'] != "Sin Evidencia":

                            try:

                                response_img = requests.get(
                                    fila['foto_path']
                                )

                                if response_img.status_code == 200:

                                    imagen_temp = f"temp_{i}.jpg"

                                    with open(
                                        imagen_temp,
                                        "wb"
                                    ) as img_file:

                                        img_file.write(
                                            response_img.content
                                        )

                                    pdf.image(
                                        imagen_temp,
                                        x=10,
                                        w=120
                                    )

                                    if os.path.exists(imagen_temp):

                                        os.remove(imagen_temp)

                            except Exception as e:

                                st.warning(
                                    f"No se pudo cargar la imagen en el PDF: {e}"
                                )

                        # =====================================
                        # EXPORTAR PDF
                        # =====================================

                        pdf_bytes = pdf.output(dest="S")

                        if isinstance(pdf_bytes, bytearray):
                            pdf_bytes = bytes(pdf_bytes)

                        elif isinstance(pdf_bytes, str):
                            pdf_bytes = pdf_bytes.encode("latin-1")

                        st.download_button(
                            label="📥 Descargar PDF",
                            data=pdf_bytes,
                            file_name=f"Informe_{fila['id']}.pdf",
                            mime="application/pdf",
                            key=f"dl_{i}"
                        )

            else:

                st.warning(
                    "No existen registros todavía."
                )

        except Exception as e:

            st.error(
                f"Error cargando historial: {e}"
            )
