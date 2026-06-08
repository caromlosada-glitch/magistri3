import streamlit as st
import google.generativeai as genai
import re

# ── Configuración ────────────────────────────────────────────────
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.0-flash")

st.set_page_config(
    page_title="Magister Scholasticus",
    page_icon="🏛️",
    layout="wide"
)

# ── Documentos RAG embebidos ─────────────────────────────────────
RAG_HABITA = """
FUENTE PRIMARIA — Authentica Habita de Federico Barbarroja (1158):
'Concedemos este privilegio, por nuestra magnanimidad, a todos los escolares que,
debido a sus estudios, se trasladan de un lugar a otro... para que tanto ellos como
sus enviados puedan ir a vivir con total seguridad en los lugares donde se lleva a
cabo el estudio de los textos... de ahora en adelante, debemos tener cuidado de no
ofender a los escolares; no pueden ser objeto de ningún tipo de condena por crímenes
cometidos en otra provincia... si los estudiantes son requeridos por alguien por
cualquier razón, pueden ser juzgados a su propia elección por el señor, por su maestro
o por el obispo de la ciudad.'
Dado en Roncaglia, noviembre de 1158.
"""

RAG_ESTATUTOS = """
FUENTE PRIMARIA — Estatutos de la Universidad de París (1215), Roberto de Courçon:
'Nadie podrá licenciarse en Artes en París, hasta haber cumplido los veintiún años
de edad, y para llegar a licenciarse deberá antes haber cursado, por lo menos,
estudios durante seis años en la Facultad de Artes... Y ordenamos que se lean los
libros de la Dialéctica de Aristóteles, tanto los de la vieja como los de la nueva,
en las escuelas ordinarias... No se lean en días festivos más que filósofos y retóricos,
y alguna vez las Vialia y el Barbatismum y la Etica... No se lean, en cambio, los
libros de Aristóteles de Metafísica y de Filosofía Natural.'
"""

RAG_PARIS = """
FUENTE SECUNDARIA — Ana María Mora, 'La Universidad de París en el siglo XIII' (2008):
ORÍGENES: 'La Universidad de París es el punto culminante de una mutación que desde
hace algunas décadas venía dándose al interior del sistema educativo del clero cristiano.'
ESTRUCTURA: 'La Universidad de París era un organismo autónomo cuyos miembros estaban
reunidos bajo un juramento, obedecían a ciertos dirigentes elegidos por ellos.'
MÉTODOS: 'El maestro proponía una cuestión con respecto a un tema, exponía las dos
posiciones posibles con los argumentos que las sostienen, pasaba a determinar la cuestión
dando su respuesta final o determinatio.'
CURRICULUM 1255: 'La universidad elimina de su programa el quadrivium y la retórica.
Reintegra la Ética y prescribe oficialmente la filosofía natural y la metafísica aristotélicas.'
"""

SYSTEM_PROMPT = f"""Eres 'Magister Scholasticus', tutor erudito de historia de la universidad medieval (siglos XII-XV).
Guías al estudiante por 4 niveles de conocimiento.

BASE DE CONOCIMIENTOS (RAG — usa estos documentos como fuente principal):
{RAG_HABITA}
{RAG_ESTATUTOS}
{RAG_PARIS}

NIVELES:
- Nivel 1: Orígenes — Universitas como gremio, escuelas catedralicias, contexto histórico.
- Nivel 2: Modelos de Bolonia y París — diferencias organizativas, rol de maestros y estudiantes.
- Nivel 3: Curriculum Medieval — Trivium y Quadrivium. Cita los Estatutos de 1215.
- Nivel 4: Legado — Constitución Habita, Goliardos, herencia moderna. Cita la Habita de 1158.

REGLAS:
1. Estructura dialéctica obligatoria:
   **Quaestio:** (pregunta central)
   **Videtur quod:** (argumentos erróneos o comunes)
   **Sed contra:** (argumento de autoridad — cita los documentos reales)
   **Respondeo:** (conclusión pedagógica)

2. Avance de nivel: solo cuando el estudiante demuestre comprensión real del concepto clave.
   Nivel 1 → concepto clave: Universitas como gremio, no solo un edificio.
   Cuando el estudiante lo comprenda, añade al final: [NIVEL_COMPLETADO:X]

3. Citas: menciona las fuentes: [Estatutos 1215], [Habita 1158], [Mora 2008].
4. Vocabulario: Trivium, Quadrivium, Studium Generale, Goliardos, Disputatio.
5. Tono: erudito, formal pero alentador. Termina siempre con una pregunta socrática.
6. Longitud: 130-220 palabras por respuesta.
"""

NIVELES = [
    {"n": 1, "nombre": "Orígenes de la Universidad",  "progreso": 0.25},
    {"n": 2, "nombre": "Modelos de Bolonia y París",   "progreso": 0.50},
    {"n": 3, "nombre": "El Curriculum Medieval",       "progreso": 0.75},
    {"n": 4, "nombre": "Legado e Influencia",          "progreso": 1.00},
]

CONCEPTOS_MAP = {
    "universitas": ["universitas", "gremio", "corporación"],
    "studium":     ["studium generale", "studium"],
    "trivium":     ["trivium", "gramática", "retórica", "dialéctica"],
    "quadrivium":  ["quadrivium", "aritmética", "geometría", "astronomía"],
    "goliardos":   ["goliardo", "goliardos"],
    "habita":      ["habita", "barbarroja", "federico"],
}

# ── Estado de sesión ─────────────────────────────────────────────
if "nivel" not in st.session_state:
    st.session_state.nivel = 1
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []
if "conceptos" not in st.session_state:
    st.session_state.conceptos = set()
if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat(history=[])

def detectar_conceptos(texto):
    t = texto.lower()
    for key, kws in CONCEPTOS_MAP.items():
        if any(k in t for k in kws):
            st.session_state.conceptos.add(key)

def preguntar_gemini(user_msg):
    prompt_completo = (
        SYSTEM_PROMPT +
        f"\n\nEstado actual del estudiante: NIVEL {st.session_state.nivel}\n\n"
        f"Mensaje del estudiante: {user_msg}"
    )
    resp = st.session_state.chat.send_message(prompt_completo)
    return resp.text

# ── Sidebar ──────────────────────────────────────────────────────
with st.sidebar:
    st.title("📜 Scriptorum")
    st.markdown("---")
    nv = NIVELES[st.session_state.nivel - 1]
    st.metric("Grado actual", f"Nivel {nv['n']}")
    st.progress(nv["progreso"])
    st.caption(f"*{nv['nombre']}*")
    st.markdown("---")
    st.subheader("Itinerario")
    for lvl in NIVELES:
        if lvl["n"] < st.session_state.nivel:
            st.write(f"✅ Nivel {lvl['n']} — {lvl['nombre']}")
        elif lvl["n"] == st.session_state.nivel:
            st.write(f"▶️ **Nivel {lvl['n']} — {lvl['nombre']}**")
        else:
            st.write(f"○ Nivel {lvl['n']} — {lvl['nombre']}")
    st.markdown("---")
    st.subheader("Conceptos dominados")
    for c in CONCEPTOS_MAP.keys():
        if c in st.session_state.conceptos:
            st.write(f"📜 {c.capitalize()}")
        else:
            st.write(f"· ~~{c.capitalize()}~~")

# ── Main ─────────────────────────────────────────────────────────
st.title("🏛️ Magister Scholasticus")
st.caption("Tutor de Historia de la Universidad Medieval · Siglos XII–XV")
st.markdown("---")

for msg in st.session_state.mensajes:
    with st.chat_message(msg["role"], avatar="🎓" if msg["role"] == "assistant" else "📖"):
        st.markdown(msg["content"])

# Bienvenida automática
if not st.session_state.mensajes:
    with st.chat_message("assistant", avatar="🎓"):
        with st.spinner("El Magister prepara su salutación..."):
            bienvenida = preguntar_gemini(
                "Saluda al estudiante, preséntate como Magister Scholasticus "
                "y lanza la primera Quaestio sobre los orígenes de la universidad medieval."
            )
            st.markdown(bienvenida)
            st.session_state.mensajes.append({"role": "assistant", "content": bienvenida})

# Input
if prompt := st.chat_input("Responde al Magister o formula tu quaestio…"):
    detectar_conceptos(prompt)
    st.session_state.mensajes.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="📖"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🎓"):
        with st.spinner("El Magister medita su respuesta..."):
            respuesta = preguntar_gemini(prompt)

        detectar_conceptos(respuesta)

        match = re.search(r"\[NIVEL_COMPLETADO:(\d)\]", respuesta)
        if match:
            nivel_completado = int(match.group(1))
            if nivel_completado == st.session_state.nivel and st.session_state.nivel < 4:
                st.session_state.nivel += 1
                st.balloons()
                st.success(f"⚜️ ¡Has ascendido al Nivel {st.session_state.nivel}: {NIVELES[st.session_state.nivel-1]['nombre']}!")

        limpia = re.sub(r"\[NIVEL_COMPLETADO:\d\]", "", respuesta).strip()
        st.markdown(limpia)
        st.session_state.mensajes.append({"role": "assistant", "content": limpia})
