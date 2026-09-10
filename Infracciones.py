import streamlit as st
import pandas as pd
import os
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
# CONFIGURACIÓN GENERAL
# ============================================================

USUARIO_ADMIN = "Asistentes de maniobra"
PASSWORD_ADMIN = "Seguridad2026"

CHOFERES_EXTRAS_FILE = "choferes_extras.txt"

# Nombre del bucket de Supabase Storage
STORAGE_BUCKET = "evidencias"


# ============================================================
# CONFIGURACIÓN DE LA PÁGINA
# ============================================================

st.set_page_config(
    page_title="Control de Seguridad Industrial",
    layout="wide"
)


# ============================================================
# ESTADO DE SESIÓN
# ============================================================

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False


# ============================================================
# FUNCIONES
# ============================================================

@st.cache_data(ttl=300)
def consultar_infracciones_cache():

    try:

        response = (
            supabase
            .table("Infracciones")
            .select("*")
            .order("id", desc=True)
            .execute()
        )

        return response.data

    except Exception as e:

        st.error(
            f"Error de conexión con la base de datos: {e}"
        )

        return []


# ------------------------------------------------------------
# CARGAR LISTAS TXT
# ------------------------------------------------------------

def cargar_lista_txt(ruta_archivo, nombres_defecto):

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

    except Exception as e:

        st.warning(
            f"No se pudo leer {ruta_archivo}: {e}"
        )

    return nombres_defecto


# ------------------------------------------------------------
# GUARDAR CHOFER EXTRA
# ------------------------------------------------------------

def guardar_chofer_extra(nombre):

    try:

        with open(
            CHOFERES_EXTRAS_FILE,
            "a",
            encoding="utf-8"
        ) as f:

            f.write(nombre + "\n")

        return True

    except Exception as e:

        st.error(
            f"No se pudo guardar el chofer: {e}"
        )

        return False


# ------------------------------------------------------------
# LIMPIAR NOMBRE PARA ARCHIVO
# ------------------------------------------------------------

def limpiar_nombre_archivo(texto):

    texto = str(texto).strip()

    # Reemplazar espacios
    texto = texto.replace(" ", "_")

    # Eliminar caracteres problemáticos
    texto = re.sub(
        r"[^A-Za-z0-9_\-]",
        "",
        texto
    )

    # Evitar nombre vacío
    if not texto:
        texto = "sin_nombre"

    return texto


# ------------------------------------------------------------
# COMPRIMIR FOTO
# ------------------------------------------------------------

def comprimir_fotografia(archivo):

    try:

        imagen = Image.open(archivo)

        # Convertir a RGB para poder guardar como JPEG
        if imagen.mode != "RGB":
            imagen = imagen.convert("RGB")

        # Reducir tamaño máximo.
        # Esto ayuda muchísimo a ahorrar espacio en Supabase.
        max_ancho = 1600
        max_alto = 1600

        imagen.thumbnail(
            (max_ancho, max_alto),
            Image.Resampling.LANCZOS
        )

        buffer = io.BytesIO()

        imagen.save(
            buffer,
            format="JPEG",
            quality=75,
            optimize=True
        )

        buffer.seek(0)

        return buffer.getvalue()

    except Exception as e:

        st.error(
            f"No se pudo procesar la fotografía: {e}"
        )

        return None


# ------------------------------------------------------------
# SUBIR FOTO A SUPABASE STORAGE
# ------------------------------------------------------------

def subir_fotografia_supabase(
    archivo,
    operario,
    fecha_evento
):

    if archivo is None:
        return None

    try:

        # Comprimir
        contenido = comprimir_fotografia(archivo)

        if contenido is None:
            return None

        nombre_limpio = limpiar_nombre_archivo(
            operario
        )

        fecha_archivo = str(
            fecha_evento
        ).replace("-", "")

        # Fecha y hora únicas
        identificador = datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        nombre_archivo = (
            f"{fecha_archivo}_"
            f"{nombre_limpio}_"
            f"{identificador}.jpg"
        )

        ruta_storage = (
            f"informes/{nombre_archivo}"
        )

        # Subir archivo
        supabase.storage.from_(
            STORAGE_BUCKET
        ).upload(
            ruta_storage,
            contenido,
            {
                "content-type": "image/jpeg",
                "upsert": "false"
            }
        )

        # Obtener URL pública
        url_publica = (
            supabase
            .storage
            .from_(STORAGE_BUCKET)
            .get_public_url(ruta_storage)
        )

        return {
            "ruta": ruta_storage,
            "url": url_publica
        }

    except Exception as e:

        st.error(
            "No se pudo subir la fotografía a "
            f"Supabase Storage: {e}"
        )

        return None


# ------------------------------------------------------------
# ELIMINAR FOTO DE SUPABASE STORAGE
# ------------------------------------------------------------

def eliminar_fotografia_supabase(ruta):

    if not ruta:
        return

    try:

        supabase.storage.from_(
            STORAGE_BUCKET
        ).remove([ruta])

    except Exception:
        pass


# ------------------------------------------------------------
# OBTENER VALOR DE COLUMNA
# ------------------------------------------------------------

def obtener_valor(row, *nombres):

    for nombre in nombres:

        if nombre in row:

            valor = row.get(nombre)

            if valor is not None:

                return valor

    return ""


# ------------------------------------------------------------
# GENERAR PDF
# ------------------------------------------------------------

def generar_pdf_informe(row):

    pdf = FPDF()

    pdf.add_page()

    pdf.set_auto_page_break(
        auto=True,
        margin=15
    )

    # --------------------------------------------------------
    # TÍTULO
    # --------------------------------------------------------

    pdf.set_font(
        "Arial",
        "B",
        16
    )

    pdf.cell(
        0,
        10,
        "Reporte de Incumplimiento de Seguridad e Higiene",
        ln=True,
        align="C"
    )

    pdf.ln(8)

    # --------------------------------------------------------
    # DATOS
    # --------------------------------------------------------

    fecha = obtener_valor(
        row,
        "Fecha",
        "fecha"
    )

    operario = obtener_valor(
        row,
        "Operario",
        "operario"
    )

    grupo = obtener_valor(
        row,
        "grupo_lista",
        "Grupo_lista"
    )

    creado = obtener_valor(
        row,
        "created_at",
        "Created_at"
    )

    sancion = obtener_valor(
        row,
        "Sancion",
        "sancion"
    )

    descripcion = obtener_valor(
        row,
        "Descripcion",
        "descripcion"
    )

    pdf.set_font(
        "Arial",
        "",
        11
    )

    pdf.cell(
        0,
        8,
        f"Fecha del evento: {fecha}",
        ln=True
    )

    pdf.cell(
        0,
        8,
        f"Conductor / Operario: {operario}",
        ln=True
    )

    pdf.cell(
        0,
        8,
        f"Lista de origen: {grupo}",
        ln=True
    )

    if creado:

        pdf.cell(
            0,
            8,
            f"Fecha y hora de carga: {creado}",
            ln=True
        )

    pdf.ln(5)

    # --------------------------------------------------------
    # DESVÍOS / FALTAS
    # --------------------------------------------------------

    pdf.set_font(
        "Arial",
        "B",
        12
    )

    pdf.cell(
        0,
        8,
        "Desvios Detectados:",
        ln=True
    )

    pdf.set_font(
        "Arial",
        "",
        11
    )

    faltas_data = obtener_valor(
        row,
        "Faltas",
        "faltas"
    )

    if isinstance(faltas_data, list):

        for falta in faltas_data:

            pdf.multi_cell(
                0,
                7,
                f"- {falta}"
            )

    else:

        texto_faltas = str(
            faltas_data
        )

        # Si Supabase devuelve una lista como texto
        texto_faltas = texto_faltas.replace(
            "[",
            ""
        ).replace(
            "]",
            ""
        ).replace(
            "'",
            ""
        )

        pdf.multi_cell(
            0,
            7,
            f"- {texto_faltas}"
        )

    pdf.ln(5)

    # --------------------------------------------------------
    # SANCIÓN
    # --------------------------------------------------------

    pdf.set_font(
        "Arial",
        "B",
        12
    )

    pdf.cell(
        0,
        8,
        "Sancion / Observaciones:",
        ln=True
    )

    pdf.set_font(
        "Arial",
        "",
        11
    )

    if sancion:

        pdf.multi_cell(
            0,
            7,
            str(sancion)
        )

    else:

        pdf.multi_cell(
            0,
            7,
            "Sin observaciones registradas."
        )

    # --------------------------------------------------------
    # DESCRIPCIÓN
    # --------------------------------------------------------

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
            "Descripcion de los Hechos:",
            ln=True
        )

        pdf.set_font(
            "Arial",
            "",
            11
        )

        pdf.multi_cell(
            0,
            7,
            str(descripcion)
        )

    # --------------------------------------------------------
    # SALIDA
    # --------------------------------------------------------

    return pdf.output(
        dest="S"
    ).encode(
        "latin-1",
        errors="ignore"
    )


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
# LOGIN
# ============================================================

def login():

    st.title(
        "Acceso al Sistema de Seguridad"
    )

    st.write(
        "Ingrese sus credenciales para continuar."
    )

    user = st.text_input(
        "Usuario"
    )

    password = st.text_input(
        "Contraseña",
        type="password"
    )

    if st.button(
        "Ingresar",
        use_container_width=True
    ):

        if (
            user == USUARIO_ADMIN
            and
            password == PASSWORD_ADMIN
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
# APLICACIÓN PRINCIPAL
# ============================================================

if not st.session_state["autenticado"]:

    login()

else:

    # ========================================================
    # SIDEBAR
    # ========================================================

    st.sidebar.title(
        "Navegación"
    )

    st.sidebar.success(
        "Sistema autenticado"
    )

    if st.sidebar.button(
        "Cerrar Sesión",
        use_container_width=True
    ):

        st.session_state[
            "autenticado"
        ] = False

        st.rerun()

    # ========================================================
    # TÍTULO
    # ========================================================

    st.title(
        "Sistema de Gestión de Seguridad e Higiene"
    )

    st.caption(
        "Registro permanente de informes y evidencias fotográficas."
    )

    # ========================================================
    # PANEL DE ALERTAS
    # ========================================================

    datos_alertas = (
        consultar_infracciones_cache()
    )

    if datos_alertas:

        df_alertas = pd.DataFrame(
            datos_alertas
        )

        col_op = None

        if "Operario" in df_alertas.columns:

            col_op = "Operario"

        elif "operario" in df_alertas.columns:

            col_op = "operario"

        if (
            not df_alertas.empty
            and
            col_op
        ):

            conteo_faltas = (
                df_alertas[
                    col_op
                ].value_counts()
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

    tab_reg, tab_hist = st.tabs(
        [
            "Registro de Incidencias",
            "Historial de Informes"
        ]
    )


    # ========================================================
    # REGISTRO DE INCIDENCIAS
    # ========================================================

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
                    "No se encontraron choferes de T1."
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
                    "No se encontraron choferes de T2."
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
                    "No se encontraron choferes de T2 Catamarca."
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
                    "No se encontraron choferes de T2 La Rioja."
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
                    "No se encontraron choferes de T2 Santiago Del Estero."
                )


        # ----------------------------------------------------
        # CHOFERES EXTRAS
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

                    if nuevo_nombre.strip() != "":

                        if guardar_chofer_extra(
                            nuevo_nombre.strip()
                        ):

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


        # ----------------------------------------------------
        # DATOS DEL OPERARIO
        # ----------------------------------------------------

        st.write("---")

        st.markdown(
            f"**Conductor:** {operario}  \n"
            f"**Lista de Origen:** {grupo_pertenencia}"
        )


        # ====================================================
        # FALTAS
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
                "Interaccion Hombre-Maquina",
                "Exceso de velocidad"
            ]
        )


        # ====================================================
        # DESCRIPCIÓN
        # ====================================================

        descripcion_input = st.text_area(
            "Descripción Técnica de los Hechos",
            height=120
        )


        # ====================================================
        # SANCIÓN
        # ====================================================

        sancion_input = st.text_area(
            "Sanción aplicada / Detalles de la medida",
            height=100
        )


        # ====================================================
        # FECHA
        # ====================================================

        fecha_registro = st.date_input(
            "Fecha del Evento",
            date.today()
        )


        # ====================================================
        # FOTO
        # ====================================================

        foto = st.file_uploader(
            "Adjuntar Evidencia Fotográfica",
            type=[
                "jpg",
                "jpeg",
                "png"
            ],
            help=(
                "La fotografía será comprimida automáticamente "
                "antes de almacenarse para ahorrar espacio."
            )
        )


        if foto:

            st.image(
                foto,
                caption="Vista previa de la evidencia",
                use_container_width=True
            )


        # ====================================================
        # GUARDAR INFORME
        # ====================================================

        if st.button(
            "💾 Guardar Informe",
            use_container_width=True
        ):

            if not operario:

                st.error(
                    "Por favor, seleccione un operario/chofer válido."
                )

            elif not faltas:

                st.error(
                    "Debe seleccionar al menos un tipo "
                    "de incumplimiento."
                )

            else:

                with st.spinner(
                    "Guardando informe..."
                ):

                    foto_info = None

                    # ------------------------------------------------
                    # SUBIR FOTO
                    # ------------------------------------------------

                    if foto:

                        foto_info = (
                            subir_fotografia_supabase(
                                foto,
                                operario,
                                fecha_registro
                            )
                        )

                        if foto_info is None:

                            st.error(
                                "El informe no se guardó porque "
                                "la fotografía no pudo almacenarse."
                            )

                            st.stop()


                    # ------------------------------------------------
                    # FECHA Y HORA
                    # ------------------------------------------------

                    fecha_hora_actual = (
                        datetime.now().isoformat()
                    )


                    # ------------------------------------------------
                    # DATOS
                    # ------------------------------------------------

                    datos_informe = {

                        "Operario": operario,

                        "grupo_lista": (
                            grupo_pertenencia
                        ),

                        "Faltas": faltas,

                        "Descripcion": (
                            descripcion_input
                        ),

                        "Sancion": (
                            sancion_input
                        ),

                        "Fecha": (
                            str(fecha_registro)
                        ),

                        "created_at": (
                            fecha_hora_actual
                        )
                    }


                    # ------------------------------------------------
                    # DATOS DE FOTO
                    # ------------------------------------------------

                    if foto_info:

                        datos_informe[
                            "foto_path"
                        ] = foto_info["ruta"]

                        datos_informe[
                            "foto_url"
                        ] = foto_info["url"]


                    # ------------------------------------------------
                    # INSERTAR EN SUPABASE
                    # ------------------------------------------------

                    try:

                        (
                            supabase
                            .table("Infracciones")
                            .insert(datos_informe)
                            .execute()
                        )

                        st.cache_data.clear()

                        st.success(
                            "✅ ¡Informe registrado exitosamente!"
                        )

                        st.info(
                            "El informe y la evidencia "
                            "quedaron almacenados en Supabase."
                        )

                        st.rerun()


                    except Exception as error_db:

                        # Si falla la base de datos,
                        # intentar eliminar la foto que ya se subió
                        if foto_info:

                            eliminar_fotografia_supabase(
                                foto_info["ruta"]
                            )

                        st.error(
                            "Error al guardar en la base de datos:"
                        )

                        st.code(
                            str(error_db)
                        )


    # ========================================================
    # HISTORIAL
    # ========================================================

    with tab_hist:

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
            # IDENTIFICAR COLUMNAS
            # ------------------------------------------------

            col_id = None

            if "id" in df_historial.columns:

                col_id = "id"

            elif "Id" in df_historial.columns:

                col_id = "Id"


            col_creado = None

            if "created_at" in df_historial.columns:

                col_creado = "created_at"

            elif "Created_at" in df_historial.columns:

                col_creado = "Created_at"


            col_grupo = None

            if "grupo_lista" in df_historial.columns:

                col_grupo = "grupo_lista"

            elif "Grupo_lista" in df_historial.columns:

                col_grupo = "Grupo_lista"


            col_operario = None

            if "Operario" in df_historial.columns:

                col_operario = "Operario"

            elif "operario" in df_historial.columns:

                col_operario = "operario"


            # ------------------------------------------------
            # FILTRO DE GRUPO
            # ------------------------------------------------

            opciones_filtro = [
                "Mostrar Todos",
                "T1",
                "T2",
                "T2 Catamarca",
                "T2 La Rioja",
                "T2 Santiago Del Estero",
                "Carga Aparte / Extra"
            ]

            filtro_grupo = st.selectbox(
                "Filtrar historial por grupo",
                opciones_filtro
            )


            df_mostrar = (
                df_historial.copy()
            )


            if (
                filtro_grupo != "Mostrar Todos"
                and
                col_grupo
            ):

                df_mostrar = (
                    df_mostrar[
                        df_mostrar[
                            col_grupo
                        ].astype(str)
                        == filtro_grupo
                    ]
                )


            # ------------------------------------------------
            # ORDENAR
            # ------------------------------------------------

            if col_creado:

                try:

                    df_mostrar = (
                        df_mostrar
                        .sort_values(
                            by=col_creado,
                            ascending=False
                        )
                    )

                except Exception:

                    pass


            # ------------------------------------------------
            # CONTADOR
            # ------------------------------------------------

            st.write(
                f"**Informes encontrados: {len(df_mostrar)}**"
            )


            # ------------------------------------------------
            # MOSTRAR INFORMES
            # ------------------------------------------------

            for indice, row in df_mostrar.iterrows():

                if col_id:

                    identificador = row.get(
                        col_id
                    )

                else:

                    identificador = indice


                operario_hist = obtener_valor(
                    row,
                    "Operario",
                    "operario"
                )

                fecha_hist = obtener_valor(
                    row,
                    "Fecha",
                    "fecha"
                )

                grupo_hist = obtener_valor(
                    row,
                    "grupo_lista",
                    "Grupo_lista"
                )

                faltas_hist = obtener_valor(
                    row,
                    "Faltas",
                    "faltas"
                )

                descripcion_hist = obtener_valor(
                    row,
                    "Descripcion",
                    "descripcion"
                )

                sancion_hist = obtener_valor(
                    row,
                    "Sancion",
                    "sancion"
                )

                foto_url_hist = obtener_valor(
                    row,
                    "foto_url",
                    "Foto_url"
                )

                foto_path_hist = obtener_valor(
                    row,
                    "foto_path",
                    "Foto_Path"
                )

                creado_hist = obtener_valor(
                    row,
                    "created_at",
                    "Created_at"
                )


                # ------------------------------------------------
                # EXPANDER
                # ------------------------------------------------

                titulo = (
                    f"📋 {fecha_hist} | "
                    f"{operario_hist}"
                )

                with st.expander(
                    titulo
                ):

                    col1, col2 = st.columns(
                        [2, 1]
                    )


                    # --------------------------------------------
                    # INFORMACIÓN
                    # --------------------------------------------

                    with col1:

                        st.markdown(
                            f"**Conductor / Operario:** "
                            f"{operario_hist}"
                        )

                        st.markdown(
                            f"**Fecha del evento:** "
                            f"{fecha_hist}"
                        )

                        st.markdown(
                            f"**Lista de origen:** "
                            f"{grupo_hist}"
                        )

                        if creado_hist:

                            st.markdown(
                                f"**Fecha y hora de carga:** "
                                f"{creado_hist}"
                            )


                        st.markdown(
                            "**Incumplimientos:**"
                        )


                        if isinstance(
                            faltas_hist,
                            list
                        ):

                            for falta in faltas_hist:

                                st.markdown(
                                    f"- {falta}"
                                )

                        else:

                            texto_faltas = str(
                                faltas_hist
                            )

                            st.markdown(
                                texto_faltas
                            )


                        if descripcion_hist:

                            st.markdown(
                                "**Descripción Técnica:**"
                            )

                            st.write(
                                descripcion_hist
                            )


                        if sancion_hist:

                            st.markdown(
                                "**Sanción / Medida:**"
                            )

                            st.write(
                                sancion_hist
                            )


                    # --------------------------------------------
                    # FOTOGRAFÍA
                    # --------------------------------------------

                    with col2:

                        if foto_url_hist:

                            try:

                                st.image(
                                    foto_url_hist,
                                    caption="Evidencia fotográfica",
                                    use_container_width=True
                                )

                            except Exception:

                                st.warning(
                                    "No se pudo mostrar la fotografía."
                                )

                        else:

                            st.info(
                                "Este informe no tiene "
                                "evidencia fotográfica."
                            )


                    st.write("---")


                    # --------------------------------------------
                    # BOTONES
                    # --------------------------------------------

                    col_pdf, col_eliminar = st.columns(
                        2
                    )


                    # --------------------------------------------
                    # PDF
                    # --------------------------------------------

                    with col_pdf:

                        try:

                            pdf_bytes = (
                                generar_pdf_informe(
                                    row
                                )
                            )

                            st.download_button(
                                label="📄 Descargar PDF",
                                data=pdf_bytes,
                                file_name=(
                                    f"Informe_{identificador}.pdf"
                                ),
                                mime="application/pdf",
                                key=(
                                    f"pdf_{identificador}"
                                ),
                                use_container_width=True
                            )

                        except Exception as e:

                            st.error(
                                f"No se pudo generar el PDF: {e}"
                            )


                    # --------------------------------------------
                    # ELIMINAR
                    # --------------------------------------------

                    with col_eliminar:

                        confirmar = st.checkbox(
                            "Confirmar eliminación",
                            key=(
                                f"confirmar_{identificador}"
                            )
                        )

                        if st.button(
                            "🗑️ Eliminar Informe",
                            key=(
                                f"eliminar_{identificador}"
                            ),
                            use_container_width=True
                        ):

                            if not confirmar:

                                st.warning(
                                    "Marque primero "
                                    "'Confirmar eliminación'."
                                )

                            else:

                                try:

                                    # ----------------------------
                                    # ELIMINAR DE BASE DE DATOS
                                    # ----------------------------

                                    if col_id:

                                        (
                                            supabase
                                            .table("Infracciones")
                                            .delete()
                                            .eq(
                                                col_id,
                                                identificador
                                            )
                                            .execute()
                                        )

                                    else:

                                        st.error(
                                            "No se encontró la columna ID."
                                        )

                                        st.stop()


                                    # ----------------------------
                                    # ELIMINAR FOTO
                                    # ----------------------------

                                    if foto_path_hist:

                                        eliminar_fotografia_supabase(
                                            foto_path_hist
                                        )


                                    st.cache_data.clear()

                                    st.success(
                                        "Informe eliminado correctamente."
                                    )

                                    st.rerun()


                                except Exception as error_eliminar:

                                    st.error(
                                        "No se pudo eliminar el informe:"
                                    )

                                    st.code(
                                        str(error_eliminar)
                                    )


# ============================================================
# FIN DEL PROGRAMA
# ============================================================
