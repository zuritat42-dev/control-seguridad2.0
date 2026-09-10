import streamlit as st
import pandas as pd
import os
import requests
import re
import io
from datetime import date, datetime
from fpdf import FPDF
from supabase import create_client, Client
from PIL import Image


# ============================================================
# CONFIGURACIÓN SUPABASE
# ============================================================

SUPABASE_URL = "https://zwchdpugmqturznuxntc.supabase.co"

SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp3Y2hkcHVnbXF0dXJ6bnV4bnRjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg5OTM0MjYsImV4cCI6MjEwNDU2OTQyNn0.3ZPaWLTh2rWcnGvK_Cg5USgAOGxrB0dRd-AwYhEPK6s"

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# ============================================================
# CONFIGURACIÓN DEL SISTEMA
# ============================================================

USUARIO_ADMIN = "Asistentes de maniobra"
PASSWORD_ADMIN = "Seguridad2026"

# Nombre EXACTO del bucket de Supabase Storage
STORAGE_BUCKET = "evidencias"

# Nombre EXACTO de la tabla
TABLA_INFRACCIONES = "infracciones"

CHOFERES_EXTRAS_FILE = "choferes_extras.txt"


# ============================================================
# CONFIGURACIÓN STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Control de Seguridad Industrial",
    layout="wide"
)


# ============================================================
# FUNCIONES GENERALES
# ============================================================

def obtener_valor(row, *nombres, default=""):
    """
    Busca un valor probando varios nombres de columna.
    Permite trabajar aunque algunas columnas estén en
    mayúsculas/minúsculas.
    """

    for nombre in nombres:
        if nombre in row:
            valor = row[nombre]

            if valor is None:
                return default

            return valor

    return default


def limpiar_nombre_archivo(texto):
    """
    Convierte el nombre del operario en un nombre seguro
    para utilizarlo en Storage.
    """

    if texto is None:
        texto = ""

    texto = str(texto).strip()

    # Eliminar caracteres problemáticos
    texto = re.sub(
        r'[\t\r\n]+',
        '_',
        texto
    )

    # Reemplazar espacios
    texto = texto.replace(" ", "_")

    # Mantener solamente caracteres seguros
    texto = re.sub(
        r'[^A-Za-z0-9_\-]',
        '',
        texto
    )

    # Evitar nombre vacío
    if not texto:
        texto = "operario"

    return texto


def cargar_lista_txt(ruta_archivo, nombres_defecto):
    """
    Carga los nombres desde un archivo TXT.
    """

    if os.path.exists(ruta_archivo):

        try:
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

        except Exception:
            return nombres_defecto

    return nombres_defecto


def guardar_chofer_extra(nombre):
    """
    Guarda un chofer adicional en el archivo TXT.
    """

    with open(
        CHOFERES_EXTRAS_FILE,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            nombre.strip() + "\n"
        )


# ============================================================
# CONSULTAR INFRACCIONES
# ============================================================

@st.cache_data(ttl=30)
def consultar_infracciones_cache():

    try:

        respuesta = (
            supabase
            .table(TABLA_INFRACCIONES)
            .select("*")
            .order("id", desc=True)
            .execute()
        )

        return respuesta.data

    except Exception as e:

        st.error(
            f"Error de conexión con la base de datos: {e}"
        )

        return []


# ============================================================
# SUBIR FOTOGRAFÍA A SUPABASE STORAGE
# ============================================================

def subir_fotografia(archivo, operario, fecha_evento):

    if archivo is None:
        return None, None

    try:

        # ----------------------------------------------------
        # Abrir imagen
        # ----------------------------------------------------

        imagen = Image.open(archivo)

        # Convertir a RGB para evitar problemas con PNG/RGBA
        if imagen.mode != "RGB":
            imagen = imagen.convert("RGB")

        # ----------------------------------------------------
        # Reducir tamaño si es demasiado grande
        # ----------------------------------------------------

        imagen.thumbnail(
            (1600, 1600)
        )

        # ----------------------------------------------------
        # Comprimir imagen
        # ----------------------------------------------------

        buffer = io.BytesIO()

        imagen.save(
            buffer,
            format="JPEG",
            quality=75,
            optimize=True
        )

        contenido = buffer.getvalue()

        # ----------------------------------------------------
        # Crear nombre seguro
        # ----------------------------------------------------

        nombre_operario = limpiar_nombre_archivo(
            operario
        )

        fecha_texto = str(
            fecha_evento
        )

        fecha_texto = limpiar_nombre_archivo(
            fecha_texto
        )

        hora_texto = datetime.now().strftime(
            "%H%M%S"
        )

        nombre_archivo = (
            f"{fecha_texto}_"
            f"{nombre_operario}_"
            f"{hora_texto}.jpg"
        )

        # ----------------------------------------------------
        # Ruta dentro del bucket
        # ----------------------------------------------------

        ruta_storage = (
            f"informes/{nombre_archivo}"
        )

        # ----------------------------------------------------
        # Subir archivo
        # ----------------------------------------------------

        supabase.storage.from_(
            STORAGE_BUCKET
        ).upload(
            ruta_storage,
            contenido,
            {
                "content-type": "image/jpeg",
                "cache-control": "3600",
                "upsert": False
            }
        )

        # ----------------------------------------------------
        # Obtener URL pública
        # ----------------------------------------------------

        resultado_url = (
            supabase
            .storage
            .from_(STORAGE_BUCKET)
            .get_public_url(ruta_storage)
        )

        # Dependiendo de la versión de la librería,
        # puede devolver directamente un string o un dict.
        if isinstance(resultado_url, str):

            foto_url = resultado_url

        elif isinstance(resultado_url, dict):

            foto_url = (
                resultado_url.get("publicUrl")
                or resultado_url.get("public_url")
                or resultado_url.get("url")
            )

        else:

            foto_url = str(
                resultado_url
            )

        return ruta_storage, foto_url

    except Exception as e:

        st.error(
            f"No se pudo subir la fotografía: {e}"
        )

        return None, None


# ============================================================
# GENERAR PDF
# ============================================================

def generar_pdf_informe(row):

    pdf = FPDF()

    pdf.set_auto_page_break(
        auto=True,
        margin=15
    )

    pdf.add_page()

    # ========================================================
    # TÍTULO
    # ========================================================

    pdf.set_font(
        "Arial",
        "B",
        16
    )

    pdf.cell(
        0,
        10,
        "REPORTE DE INCUMPLIMIENTO",
        ln=True,
        align="C"
    )

    pdf.set_font(
        "Arial",
        "",
        10
    )

    pdf.cell(
        0,
        7,
        "Seguridad e Higiene",
        ln=True,
        align="C"
    )

    pdf.ln(10)

    # ========================================================
    # NÚMERO DE INFORME
    # ========================================================

    informe_id = obtener_valor(
        row,
        "id",
        "ID",
        "Id",
        default="N/A"
    )

    pdf.set_font(
        "Arial",
        "B",
        11
    )

    pdf.cell(
        45,
        8,
        "N° de Informe:"
    )

    pdf.set_font(
        "Arial",
        "",
        11
    )

    pdf.cell(
        0,
        8,
        str(informe_id),
        ln=True
    )

    # ========================================================
    # FECHA DEL EVENTO
    # ========================================================

    fecha = obtener_valor(
        row,
        "Fecha",
        "fecha",
        default="N/A"
    )

    pdf.set_font(
        "Arial",
        "B",
        11
    )

    pdf.cell(
        45,
        8,
        "Fecha del Evento:"
    )

    pdf.set_font(
        "Arial",
        "",
        11
    )

    pdf.cell(
        0,
        8,
        str(fecha),
        ln=True
    )

    # ========================================================
    # FECHA Y HORA DE CREACIÓN
    # ========================================================

    created_at = obtener_valor(
        row,
        "created_at",
        "Created_at",
        "Created_At",
        default=""
    )

    if created_at:

        pdf.set_font(
            "Arial",
            "B",
            11
        )

        pdf.cell(
            45,
            8,
            "Registrado:"
        )

        pdf.set_font(
            "Arial",
            "",
            11
        )

        pdf.cell(
            0,
            8,
            str(created_at),
            ln=True
        )

    # ========================================================
    # OPERARIO
    # ========================================================

    operario = obtener_valor(
        row,
        "Operario",
        "operario",
        default="N/A"
    )

    pdf.set_font(
        "Arial",
        "B",
        11
    )

    pdf.cell(
        45,
        8,
        "Operario:"
    )

    pdf.set_font(
        "Arial",
        "",
        11
    )

    pdf.multi_cell(
        0,
        8,
        str(operario)
    )

    # ========================================================
    # GRUPO
    # ========================================================

    grupo = obtener_valor(
        row,
        "grupo_lista",
        "Grupo_lista",
        "grupo",
        "Grupo",
        default=""
    )

    if str(grupo).lower() == "nan":
        grupo = ""

    pdf.set_font(
        "Arial",
        "B",
        11
    )

    pdf.cell(
        45,
        8,
        "Lista de Origen:"
    )

    pdf.set_font(
        "Arial",
        "",
        11
    )

    pdf.cell(
        0,
        8,
        str(grupo),
        ln=True
    )

    # ========================================================
    # INCUMPLIMIENTOS
    # ========================================================

    pdf.ln(5)

    pdf.set_font(
        "Arial",
        "B",
        12
    )

    pdf.cell(
        0,
        8,
        "Desvíos Detectados:",
        ln=True
    )

    pdf.set_font(
        "Arial",
        "",
        11
    )

    faltas = obtener_valor(
        row,
        "Faltas",
        "faltas",
        default=""
    )

    if isinstance(faltas, list):

        for falta in faltas:

            pdf.multi_cell(
                0,
                7,
                f"- {str(falta)}"
            )

    else:

        texto_faltas = str(faltas)

        # Si viene guardado como lista de texto
        if texto_faltas.startswith("["):

            texto_faltas = (
                texto_faltas
                .replace("[", "")
                .replace("]", "")
                .replace("'", "")
                .replace('"', "")
            )

        pdf.multi_cell(
            0,
            7,
            f"- {texto_faltas}"
        )

    # ========================================================
    # SANCIÓN
    # ========================================================

    pdf.ln(5)

    pdf.set_font(
        "Arial",
        "B",
        12
    )

    pdf.cell(
        0,
        8,
        "Sanción / Observaciones:",
        ln=True
    )

    pdf.set_font(
        "Arial",
        "",
        11
    )

    sancion = obtener_valor(
        row,
        "Sancion",
        "sancion",
        default="Sin observaciones registradas."
    )

    pdf.multi_cell(
        0,
        8,
        str(sancion)
    )

    # ========================================================
    # DESCRIPCIÓN
    # ========================================================

    descripcion = obtener_valor(
        row,
        "Descripcion",
        "descripcion",
        default=""
    )

    if descripcion:

        pdf.ln(5)

        pdf.set_font(
            "Arial",
            "B",
            12
        )

        pdf.cell(
            0,
            8,
            "Descripción Técnica de los Hechos:",
            ln=True
        )

        pdf.set_font(
            "Arial",
            "",
            11
        )

        pdf.multi_cell(
            0,
            8,
            str(descripcion)
        )

    # ========================================================
    # FOTOGRAFÍA
    # ========================================================

    foto_url = obtener_valor(
        row,
        "foto_url",
        "Foto_url",
        "Foto_URL",
        default=""
    )

    if foto_url:

        try:

            respuesta = requests.get(
                str(foto_url),
                timeout=20
            )

            if respuesta.status_code == 200:

                # ------------------------------------------------
                # Guardamos temporalmente la imagen.
                # FPDF necesita una RUTA DE ARCHIVO.
                # ------------------------------------------------

                import tempfile

                archivo_temporal = tempfile.NamedTemporaryFile(
                    suffix=".jpg",
                    delete=False
                )

                ruta_temporal = (
                    archivo_temporal.name
                )

                archivo_temporal.write(
                    respuesta.content
                )

                archivo_temporal.close()

                try:

                    pdf.add_page()

                    pdf.set_font(
                        "Arial",
                        "B",
                        12
                    )

                    pdf.cell(
                        0,
                        10,
                        "Evidencia Fotográfica:",
                        ln=True
                    )

                    pdf.image(
                        ruta_temporal,
                        x=15,
                        y=30,
                        w=180
                    )

                finally:

                    try:
                        os.remove(
                            ruta_temporal
                        )
                    except Exception:
                        pass

        except Exception:

            # Si la foto no puede descargarse,
            # el PDF igualmente se genera.
            pass

    # ========================================================
    # DEVOLVER PDF
    # ========================================================

    resultado = pdf.output(
        dest="S"
    )

    # ========================================================
    # CORRECCIÓN IMPORTANTE
    #
    # Dependiendo de la versión de FPDF, output()
    # puede devolver bytes o bytearray.
    #
    # NO usamos .encode()
    # porque ese fue el error que apareció.
    # ========================================================

    if isinstance(resultado, bytes):
        return resultado

    if isinstance(resultado, bytearray):
        return bytes(resultado)

    if isinstance(resultado, str):
        return resultado.encode(
            "latin-1",
            errors="ignore"
        )

    return bytes(resultado)


# ============================================================
# CARGA DE LISTAS
# ============================================================

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


# ============================================================
# SESIÓN
# ============================================================

if "autenticado" not in st.session_state:

    st.session_state["autenticado"] = False


# ============================================================
# LOGIN
# ============================================================

def login():

    st.title(
        "Acceso al Sistema de Seguridad"
    )

    usuario = st.text_input(
        "Usuario"
    )

    password = st.text_input(
        "Contraseña",
        type="password"
    )

    if st.button(
        "Ingresar"
    ):

        if (
            usuario == USUARIO_ADMIN
            and password == PASSWORD_ADMIN
        ):

            st.session_state[
                "autenticado"
            ] = True

            st.rerun()

        else:

            st.error(
                "Credenciales incorrectas."
            )


# ============================================================
# SI NO ESTÁ AUTENTICADO
# ============================================================

if not st.session_state["autenticado"]:

    login()

# ============================================================
# APLICACIÓN PRINCIPAL
# ============================================================

else:

    # --------------------------------------------------------
    # SIDEBAR
    # --------------------------------------------------------

    st.sidebar.title(
        "Navegación"
    )

    if st.sidebar.button(
        "Cerrar Sesión"
    ):

        st.session_state[
            "autenticado"
        ] = False

        st.rerun()

    # --------------------------------------------------------
    # TÍTULO
    # --------------------------------------------------------

    st.title(
        "Sistema de Gestión de Seguridad e Higiene"
    )

    st.caption(
        "Registro permanente de informes y evidencias fotográficas."
    )

    # ========================================================
    # ALERTAS DE REINCIDENCIA
    # ========================================================

    datos_alertas = (
        consultar_infracciones_cache()
    )

    if datos_alertas:

        df_alertas = pd.DataFrame(
            datos_alertas
        )

        col_operario = None

        if "Operario" in df_alertas.columns:
            col_operario = "Operario"

        elif "operario" in df_alertas.columns:
            col_operario = "operario"

        if (
            not df_alertas.empty
            and col_operario
        ):

            conteo_faltas = (
                df_alertas[
                    col_operario
                ]
                .value_counts()
            )

            reincidentes = (
                conteo_faltas[
                    conteo_faltas >= 3
                ]
            )

            if not reincidentes.empty:

                with st.container(
                    border=True
                ):

                    st.error(
                        "⚠️ ALERTA DE SEGURIDAD: "
                        "CONTROL DE REINCIDENCIA CRÍTICA"
                    )

                    for chofer, total in reincidentes.items():

                        st.markdown(
                            f"* El conductor "
                            f"**{chofer}** ha acumulado "
                            f"**{total} informes**."
                        )

    # ========================================================
    # PESTAÑAS
    # ========================================================

    tab_registro, tab_historial = st.tabs(
        [
            "Registro de Incidencias",
            "Historial de Informes"
        ]
    )


    # ========================================================
    # REGISTRO DE INCIDENCIAS
    # ========================================================

    with tab_registro:

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
        grupo_pertenencia = ""

        # ----------------------------------------------------
        # T1
        # ----------------------------------------------------

        if opcion_seleccionada == "Choferes de T1":

            grupo_pertenencia = "T1"

            if LISTA_T1:

                operario = st.selectbox(
                    "Personal de T1 Involucrado",
                    LISTA_T1
                )

            else:

                st.warning(
                    "No se encontraron nombres "
                    "en choferes_t1.txt."
                )

        # ----------------------------------------------------
        # T2
        # ----------------------------------------------------

        elif opcion_seleccionada == "Choferes de T2":

            grupo_pertenencia = "T2"

            if LISTA_T2:

                operario = st.selectbox(
                    "Personal de T2 Involucrado",
                    LISTA_T2
                )

            else:

                st.warning(
                    "No se encontraron nombres "
                    "en choferes_t2.txt."
                )

        # ----------------------------------------------------
        # T2 CATAMARCA
        # ----------------------------------------------------

        elif opcion_seleccionada == "Choferes de T2 Catamarca":

            grupo_pertenencia = "T2 Catamarca"

            if LISTA_T2_CATAMARCA:

                operario = st.selectbox(
                    "Choferes de T2 Catamarca",
                    LISTA_T2_CATAMARCA
                )

            else:

                st.warning(
                    "No se encontraron nombres "
                    "en choferes_t2_catamarca.txt."
                )

        # ----------------------------------------------------
        # T2 LA RIOJA
        # ----------------------------------------------------

        elif opcion_seleccionada == "Choferes de T2 La Rioja":

            grupo_pertenencia = "T2 La Rioja"

            if LISTA_T2_LARIOJA:

                operario = st.selectbox(
                    "Choferes de T2 La Rioja",
                    LISTA_T2_LARIOJA
                )

            else:

                st.warning(
                    "No se encontraron nombres "
                    "en choferes_t2_larioja.txt."
                )

        # ----------------------------------------------------
        # T2 SANTIAGO
        # ----------------------------------------------------

        elif opcion_seleccionada == "Choferes de T2 Santiago Del Estero":

            grupo_pertenencia = (
                "T2 Santiago Del Estero"
            )

            if LISTA_T2_SANTIAGO:

                operario = st.selectbox(
                    "Choferes de T2 Santiago Del Estero",
                    LISTA_T2_SANTIAGO
                )

            else:

                st.warning(
                    "No se encontraron nombres "
                    "en choferes_t2_santiago.txt."
                )

        # ----------------------------------------------------
        # EXTRAS
        # ----------------------------------------------------

        elif opcion_seleccionada == "Cargar nombres apartes":

            grupo_pertenencia = (
                "Carga Aparte / Extra"
            )

            st.info(
                "Módulo para registrar choferes "
                "fuera de las listas principales."
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

                    if nuevo_nombre.strip():

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

        # ====================================================
        # DATOS SELECCIONADOS
        # ====================================================

        st.write("---")

        st.markdown(
            f"**Conductor:** {operario}"
            f" | **Lista de Origen:** "
            f"{grupo_pertenencia}"
        )

        # ====================================================
        # INCUMPLIMIENTOS
        # ====================================================

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
                "No espera a ser asistido en la Maniobra de reversa",
                "Exceso de velocidad",
                "Interaccion Hombre-Maquina"
            ]
        )

        # ====================================================
        # SANCIÓN
        # ====================================================

        sancion_input = st.text_area(
            "Sanción aplicada / Detalles de la medida"
        )

        # ====================================================
        # DESCRIPCIÓN
        # ====================================================

        descripcion_input = st.text_area(
            "Descripción Técnica de los Hechos"
        )

        # ====================================================
        # FECHA
        # ====================================================

        fecha_registro = st.date_input(
            "Fecha del Evento",
            date.today()
        )

        # ====================================================
        # FOTOGRAFÍA
        # ====================================================

        fotografia = st.file_uploader(
            "Adjuntar Evidencia Fotográfica",
            type=[
                "jpg",
                "jpeg",
                "png"
            ]
        )

        if fotografia:

            st.image(
                fotografia,
                caption="Vista previa de la evidencia",
                width=400
            )

        # ====================================================
        # GUARDAR INFORME
        # ====================================================

        if st.button(
            "Confirmar y Guardar Registro",
            type="primary"
        ):

            # ------------------------------------------------
            # VALIDACIONES
            # ------------------------------------------------

            if not operario:

                st.error(
                    "Por favor, seleccione "
                    "un operario/chofer válido."
                )

            elif not faltas:

                st.error(
                    "Debe seleccionar al menos "
                    "un tipo de incumplimiento."
                )

            else:

                # ------------------------------------------------
                # SUBIR FOTO PRIMERO
                # ------------------------------------------------

                foto_path = None
                foto_url = None

                if fotografia:

                    foto_path, foto_url = (
                        subir_fotografia(
                            fotografia,
                            operario,
                            fecha_registro
                        )
                    )

                # ------------------------------------------------
                # FECHA Y HORA AUTOMÁTICA
                # ------------------------------------------------

                momento_creacion = (
                    datetime.now().isoformat()
                )

                # ------------------------------------------------
                # DATOS DEL INFORME
                # ------------------------------------------------

                datos_informe = {

                    "Operario": operario,

                    "grupo_lista": (
                        grupo_pertenencia
                    ),

                    "Faltas": faltas,

                    "Sancion": (
                        sancion_input
                    ),

                    "Descripcion": (
                        descripcion_input
                    ),

                    "Fecha": (
                        str(fecha_registro)
                    ),

                    "created_at": (
                        momento_creacion
                    )
                }

                # ------------------------------------------------
                # FOTO
                # ------------------------------------------------

                if foto_path:

                    datos_informe[
                        "foto_path"
                    ] = foto_path

                if foto_url:

                    datos_informe[
                        "foto_url"
                    ] = foto_url

                # ------------------------------------------------
                # GUARDAR EN SUPABASE
                # ------------------------------------------------

                try:

                    respuesta = (
                        supabase
                        .table(
                            TABLA_INFRACCIONES
                        )
                        .insert(
                            datos_informe
                        )
                        .execute()
                    )

                    st.success(
                        "✅ ¡Informe registrado exitosamente!"
                    )

                    if fotografia and foto_url:

                        st.success(
                            "📸 La evidencia fotográfica "
                            "también fue guardada correctamente."
                        )

                    elif fotografia:

                        st.warning(
                            "⚠️ El informe fue guardado, "
                            "pero la fotografía no pudo subirse."
                        )

                    st.cache_data.clear()

                    st.rerun()

                except Exception as error_db:

                    st.error(
                        "Error al guardar en la "
                        f"base de datos: {error_db}"
                    )


    # ========================================================
    # HISTORIAL
    # ========================================================

    with tab_historial:

        st.subheader(
            "Historial de Registros"
        )

        datos_historial = (
            consultar_infracciones_cache()
        )

        if not datos_historial:

            st.info(
                "Todavía no hay informes registrados."
            )

        else:

            df_historial = pd.DataFrame(
                datos_historial
            )

            # ------------------------------------------------
            # FILTRO POR GRUPO
            # ------------------------------------------------

            columna_grupo = None

            if "grupo_lista" in df_historial.columns:

                columna_grupo = "grupo_lista"

            elif "Grupo_lista" in df_historial.columns:

                columna_grupo = "Grupo_lista"

            if columna_grupo:

                grupos_disponibles = [
                    "Mostrar Todos"
                ]

                grupos = (
                    df_historial[
                        columna_grupo
                    ]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )

                grupos_disponibles.extend(
                    sorted(grupos)
                )

                filtro_grupo = st.selectbox(
                    "Filtrar por lista de origen",
                    grupos_disponibles
                )

                if (
                    filtro_grupo
                    != "Mostrar Todos"
                ):

                    df_historial = (
                        df_historial[
                            df_historial[
                                columna_grupo
                            ].astype(str)
                            == filtro_grupo
                        ]
                    )

            # ------------------------------------------------
            # ORDENAR DEL MÁS NUEVO AL MÁS ANTIGUO
            # ------------------------------------------------

            if "id" in df_historial.columns:

                df_historial = (
                    df_historial
                    .sort_values(
                        "id",
                        ascending=False
                    )
                )

            # ------------------------------------------------
            # MOSTRAR INFORMES
            # ------------------------------------------------

            for _, row in df_historial.iterrows():

                informe_id = obtener_valor(
                    row,
                    "id",
                    "ID",
                    "Id",
                    default=""
                )

                fecha = obtener_valor(
                    row,
                    "Fecha",
                    "fecha",
                    default=""
                )

                operario = obtener_valor(
                    row,
                    "Operario",
                    "operario",
                    default="Sin nombre"
                )

                grupo = obtener_valor(
                    row,
                    "grupo_lista",
                    "Grupo_lista",
                    "grupo",
                    default=""
                )

                titulo = (
                    f"📄 Informe #{informe_id}"
                    f" - {operario}"
                    f" - {fecha}"
                )

                with st.expander(
                    titulo
                ):

                    # ==========================================
                    # COLUMNAS
                    # ==========================================

                    col1, col2 = st.columns(
                        [1.5, 1]
                    )

                    # ==========================================
                    # INFORMACIÓN
                    # ==========================================

                    with col1:

                        st.markdown(
                            f"**Fecha:** {fecha}"
                        )

                        st.markdown(
                            f"**Operario:** {operario}"
                        )

                        st.markdown(
                            f"**Grupo:** {grupo}"
                        )

                        created_at = obtener_valor(
                            row,
                            "created_at",
                            "Created_at",
                            "Created_At",
                            default=""
                        )

                        if created_at:

                            st.markdown(
                                f"**Fecha y hora de registro:** "
                                f"{created_at}"
                            )

                        st.markdown(
                            "**Incumplimientos:**"
                        )

                        faltas = obtener_valor(
                            row,
                            "Faltas",
                            "faltas",
                            default=""
                        )

                        if isinstance(
                            faltas,
                            list
                        ):

                            for falta in faltas:

                                st.markdown(
                                    f"• {falta}"
                                )

                        else:

                            texto_faltas = str(
                                faltas
                            )

                            st.markdown(
                                texto_faltas
                            )

                        st.markdown(
                            "**Sanción / Observaciones:**"
                        )

                        sancion = obtener_valor(
                            row,
                            "Sancion",
                            "sancion",
                            default=""
                        )

                        if sancion:

                            st.write(
                                sancion
                            )

                        else:

                            st.write(
                                "Sin observaciones registradas."
                            )

                        descripcion = obtener_valor(
                            row,
                            "Descripcion",
                            "descripcion",
                            default=""
                        )

                        if descripcion:

                            st.markdown(
                                "**Descripción Técnica:**"
                            )

                            st.write(
                                descripcion
                            )

                    # ==========================================
                    # FOTOGRAFÍA
                    # ==========================================

                    with col2:

                        foto_url = obtener_valor(
                            row,
                            "foto_url",
                            "Foto_url",
                            "Foto_URL",
                            default=""
                        )

                        if foto_url:

                            try:

                                st.image(
                                    foto_url,
                                    caption=(
                                        "Evidencia fotográfica"
                                    ),
                                    use_container_width=True
                                )

                            except Exception:

                                st.warning(
                                    "No se pudo mostrar "
                                    "la evidencia fotográfica."
                                )

                        else:

                            st.info(
                                "Este informe no tiene "
                                "evidencia fotográfica."
                            )

                    # ==========================================
                    # PDF
                    # ==========================================

                    st.write("---")

                    try:

                        pdf_bytes = (
                            generar_pdf_informe(
                                row
                            )
                        )

                        nombre_pdf = (
                            f"Informe_"
                            f"{informe_id}.pdf"
                        )

                        st.download_button(
                            label="📄 Descargar Informe en PDF",
                            data=pdf_bytes,
                            file_name=nombre_pdf,
                            mime="application/pdf",
                            key=f"pdf_{informe_id}"
                        )

                    except Exception as error_pdf:

                        st.error(
                            "No se pudo generar "
                            f"el PDF: {error_pdf}"
                        )
