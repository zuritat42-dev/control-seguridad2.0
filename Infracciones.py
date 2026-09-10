import streamlit as st
import pandas as pd
import os
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

# Nombre EXACTO del bucket de Supabase Storage
STORAGE_BUCKET = "evidencias"

# =====================================
# CONFIGURACIÓN DE SEGURIDAD
# =====================================

USUARIO_ADMIN = "Asistentes de maniobra"
PASSWORD_ADMIN = "Seguridad2026"

# =====================================
# ARCHIVOS LOCALES
# =====================================

CHOFERES_EXTRAS_FILE = "choferes_extras.txt"

# =====================================
# CONFIGURACIÓN STREAMLIT
# =====================================

st.set_page_config(
    page_title="Control de Seguridad Industrial",
    layout="wide"
)

# =====================================
# FUNCIONES
# =====================================

@st.cache_data(ttl=30)
def consultar_infracciones_cache():
    """
    Consulta todos los informes de la tabla infracciones.
    """

    try:
        # IMPORTANTE:
        # La tabla de Supabase se llama "infracciones"
        response = supabase.table("infracciones").select("*").execute()

        return response.data

    except Exception as e:
        st.error(
            f"Error de conexión con la base de datos: {e}"
        )
        return []


def cargar_lista_txt(ruta_archivo, nombres_defecto):
    """
    Carga nombres desde un archivo TXT.
    """

    try:
        if os.path.exists(ruta_archivo):

            with open(
                ruta_archivo,
                "r",
                encoding="utf-8"
            ) as f:

                return [
                    linea.strip()
                    for linea in f.readlines()
                    if linea.strip()
                ]

    except Exception as e:
        st.warning(
            f"No se pudo leer {ruta_archivo}: {e}"
        )

    return nombres_defecto


def guardar_chofer_extra(nombre):
    """
    Guarda un chofer adicional en el archivo local.
    """

    with open(
        CHOFERES_EXTRAS_FILE,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(nombre.strip() + "\n")


def limpiar_nombre_archivo(texto):
    """
    Limpia nombres para utilizarlos dentro
    de las rutas de Supabase Storage.
    """

    if not texto:
        return "sin_nombre"

    texto = str(texto).strip()

    # Reemplazar espacios por _
    texto = texto.replace(" ", "_")

    # Eliminar caracteres especiales
    texto = re.sub(
        r"[^A-Za-z0-9_\-]",
        "",
        texto
    )

    # Evitar nombre vacío
    if not texto:
        texto = "sin_nombre"

    return texto


def generar_pdf_informe(row):
    """
    Genera el PDF del informe.
    """

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font(
        "Arial",
        "B",
        16
    )

    pdf.cell(
        200,
        10,
        "Reporte de Incumplimiento de Seguridad e Higiene",
        ln=True,
        align="C"
    )

    pdf.ln(10)

    pdf.set_font(
        "Arial",
        "",
        12
    )

    fecha = obtener_valor_columna(
        row,
        ["Fecha", "fecha"],
        "N/A"
    )

    operario = obtener_valor_columna(
        row,
        ["Operario", "operario"],
        "N/A"
    )

    grupo = obtener_valor_columna(
        row,
        ["grupo_lista", "Grupo_lista"],
        "N/A"
    )

    pdf.cell(
        200,
        10,
        f"Fecha del Registro: {fecha}",
        ln=True
    )

    pdf.cell(
        200,
        10,
        f"Conductor/Operario: {operario}",
        ln=True
    )

    pdf.cell(
        200,
        10,
        f"Lista de Origen: {grupo}",
        ln=True
    )

    pdf.ln(5)

    # =====================================
    # FALTAS
    # =====================================

    pdf.set_font(
        "Arial",
        "B",
        12
    )

    pdf.cell(
        200,
        10,
        "Desvios Detectados:",
        ln=True
    )

    pdf.set_font(
        "Arial",
        "",
        12
    )

    faltas_data = obtener_valor_columna(
        row,
        ["Faltas", "faltas"],
        ""
    )

    if isinstance(faltas_data, list):

        for falta in faltas_data:

            pdf.cell(
                200,
                8,
                f"- {falta}",
                ln=True
            )

    else:

        texto_faltas = str(faltas_data)

        # Si vienen separadas por coma
        if "," in texto_faltas:

            partes = texto_faltas.split(",")

            for falta in partes:

                pdf.cell(
                    200,
                    8,
                    f"- {falta.strip()}",
                    ln=True
                )

        else:

            pdf.cell(
                200,
                8,
                f"- {texto_faltas}",
                ln=True
            )

    pdf.ln(5)

    # =====================================
    # SANCIÓN
    # =====================================

    pdf.set_font(
        "Arial",
        "B",
        12
    )

    pdf.cell(
        200,
        10,
        "Sancion / Observaciones:",
        ln=True
    )

    pdf.set_font(
        "Arial",
        "",
        12
    )

    sancion_data = obtener_valor_columna(
        row,
        ["Sancion", "sancion"],
        "Sin observaciones registradas."
    )

    pdf.multi_cell(
        0,
        10,
        str(sancion_data)
    )

    return pdf.output(
        dest="S"
    ).encode(
        "latin-1",
        errors="ignore"
    )


def obtener_valor_columna(
    row,
    posibles_columnas,
    valor_defecto=""
):
    """
    Busca un valor probando diferentes
    nombres de columnas.
    """

    for columna in posibles_columnas:

        if columna in row:

            valor = row[columna]

            if valor is not None:

                return valor

    return valor_defecto


def crear_ruta_foto(id_informe, operario):
    """
    Crea una ruta segura para la fotografía.

    Ejemplo:

    informes/25_Juan_Perez.jpg
    """

    nombre_limpio = limpiar_nombre_archivo(
        operario
    )

    return (
        f"informes/"
        f"{id_informe}_"
        f"{nombre_limpio}.jpg"
    )


def subir_fotografia(
    archivo,
    id_informe,
    operario
):
    """
    Sube la fotografía al bucket evidencias.
    """

    try:

        # Importamos PIL solamente cuando
        # realmente se necesita una fotografía.
        from PIL import Image
        import io

        imagen = Image.open(archivo)

        # Convertir a RGB
        if imagen.mode != "RGB":
            imagen = imagen.convert("RGB")

        # Reducir fotografías demasiado grandes
        imagen.thumbnail(
            (1600, 1600)
        )

        # Comprimir a JPG
        buffer = io.BytesIO()

        imagen.save(
            buffer,
            format="JPEG",
            quality=75,
            optimize=True
        )

        contenido = buffer.getvalue()

        # Crear ruta
        ruta = crear_ruta_foto(
            id_informe,
            operario
        )

        # Subir a Supabase Storage
        supabase.storage.from_(
            STORAGE_BUCKET
        ).upload(
            ruta,
            contenido,
            file_options={
                "content-type": "image/jpeg",
                "upsert": "true"
            }
        )

        return ruta

    except Exception as e:

        st.error(
            f"No se pudo subir la fotografía: {e}"
        )

        return None


def obtener_url_fotografia(ruta):
    """
    Obtiene la URL pública de una fotografía.
    """

    try:

        resultado = supabase.storage.from_(
            STORAGE_BUCKET
        ).get_public_url(ruta)

        return resultado

    except Exception:

        return None


def eliminar_fotografia(
    id_informe,
    operario
):
    """
    Elimina la fotografía correspondiente
    al informe.
    """

    try:

        ruta = crear_ruta_foto(
            id_informe,
            operario
        )

        supabase.storage.from_(
            STORAGE_BUCKET
        ).remove(
            [ruta]
        )

        return True

    except Exception as e:

        st.warning(
            f"No se pudo eliminar la fotografía: {e}"
        )

        return False


def guardar_informe_en_bd(datos):
    """
    Guarda el informe en Supabase.

    Primero intenta con los nombres de columnas
    originales del programa.

    Si la tabla utiliza nombres en minúscula,
    intenta automáticamente con la versión
    en minúscula.
    """

    errores = []

    # =====================================
    # PRIMER INTENTO
    # Columnas originales
    # =====================================

    datos_mayusculas = {
        "Operario": datos["operario"],
        "grupo_lista": datos["grupo_lista"],
        "Faltas": datos["faltas"],
        "Sancion": datos["sancion"],
        "Fecha": datos["fecha"]
    }

    try:

        respuesta = supabase.table(
            "infracciones"
        ).insert(
            datos_mayusculas
        ).execute()

        if respuesta.data:
            return respuesta.data[0]

    except Exception as e:

        errores.append(str(e))

    # =====================================
    # SEGUNDO INTENTO
    # Columnas minúsculas
    # =====================================

    datos_minusculas = {
        "operario": datos["operario"],
        "grupo_lista": datos["grupo_lista"],
        "faltas": datos["faltas"],
        "sancion": datos["sancion"],
        "fecha": datos["fecha"]
    }

    try:

        respuesta = supabase.table(
            "infracciones"
        ).insert(
            datos_minusculas
        ).execute()

        if respuesta.data:
            return respuesta.data[0]

    except Exception as e:

        errores.append(str(e))

    # Si llegamos acá, ninguno funcionó
    raise Exception(
        "No se pudo guardar el informe.\n\n"
        + "\n".join(errores)
    )


# =====================================
# CARGA DE LISTAS
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
# SESIÓN
# =====================================

if "autenticado" not in st.session_state:

    st.session_state["autenticado"] = False


# =====================================
# LOGIN
# =====================================

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

    if st.button("Ingresar"):

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


# =====================================
# APLICACIÓN PRINCIPAL
# =====================================

if not st.session_state["autenticado"]:

    login()

else:

    # =====================================
    # SIDEBAR
    # =====================================

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

    # =====================================
    # TÍTULO
    # =====================================

    st.title(
        "Sistema de Gestión de Seguridad e Higiene"
    )

    st.caption(
        "Registro permanente de informes y evidencias fotográficas."
    )

    # =====================================
    # CONSULTAR DATOS
    # =====================================

    datos_alertas = consultar_infracciones_cache()

    # =====================================
    # PANEL DE ALERTAS
    # =====================================

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

    # =====================================
    # PESTAÑAS
    # =====================================

    tab_registro, tab_historial = st.tabs(
        [
            "Registro de Incidencias",
            "Historial de Informes"
        ]
    )

    # =====================================
    # REGISTRO
    # =====================================

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

        # =====================================
        # T1
        # =====================================

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
                    "en choferes_t1.txt"
                )

        # =====================================
        # T2
        # =====================================

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
                    "en choferes_t2.txt"
                )

        # =====================================
        # T2 CATAMARCA
        # =====================================

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
                    "en choferes_t2_catamarca.txt"
                )

        # =====================================
        # T2 LA RIOJA
        # =====================================

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
                    "en choferes_t2_larioja.txt"
                )

        # =====================================
        # T2 SANTIAGO
        # =====================================

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
                    "en choferes_t2_santiago.txt"
                )

        # =====================================
        # EXTRAS
        # =====================================

        elif opcion_seleccionada == "Cargar nombres apartes":

            st.info(
                "Módulo para registrar choferes "
                "fuera de las listas T1/T2."
            )

            grupo_pertenencia = (
                "Carga Aparte / Extra"
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
                            f"{nuevo_nombre} "
                            "agregado con éxito."
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
        # INFORMACIÓN DEL OPERARIO
        # =====================================

        st.write("---")

        st.markdown(
            f"**Conductor:** {operario}  \n"
            f"**Lista de Origen:** {grupo_pertenencia}"
        )

        # =====================================
        # TIPOS DE INCUMPLIMIENTO
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
                "Estaciona en zona prohibida",
                "No posee alarma de retroceso",
                "No espera a ser asistido en la Maniobra de reversa",
                "Exceso de velocidad",
                "Interaccion Hombre-Maquina"
            ]
        )

        # =====================================
        # SANCIÓN
        # =====================================

        sancion_input = st.text_area(
            "Sanción aplicada / Detalles de la medida"
        )

        # =====================================
        # FECHA
        # =====================================

        fecha_registro = st.date_input(
            "Fecha del Evento",
            date.today()
        )

        # =====================================
        # FOTOGRAFÍA
        # =====================================

        st.write("---")

        st.subheader(
            "Evidencia Fotográfica"
        )

        fotografia = st.file_uploader(
            "Adjuntar fotografía del incidente",
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

        # =====================================
        # GUARDAR INFORME
        # =====================================

        if st.button(
            "💾 Guardar Informe",
            type="primary"
        ):

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

                datos = {

                    "operario": operario,

                    "grupo_lista": grupo_pertenencia,

                    "faltas": faltas,

                    "sancion": sancion_input,

                    "fecha": str(
                        fecha_registro
                    )
                }

                try:

                    # =====================================
                    # GUARDAR INFORME
                    # =====================================

                    registro_creado = (
                        guardar_informe_en_bd(
                            datos
                        )
                    )

                    # Obtener ID
                    id_informe = obtener_valor_columna(
                        registro_creado,
                        ["id", "ID", "Id"],
                        None
                    )

                    # =====================================
                    # SUBIR FOTO
                    # =====================================

                    foto_guardada = False

                    if (
                        fotografia
                        and id_informe is not None
                    ):

                        ruta_foto = subir_fotografia(
                            fotografia,
                            id_informe,
                            operario
                        )

                        if ruta_foto:

                            foto_guardada = True

                    # =====================================
                    # MENSAJE FINAL
                    # =====================================

                    if fotografia:

                        if foto_guardada:

                            st.success(
                                "✅ Informe y fotografía "
                                "guardados correctamente."
                            )

                        else:

                            st.warning(
                                "⚠️ El informe fue guardado, "
                                "pero la fotografía no pudo "
                                "subirse."
                            )

                    else:

                        st.success(
                            "✅ Informe registrado "
                            "exitosamente."
                        )

                    # Limpiar caché
                    st.cache_data.clear()

                    st.rerun()

                except Exception as error_db:

                    st.error(
                        "❌ Error al guardar el informe "
                        f"en la base de datos:\n\n"
                        f"{error_db}"
                    )

    # =====================================
    # HISTORIAL
    # =====================================

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

            # =====================================
            # IDENTIFICAR COLUMNAS
            # =====================================

            col_id = None

            if "id" in df_historial.columns:
                col_id = "id"

            elif "ID" in df_historial.columns:
                col_id = "ID"

            elif "Id" in df_historial.columns:
                col_id = "Id"

            col_operario = None

            if "Operario" in df_historial.columns:
                col_operario = "Operario"

            elif "operario" in df_historial.columns:
                col_operario = "operario"

            col_grupo = None

            if "grupo_lista" in df_historial.columns:
                col_grupo = "grupo_lista"

            elif "Grupo_lista" in df_historial.columns:
                col_grupo = "Grupo_lista"

            # =====================================
            # FILTRO
            # =====================================

            if col_grupo:

                grupos_disponibles = sorted(
                    [
                        str(x)
                        for x in df_historial[
                            col_grupo
                        ]
                        .dropna()
                        .unique()
                    ]
                )

                filtro_grupo = st.selectbox(
                    "Filtrar por grupo:",
                    [
                        "Mostrar Todos"
                    ] + grupos_disponibles
                )

                if filtro_grupo != "Mostrar Todos":

                    df_historial = df_historial[
                        df_historial[
                            col_grupo
                        ].astype(str)
                        == filtro_grupo
                    ]

            # =====================================
            # MOSTRAR REGISTROS
            # =====================================

            if df_historial.empty:

                st.info(
                    "No hay informes para el filtro seleccionado."
                )

            else:

                # Mostrar primero los últimos
                # registros
                if col_id:

                    try:

                        df_historial = (
                            df_historial
                            .sort_values(
                                by=col_id,
                                ascending=False
                            )
                        )

                    except Exception:
                        pass

                for _, row in df_historial.iterrows():

                    id_informe = obtener_valor_columna(
                        row,
                        ["id", "ID", "Id"],
                        None
                    )

                    operario = obtener_valor_columna(
                        row,
                        ["Operario", "operario"],
                        "N/A"
                    )

                    grupo = obtener_valor_columna(
                        row,
                        ["grupo_lista", "Grupo_lista"],
                        "N/A"
                    )

                    fecha = obtener_valor_columna(
                        row,
                        ["Fecha", "fecha"],
                        "N/A"
                    )

                    faltas_data = obtener_valor_columna(
                        row,
                        ["Faltas", "faltas"],
                        ""
                    )

                    sancion = obtener_valor_columna(
                        row,
                        ["Sancion", "sancion"],
                        ""
                    )

                    # =====================================
                    # EXPANDER
                    # =====================================

                    titulo = (
                        f"📋 Informe #{id_informe} - "
                        f"{operario} - {fecha}"
                    )

                    with st.expander(titulo):

                        col1, col2 = st.columns(
                            [2, 1]
                        )

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

                            st.markdown(
                                "**Incumplimientos:**"
                            )

                            if isinstance(
                                faltas_data,
                                list
                            ):

                                for falta in faltas_data:

                                    st.write(
                                        f"• {falta}"
                                    )

                            else:

                                texto_faltas = str(
                                    faltas_data
                                )

                                if "," in texto_faltas:

                                    for falta in texto_faltas.split(","):

                                        st.write(
                                            f"• {falta.strip()}"
                                        )

                                else:

                                    st.write(
                                        f"• {texto_faltas}"
                                    )

                            st.markdown(
                                "**Sanción / Observaciones:**"
                            )

                            if sancion:

                                st.write(
                                    sancion
                                )

                            else:

                                st.write(
                                    "Sin observaciones."
                                )

                        # =====================================
                        # FOTO
                        # =====================================

                        with col2:

                            if id_informe is not None:

                                ruta_foto = crear_ruta_foto(
                                    id_informe,
                                    operario
                                )

                                url_foto = (
                                    obtener_url_fotografia(
                                        ruta_foto
                                    )
                                )

                                if url_foto:

                                    st.image(
                                        url_foto,
                                        caption="Evidencia fotográfica",
                                        use_container_width=True
                                    )

                                else:

                                    st.caption(
                                        "No hay evidencia "
                                        "fotográfica asociada."
                                    )

                        # =====================================
                        # BOTONES
                        # =====================================

                        col_pdf, col_eliminar = st.columns(
                            2
                        )

                        # =====================================
                        # PDF
                        # =====================================

                        with col_pdf:

                            try:

                                pdf_bytes = (
                                    generar_pdf_informe(
                                        row
                                    )
                                )

                                nombre_pdf = (
                                    f"Informe_{id_informe}.pdf"
                                )

                                st.download_button(
                                    label="📄 Descargar PDF",
                                    data=pdf_bytes,
                                    file_name=nombre_pdf,
                                    mime="application/pdf",
                                    key=f"pdf_{id_informe}"
                                )

                            except Exception as e:

                                st.error(
                                    f"No se pudo generar el PDF: {e}"
                                )

                        # =====================================
                        # ELIMINAR
                        # =====================================

                        with col_eliminar:

                            if st.button(
                                "🗑️ Eliminar Informe",
                                key=f"eliminar_{id_informe}"
                            ):

                                if id_informe is None:

                                    st.error(
                                        "No se encontró el ID "
                                        "del informe."
                                    )

                                else:

                                    try:

                                        # =====================================
                                        # ELIMINAR FOTO
                                        # =====================================

                                        eliminar_fotografia(
                                            id_informe,
                                            operario
                                        )

                                        # =====================================
                                        # ELIMINAR REGISTRO
                                        # =====================================

                                        # Probar primero
                                        # con id normal
                                        supabase.table(
                                            "infracciones"
                                        ).delete().eq(
                                            "id",
                                            id_informe
                                        ).execute()

                                        st.success(
                                            "Informe eliminado "
                                            "correctamente."
                                        )

                                        st.cache_data.clear()

                                        st.rerun()

                                    except Exception as e:

                                        st.error(
                                            "No se pudo eliminar "
                                            f"el informe: {e}"
                                        )
