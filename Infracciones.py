import streamlit as st
import pandas as pd
import os
import re
from datetime import date
from fpdf import FPDF
from supabase import create_client, Client

# ==============================
# SUPABASE
# ==============================
SUPABASE_URL = "https://zwchdpugmqturznuxntc.supabase.co"

# Usa la misma clave que ya tenías en tu código.
# Recomendado: guardarla en Streamlit Secrets como SUPABASE_KEY.
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

if not SUPABASE_KEY:
    st.error("Falta SUPABASE_KEY en los Secrets de Streamlit.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

TABLA = "infracciones"
BUCKET = "evidencias"
CHOFERES_EXTRAS_FILE = "choferes_extras.txt"

USUARIO_ADMIN = "Asistentes de maniobra"
PASSWORD_ADMIN = "Seguridad2026"


# ==============================
# FUNCIONES
# ==============================
@st.cache_data(ttl=60)
def consultar_infracciones():
    try:
        r = (supabase.table(TABLA)
             .select("id,fecha,operario,faltas,observaciones,sancion,foto_path,grupo_lista")
             .order("id", desc=True).execute())
        return r.data or []
    except Exception as e:
        st.error(f"Error de conexión con la base de datos: {e}")
        return []


def cargar_lista_txt(ruta, defecto):
    if os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            return [x.strip() for x in f if x.strip()]
    return defecto


def guardar_chofer_extra(nombre):
    with open(CHOFERES_EXTRAS_FILE, "a", encoding="utf-8") as f:
        f.write(nombre + "\n")


def limpiar_nombre(texto):
    texto = str(texto).strip().replace(" ", "_")
    return re.sub(r"[^A-Za-z0-9_\-]", "", texto) or "operario"


def obtener_url_foto(valor):
    if not valor:
        return None
    valor = str(valor).strip()
    if valor.startswith(("http://", "https://")):
        return valor
    try:
        r = supabase.storage.from_(BUCKET).get_public_url(valor)
        if isinstance(r, str):
            return r
        return (r.get("publicUrl") or r.get("public_url")
                or r.get("data", {}).get("publicUrl")
                or r.get("data", {}).get("public_url"))
    except Exception:
        return None


def subir_foto(archivo, operario, fecha):
    if archivo is None:
        return None

    ext = os.path.splitext(archivo.name)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png"]:
        raise ValueError("La evidencia debe ser JPG, JPEG o PNG.")

    nombre = f"{str(fecha).replace('-', '')}_{limpiar_nombre(operario)}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S_%f')}{ext}"
    ruta = f"informes/{nombre}"
    mime = "image/png" if ext == ".png" else "image/jpeg"

    supabase.storage.from_(BUCKET).upload(
        ruta, archivo.getvalue(),
        file_options={"content-type": mime, "cache-control": "3600", "upsert": "false"}
    )
    url = obtener_url_foto(ruta)
    if not url:
        raise RuntimeError("La foto se subió, pero no se pudo obtener su URL.")
    return url


def pdf_texto(valor):
    return str(valor or "").encode("latin-1", errors="replace").decode("latin-1")


def generar_pdf(row):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, pdf_texto("Reporte de Incumplimiento de Seguridad e Higiene"),
             ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", "", 12)
    pdf.cell(200, 10, pdf_texto(f"Fecha del Registro: {row.get('fecha', 'N/A')}"), ln=True)
    pdf.cell(200, 10, pdf_texto(f"Conductor/Operario: {row.get('operario', 'N/A')}"), ln=True)
    pdf.cell(200, 10, pdf_texto(f"Lista de Origen: {row.get('grupo_lista', 'N/A')}"), ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, pdf_texto("Desvios Detectados:"), ln=True)
    pdf.set_font("Arial", "", 12)

    faltas = str(row.get("faltas", "") or "")
    for falta in re.split(r"[\n,;]+", faltas):
        if falta.strip():
            pdf.cell(200, 8, pdf_texto(f"- {falta.strip()}"), ln=True)

    pdf.ln(5)
    obs = str(row.get("observaciones", "") or "")
    if obs:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 10, pdf_texto("Observaciones:"), ln=True)
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, 10, pdf_texto(obs))
        pdf.ln(3)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, pdf_texto("Sancion / Observaciones:"), ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 10, pdf_texto(
        row.get("sancion", "") or "Sin observaciones registradas."
    ))

    # FPDF puede devolver bytearray; bytes() corrige el error de encode.
    return bytes(pdf.output(dest="S"))


# ==============================
# LISTAS
# ==============================
LISTA_T1 = cargar_lista_txt("choferes_t1.txt", [])
LISTA_T2 = cargar_lista_txt("choferes_t2.txt", [])
LISTA_T2_CATAMARCA = cargar_lista_txt("choferes_t2_catamarca.txt", [])
LISTA_T2_LARIOJA = cargar_lista_txt("choferes_t2_larioja.txt", [])
LISTA_T2_SANTIAGO = cargar_lista_txt("choferes_t2_santiago.txt", [])


# ==============================
# STREAMLIT / LOGIN
# ==============================
st.set_page_config(page_title="Control de Seguridad Industrial", layout="wide")

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False


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


if not st.session_state["autenticado"]:
    login()
    st.stop()

st.sidebar.title("Navegación")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

st.title("Sistema de Gestión de Seguridad e Higiene")
st.caption("Registro permanente de informes y evidencias fotográficas.")

# ==============================
# ALERTA DE REINCIDENCIA
# ==============================
datos = consultar_infracciones()
if datos:
    df = pd.DataFrame(datos)
    if not df.empty and "operario" in df.columns:
        reincidentes = df["operario"].value_counts()
        reincidentes = reincidentes[reincidentes >= 3]
        if not reincidentes.empty:
            with st.container(border=True):
                st.error("⚠️ ALERTA DE SEGURIDAD: CONTROL DE REINCIDENCIA CRÍTICA")
                for chofer, total in reincidentes.items():
                    st.markdown(f"* El conductor **{chofer}** ha acumulado **{total} informes**.")

tab_reg, tab_hist = st.tabs(["Registro de Incidencias", "Historial de Informes"])

# ==============================
# REGISTRO
# ==============================
with tab_reg:
    st.subheader("Formulario de Registro")

    opcion = st.radio("Seleccione el grupo de personal:", [
        "Choferes de T1", "Choferes de T2", "Choferes de T2 Catamarca",
        "Choferes de T2 La Rioja", "Choferes de T2 Santiago Del Estero",
        "Cargar nombres apartes"
    ])

    operario = ""
    grupo = ""

    if opcion == "Choferes de T1":
        operario = st.selectbox("Personal de T1 Involucrado", LISTA_T1)
        grupo = "T1"
    elif opcion == "Choferes de T2":
        operario = st.selectbox("Personal de T2 Involucrado", LISTA_T2)
        grupo = "T2"
    elif opcion == "Choferes de T2 Catamarca":
        operario = st.selectbox("Choferes de T2 Catamarca", LISTA_T2_CATAMARCA)
        grupo = "T2 Catamarca"
    elif opcion == "Choferes de T2 La Rioja":
        operario = st.selectbox("Choferes de T2 La Rioja", LISTA_T2_LARIOJA)
        grupo = "T2 La Rioja"
    elif opcion == "Choferes de T2 Santiago Del Estero":
        operario = st.selectbox("Choferes de T2 Santiago Del Estero", LISTA_T2_SANTIAGO)
        grupo = "T2 Santiago Del Estero"
    else:
        st.info("Módulo para registrar choferes fuera de T1/T2.")
        grupo = "Carga Aparte / Extra"
        with st.expander("➕ Registrar nuevo chofer"):
            nuevo = st.text_input("Nombre completo del nuevo chofer")
            if st.button("Guardar nombre en el sistema"):
                if nuevo.strip():
                    guardar_chofer_extra(nuevo.strip())
                    st.success(f"{nuevo} agregado con éxito.")
                    st.rerun()
                else:
                    st.error("El nombre no puede estar vacío.")

        extras = cargar_lista_txt(CHOFERES_EXTRAS_FILE, [])
        if extras:
            operario = st.selectbox("Seleccione el chofer", extras)
        else:
            st.warning("No hay choferes cargados.")

    st.write("---")
    st.markdown(f"**Conductor:** {operario} | **Lista de Origen:** {grupo}")

    faltas = st.multiselect("Tipos de Incumplimiento", [
        "No utiliza Cuñas/Calzas", "Situacion de riesgo", "Falta de E.P.P",
        "Uso del celular", "Comportamiento indebido", "No cumple con el punto seguro",
        "Estaciona en zona prohibida", "No posee alarma de retroceso",
        "Exceso de velocidad", "Interaccion Hombre-Maquina",
        "No espera a ser asistido en la Maniobra de reversa"
    ])

    observaciones = st.text_area("Observaciones")
    sancion = st.text_area("Sanción aplicada / Detalles de la medida")
    fecha = st.date_input("Fecha del Evento", date.today())
    foto = st.file_uploader("Adjuntar Evidencia Fotográfica", type=["jpg", "jpeg", "png"])

    if st.button("Guardar Informe"):
        if not operario:
            st.error("Por favor, seleccione un operario/chofer válido.")
        elif not faltas:
            st.error("Debe seleccionar al menos un tipo de incumplimiento.")
        else:
            try:
                foto_url = subir_foto(foto, operario, fecha) if foto else None
                datos_informe = {
                    "fecha": str(fecha),
                    "operario": operario,
                    "faltas": "\n".join(faltas),
                    "observaciones": observaciones,
                    "sancion": sancion,
                    "foto_path": foto_url,
                    "grupo_lista": grupo
                }
                supabase.table(TABLA).insert(datos_informe).execute()
                st.success("¡Informe registrado exitosamente!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar el informe: {e}")

# ==============================
# HISTORIAL
# ==============================
with tab_hist:
    st.subheader("Historial de Registros")

    datos_hist = consultar_infracciones()
    if not datos_hist:
        st.info("Todavía no hay informes registrados.")
    else:
        dfh = pd.DataFrame(datos_hist)
        grupos = ["Mostrar Todos"] + [
            x for x in dfh["grupo_lista"].dropna().astype(str).unique()
        ] if "grupo_lista" in dfh.columns else ["Mostrar Todos"]

        filtro = st.selectbox("Filtrar por grupo", grupos)
        if filtro != "Mostrar Todos":
            dfh = dfh[dfh["grupo_lista"].astype(str) == filtro]

        for _, row in dfh.iterrows():
            rid = row.get("id", "N/A")
            op = row.get("operario", "N/A")
            fec = row.get("fecha", "N/A")

            with st.expander(f"📄 Informe #{rid} - {op} - {fec}"):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown(f"**Fecha:** {fec}")
                    st.markdown(f"**Operario:** {op}")
                    st.markdown(f"**Grupo:** {row.get('grupo_lista', 'N/A')}")
                    st.markdown("**Incumplimientos:**")
                    for falta in re.split(r"[\n,;]+", str(row.get("faltas", ""))):
                        if falta.strip():
                            st.markdown(f"• {falta.strip()}")

                    if row.get("observaciones"):
                        st.markdown("**Observaciones:**")
                        st.write(row.get("observaciones"))

                    st.markdown("**Sanción / Observaciones:**")
                    st.write(row.get("sancion") or "Sin observaciones registradas.")

                with col2:
                    url = obtener_url_foto(row.get("foto_path"))
                    if url:
                        st.image(url, caption="Evidencia fotográfica", use_container_width=True)
                    else:
                        st.caption("Sin evidencia fotográfica")

                try:
                    pdf = generar_pdf(row.to_dict())
                    st.download_button(
                        "📥 Descargar Informe PDF",
                        data=pdf,
                        file_name=f"Informe_{rid}.pdf",
                        mime="application/pdf",
                        key=f"pdf_{rid}"
                    )
                except Exception as e:
                    st.error(f"No se pudo generar el PDF: {e}")
