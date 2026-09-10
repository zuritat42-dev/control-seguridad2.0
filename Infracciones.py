import io
import os
import re
from datetime import date
import pandas as pd
import requests
import streamlit as st
from fpdf import FPDF
from PIL import Image
from supabase import Client, create_client

# ============================================================
# SUPABASE Y CREDENCIALES
# ============================================================
SUPABASE_URL = "https://zwchdpugmqturznuxntc.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

if not SUPABASE_KEY:
    st.error("Falta SUPABASE_KEY en los Secrets de Streamlit.")
    st.stop()

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

TABLA = "infracciones"
BUCKET = "evidencias"
CHOFERES_EXTRAS_FILE = "choferes_extras.txt"

USUARIO_ADMIN = "Asistentes de maniobra"
PASSWORD_ADMIN = "Seguridad2026"

MAPA_LISTAS = {
    "Choferes de T1": ("T1", "choferes_t1.txt"),
    "Choferes de T2": ("T2", "choferes_t2.txt"),
    "Choferes de T2 Catamarca": ("T2 Catamarca", "choferes_t2_catamarca.txt"),
    "Choferes de T2 La Rioja": ("T2 La Rioja", "choferes_t2_larioja.txt"),
    "Choferes de T2 Santiago Del Estero": ("T2 Santiago Del Estero", "choferes_t2_santiago.txt")
}

# ============================================================
# FUNCIONES AUXILIARES DE CONSULTA Y ARCHIVOS
# ============================================================
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

@st.cache_data(ttl=300)
def cargar_lista_txt(ruta):
    if os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                return [x.strip() for x in f if x.strip()]
        except Exception:
            return []
    return []

def guardar_chofer_extra(nombre):
    with open(CHOFERES_EXTRAS_FILE, "a", encoding="utf-8") as f:
        f.write(nombre.strip() + "\n")
    cargar_lista_txt.clear()

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

# ============================================================
# PROCESAMIENTO EN MEMORIA (BytesIO) DE IMÁGENES Y PDF
# ============================================================
def subir_foto(archivo, operario, fecha):
    if archivo is None:
        return None

    ext = os.path.splitext(archivo.name)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png"]:
        raise ValueError("La evidencia debe ser JPG, JPEG o PNG.")

    # Optimización y reducción de peso de la imagen
    img = Image.open(archivo)
    if img.mode != "RGB":
        img = img.convert("RGB")
    
    img.thumbnail((1600, 1600))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=80, optimize=True)
    contenido_optimizado = buffer.getvalue()

    nombre = f"{str(fecha).replace('-', '')}_{limpiar_nombre(operario)}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    ruta = f"informes/{nombre}"

    supabase.storage.from_(BUCKET).upload(
        ruta, contenido_optimizado,
        file_options={"content-type": "image/jpeg", "cache-control": "3600", "upsert": "false"}
    )
    
    url = obtener_url_foto(ruta)
    if not url:
        raise RuntimeError("La foto se subió, pero no se pudo obtener su URL.")
    return url

def pdf_texto(valor):
    return str(valor or "").encode("latin-1", errors="replace").decode("latin-1")

def generar_pdf(row):
    """Genera el PDF en memoria solo cuando el usuario lo solicita."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)

    # Encabezado
    pdf.cell(190, 10, pdf_texto("Reporte de Incumplimiento de Seguridad e Higiene"), ln=True, align="C")
    pdf.ln(8)

    # Datos principales
    pdf.set_font("Arial", "", 11)
    pdf.cell(190, 7, pdf_texto(f"Fecha del Registro: {row.get('fecha', 'N/A')}"), ln=True)
    pdf.cell(190, 7, pdf_texto(f"Conductor/Operario: {row.get('operario', 'N/A')}"), ln=True)
    pdf.cell(190, 7, pdf_texto(f"Lista de Origen: {row.get('grupo_lista', 'N/A')}"), ln=True)
    pdf.ln(5)

    # Desvíos
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 8, pdf_texto("Desvíos Detectados:"), ln=True)
    pdf.set_font("Arial", "", 11)

    faltas_data = row.get("faltas", "")
    for falta in re.split(r"[\n,;]+", str(faltas_data or "")):
        if falta.strip():
            pdf.cell(190, 6, pdf_texto(f"- {falta.strip()}"), ln=True)

    # Observaciones y Sanción
    if row.get("observaciones"):
        pdf.ln(4)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(190, 8, pdf_texto("Observaciones:"), ln=True)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 6, pdf_texto(row.get("observaciones")))

    pdf.ln(4)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 8, pdf_texto("Sanción / Detalles de la medida:"), ln=True)
    pdf.set_font("Arial", "", 11)
    sancion_data = row.get("sancion", "") or "Sin observaciones registradas."
    pdf.multi_cell(0, 6, pdf_texto(sancion_data))

    # Descarga puntual de la imagen solo para el PDF requerido
    foto_url = obtener_url_foto(row.get("foto_path"))
    if foto_url:
        try:
            resp = requests.get(foto_url, timeout=10)
            if resp.status_code == 200:
                img_ram = io.BytesIO(resp.content)
                pdf.ln(6)
                pdf.set_font("Arial", "B", 12)
                pdf.cell(190, 8, pdf_texto("Evidencia Fotográfica:"), ln=True)
                pdf.image(img_ram, x=15, w=160)
        except Exception:
            pass

    salida = pdf.output(dest="S")
    return bytes(salida) if isinstance(salida, (bytes, bytearray)) else salida.encode("latin-1", errors="replace")

# ============================================================
# STREAMLIT INTERFAZ & LOGIN
# ============================================================
st.set_page_config(page_title="Control de Seguridad Industrial", layout="wide")

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("Acceso al Sistema de Seguridad")
    user = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if user == USUARIO_ADMIN and password == PASSWORD_ADMIN:
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Credenciales incorrectas.")
    st.stop()

st.sidebar.title("Navegación")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

st.title("Sistema de Gestión de Seguridad e Higiene")
st.caption("Registro permanente de informes y evidencias fotográficas.")

# ============================================================
# ALERTA DE REINCIDENCIA
# ============================================================
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

# ============================================================
# PESTAÑAS
# ============================================================
tab_reg, tab_hist = st.tabs(["Registro de Incidencias", "Historial de Informes"])

# PESTAÑA 1: REGISTRO
with tab_reg:
    st.subheader("Formulario de Registro")

    opciones_menu = list(MAPA_LISTAS.keys()) + ["Cargar nombres apartes"]
    opcion = st.radio("Seleccione el grupo de personal:", opciones_menu)

    operario = ""
    grupo = ""

    if opcion in MAPA_LISTAS:
        grupo, archivo_txt = MAPA_LISTAS[opcion]
        lista_choferes = cargar_lista_txt(archivo_txt)
        if lista_choferes:
            operario = st.selectbox(f"Personal de {grupo} Involucrado", lista_choferes)
        else:
            st.warning(f"No se encontraron nombres en el archivo {archivo_txt}.")
    else:
        grupo = "Carga Aparte / Extra"
        st.info("Módulo para registrar choferes fuera de las listas habituales.")
        
        with st.expander("➕ Registrar nuevo chofer"):
            nuevo = st.text_input("Nombre completo del nuevo chofer")
            if st.button("Guardar nombre en el sistema"):
                if nuevo.strip():
                    guardar_chofer_extra(nuevo.strip())
                    st.success(f"'{nuevo.strip()}' agregado con éxito.")
                    st.rerun()
                else:
                    st.error("El nombre no puede estar vacío.")

        extras = cargar_lista_txt(CHOFERES_EXTRAS_FILE)
        if extras:
            operario = st.selectbox("Seleccione el chofer extra", extras)
        else:
            st.warning("No hay choferes extra cargados.")

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

    if st.button("Guardar Informe", type="primary"):
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

# PESTAÑA 2: HISTORIAL (OPTIMIZADA PARA CONTROL DE EGRESS)
with tab_hist:
    st.subheader("Historial de Registros")

    datos_hist = consultar_infracciones()
    if not datos_hist:
        st.info("Todavía no hay informes registrados.")
    else:
        dfh = pd.DataFrame(datos_hist)
        
        grupos_disponibles = ["Mostrar Todos"] + sorted(
            [str(x) for x in dfh["grupo_lista"].dropna().unique() if str(x).strip()]
        ) if "grupo_lista" in dfh.columns else ["Mostrar Todos"]

        filtro = st.selectbox("Filtrar por grupo", grupos_disponibles)
        if filtro != "Mostrar Todos":
            dfh = dfh[dfh["grupo_lista"].astype(str) == filtro]

        # Paginación para proteger el ancho de banda
        TAMANO_PAGINA = 10
        total_paginas = max(1, (len(dfh) + TAMANO_PAGINA - 1) // TAMANO_PAGINA)
        pagina_actual = st.number_input("Página", min_value=1, max_value=total_paginas, value=1)
        
        inicio = (pagina_actual - 1) * TAMANO_PAGINA
        fin = inicio + TAMANO_PAGINA
        dfh_paginado = dfh.iloc[inicio:fin]

        for _, row in dfh_paginado.iterrows():
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

                # Preparación del PDF únicamente cuando se presiona el botón
                if st.button(f"📄 Preparar PDF de Informe #{rid}", key=f"btn_pdf_{rid}"):
                    with st.spinner("Generando documento..."):
                        try:
                            pdf_bytes = generar_pdf(row.to_dict())
                            st.download_button(
                                "📥 Descargar PDF Generado",
                                data=pdf_bytes,
                                file_name=f"Informe_{rid}_{limpiar_nombre(op)}.pdf",
                                mime="application/pdf",
                                key=f"pdf_download_{rid}"
                            )
                        except Exception as e:
                            st.error(f"No se pudo generar el PDF: {e}")
