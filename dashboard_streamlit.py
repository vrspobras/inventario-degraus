import os
import base64
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import folium
import zipfile
import xml.etree.ElementTree as ET
import numpy as np
import re
import sqlite3

from streamlit_folium import st_folium

# ═══════════════════════════════════════════════════════════════════
# IDENTIDADE VISUAL — Sistema de Inventário
# ═══════════════════════════════════════════════════════════════════
AZUL      = "#1B3A8C"
AZUL_DARK = "#122970"
OURO      = "#F5A623"
CINZA_BG  = "#F4F6FA"
BRANCO    = "#FFFFFF"
VERMELHO  = "#D32F2F"
VERDE     = "#2E7D32"
LARANJA   = "#E65100"
AMARELO   = "#F9A825"



# ═══════════════════════════════════════════════════════════════════
# USUÁRIOS — edite aqui para adicionar/remover acessos
# senha fica em hash SHA256 para não ficar em texto puro
# ═══════════════════════════════════════════════════════════════════
import hashlib

def _hash(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

USUARIOS = {
    "admin": {
        "senha": _hash("admin2024"),
        "nome":  "Administrador",
        "perfil": "admin"   # admin vê tudo
    },
    "operador": {
        "senha": _hash("obras2024"),
        "nome":  "Operador de Campo",
        "perfil": "operador"  # operador só cadastra e vê pontos
    },
}

CSS_LOGIN = f"""
<style>
body, .stApp {{ background: #f0f4fb !important; }}
.login-card {{
    background: {BRANCO};
    border-radius: 16px;
    box-shadow: 0 8px 40px rgba(27,58,140,0.18);
    padding: 36px 40px 32px 40px;
    width: 100%;
    border-top: 6px solid {OURO};
    margin: 0 auto;
}}
.login-logo {{
    text-align: center;
    margin-bottom: 20px;
}}
.login-logo h2 {{
    color: {AZUL};
    font-size: 1.4rem;
    font-weight: 800;
    margin: 10px 0 4px 0;
    letter-spacing: 0.5px;
}}
.login-logo p {{
    color: #8a94b2;
    font-size: 0.8rem;
    margin: 0;
    letter-spacing: 1px;
    text-transform: uppercase;
}}
.login-footer {{
    text-align: center;
    color: #b0b8d0;
    font-size: 0.7rem;
    margin-top: 20px;
}}
.stApp input {{
    color: #122970 !important;
    background: #FFFFFF !important;
}}
</style>
"""

def tela_login():
    st.markdown(CSS_LOGIN, unsafe_allow_html=True)
    # esconder sidebar na tela de login
    st.markdown("<style>[data-testid='stSidebar']{display:none}</style>", unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([0.3, 2, 0.3])
    with col_c:
        st.markdown('''<div class="login-card">''', unsafe_allow_html=True)

        # Logo / cabeçalho
        logo_path = "logo.png"
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                logo_b64 = base64.b64encode(f.read()).decode()
            st.markdown(
                f'''<div class="login-logo">
                    <img src="data:image/png;base64,{logo_b64}" style="width:140px;">
                    <p>Inventário de Degraus</p>
                </div>''',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'''<div class="login-logo">
                    <span style="font-size:3rem;">🛣️</span>
                    <h2>Sistema de Inventário</h2>
                    <p>Inventário de Degraus</p>
                </div>''',
                unsafe_allow_html=True
            )

        usuario = st.text_input("Usuário", placeholder="Digite seu usuário", key="login_user")
        senha   = st.text_input("Senha",   placeholder="Digite sua senha",   key="login_pass", type="password")

        if st.button("Entrar →", use_container_width=True, key="login_btn"):
            if usuario in USUARIOS and USUARIOS[usuario]["senha"] == _hash(senha):
                st.session_state["logado"]  = True
                st.session_state["usuario"] = usuario
                st.session_state["nome"]    = USUARIOS[usuario]["nome"]
                st.session_state["perfil"]  = USUARIOS[usuario]["perfil"]
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

        st.markdown(
            '<div class="login-footer">© Sistema de Inventário · Acesso restrito</div>',
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# CONTROLE DE SESSÃO
# ═══════════════════════════════════════════════════════════════════
if "logado" not in st.session_state:
    st.session_state["logado"] = False

if not st.session_state["logado"]:
    tela_login()
    st.stop()



CSS = f"""
<style>
/* ── Fundo geral ── */
.stApp {{ background-color: {CINZA_BG}; }}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {AZUL_DARK} 0%, {AZUL} 100%);
    border-right: 4px solid {OURO};
}}
[data-testid="stSidebar"] * {{ color: {BRANCO} !important; }}
[data-testid="stSidebar"] .stRadio label {{ font-size: 15px; font-weight: 600; }}
[data-testid="stSidebar"] hr {{ border-color: {OURO}44; }}

/* ── Cabeçalho das páginas ── */
.vr-header {{
    background: linear-gradient(90deg, {AZUL_DARK}, {AZUL});
    border-left: 6px solid {OURO};
    border-radius: 10px;
    padding: 18px 28px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 18px;
}}
.vr-header h1 {{
    color: {BRANCO};
    margin: 0;
    font-size: 1.7rem;
    font-weight: 800;
    letter-spacing: 0.5px;
}}
.vr-header p {{
    color: {OURO};
    margin: 4px 0 0 0;
    font-size: 0.85rem;
    font-weight: 500;
    letter-spacing: 1px;
    text-transform: uppercase;
}}

/* ── Cards de métrica ── */
[data-testid="metric-container"] {{
    background: {BRANCO};
    border: 1px solid #dde3f0;
    border-top: 4px solid {AZUL};
    border-radius: 10px;
    padding: 16px 20px;
    box-shadow: 0 2px 8px rgba(27,58,140,0.08);
}}
[data-testid="metric-container"] label {{
    color: {AZUL} !important;
    font-weight: 700;
    font-size: 0.78rem;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}}
[data-testid="metric-container"] [data-testid="stMetricValue"] {{
    color: {AZUL_DARK} !important;
    font-size: 2rem !important;
    font-weight: 800 !important;
}}

/* Card crítico vermelho */
.metric-critico [data-testid="metric-container"] {{
    border-top-color: {VERMELHO};
}}

/* ── Subheaders ── */
.vr-section {{
    color: {AZUL};
    font-weight: 700;
    font-size: 1rem;
    border-bottom: 2px solid {OURO};
    padding-bottom: 6px;
    margin: 20px 0 12px 0;
    text-transform: uppercase;
    letter-spacing: 0.6px;
}}

/* ── Botões primários ── */
.stButton > button {{
    background: {AZUL};
    color: {BRANCO};
    border: none;
    border-radius: 8px;
    font-weight: 700;
    letter-spacing: 0.4px;
    transition: background 0.2s, transform 0.1s;
    padding: 8px 18px;
}}
.stButton > button:hover {{
    background: {AZUL_DARK};
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(27,58,140,0.25);
}}

/* Botão de perigo (apagar) */
.btn-danger > button {{
    background: {VERMELHO} !important;
}}
.btn-danger > button:hover {{
    background: #b71c1c !important;
}}

/* ── Tabelas ── */
[data-testid="stDataFrame"] {{
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #dde3f0;
    box-shadow: 0 2px 8px rgba(27,58,140,0.06);
}}

/* ── Inputs ── */
.stNumberInput input, .stTextInput input, .stSelectbox select {{
    border-radius: 6px;
    border: 1.5px solid #c5cde8;
    color: #122970 !important;
    background-color: #FFFFFF !important;
}}
.stNumberInput input:focus, .stTextInput input:focus {{
    border-color: #1B3A8C;
    box-shadow: 0 0 0 2px rgba(27,58,140,0.15);
}}
/* Todos inputs com fonte escura */
input, textarea, select,
[data-baseweb="input"] input,
[data-baseweb="select"] div,
[data-baseweb="textarea"] textarea,
[data-testid="stMultiSelect"] span,
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input {{
    color: #122970 !important;
    background-color: #FFFFFF !important;
}}
/* Dropdown options */
[data-baseweb="popover"] li,
[data-baseweb="menu"] li {{
    color: #122970 !important;
    background-color: #FFFFFF !important;
}}
[data-baseweb="popover"] li:hover {{
    background-color: #e8edf8 !important;
}}
/* Labels fora da sidebar */
.stApp [data-testid="stWidgetLabel"] p,
.stApp label {{ color: #122970 !important; }}

/* ── Divider personalizado ── */
.vr-divider {{
    border: none;
    border-top: 2px solid #dde3f0;
    margin: 20px 0;
}}

/* ── Rodapé ── */
.vr-footer {{
    text-align: center;
    color: #8a94b2;
    font-size: 0.75rem;
    padding: 24px 0 8px 0;
    border-top: 1px solid #dde3f0;
    margin-top: 40px;
}}
</style>
"""

# ═══════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Sistema de Inventário — Inventário de Degraus",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.markdown(CSS, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# LOGO NA SIDEBAR
# ═══════════════════════════════════════════════════════════════════
logo_path = "logo.png"
if os.path.exists(logo_path):
    with open(logo_path, "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode()
    st.sidebar.markdown(
        f"""
        <div style="text-align:center; padding: 18px 0 8px 0;">
            <img src="data:image/png;base64,{logo_b64}"
                 style="width:160px; filter: brightness(0) invert(1);">
        </div>
        <hr style="border-color:#F5A62366; margin: 4px 0 16px 0;">
        """,
        unsafe_allow_html=True
    )
else:
    st.sidebar.markdown(
        f"""<div style="text-align:center; padding:16px 0 8px 0;">
            <span style="font-size:2rem;">🛣️</span><br>
            <span style="color:#F5A623; font-weight:800; font-size:1.1rem; letter-spacing:1px;">INVENTÁRIO</span>
        </div><hr style="border-color:#F5A62366; margin:4px 0 16px 0;">""",
        unsafe_allow_html=True
    )

# ── Menu ──────────────────────────────────────────────────────────
# Saudação + logout
st.sidebar.markdown(
    f'''<div style="padding:8px 0 12px 0; text-align:center;">
        <span style="color:#F5A623; font-size:0.75rem; font-weight:700;">👤 {st.session_state["nome"]}</span>
    </div>''',
    unsafe_allow_html=True
)
if st.sidebar.button("🚪 Sair", use_container_width=True, key="logout_btn"):
    for k in ["logado","usuario","nome","perfil"]:
        st.session_state.pop(k, None)
    st.rerun()

st.sidebar.markdown("<hr style='border-color:#F5A62366; margin:4px 0 12px 0;'>", unsafe_allow_html=True)

st.sidebar.markdown(
    '<p style="color:#F5A623; font-size:0.7rem; letter-spacing:2px; font-weight:700; margin-bottom:4px;">NAVEGAÇÃO</p>',
    unsafe_allow_html=True
)
# Admin vê tudo; operador não vê o Dashboard completo
if st.session_state["perfil"] == "admin":
    opcoes = ["🏠  Dashboard", "📋  Pontos Cadastrados", "📷  Cadastrar Fotos", "📦  Upload em Massa", "📲  Importar SD"]
else:
    opcoes = ["📋  Pontos Cadastrados", "📷  Cadastrar Fotos", "📦  Upload em Massa", "📲  Importar SD"]

pagina = st.sidebar.radio(
    "Página",
    opcoes,
    label_visibility="collapsed"
)
pagina = pagina.split("  ")[-1].strip()  # extrai nome limpo

# Garantir que página atual existe no menu (evita "Page not found")
paginas_validas = [o.split("  ")[-1].strip() for o in opcoes]
if pagina not in paginas_validas:
    pagina = paginas_validas[0]

# ═══════════════════════════════════════════════════════════════════
# KMZ
# ═══════════════════════════════════════════════════════════════════

@st.cache_resource
def carregar_kmz():
    todos_os_marcos = []
    rodovias = {}

    with zipfile.ZipFile("kmz_rodovias.kmz", "r") as z:
        kml_file = [x for x in z.namelist() if x.endswith(".kml")][0]
        conteudo = z.read(kml_file)

    rootxml = ET.fromstring(conteudo)
    ns = {"kml": "http://www.opengis.net/kml/2.2"}

    def normalizar_rodovia(txt):
        txt = str(txt).upper()
        m = re.search(r'(SPA\s*\d+/\d+)', txt)
        if m:
            return m.group(1).replace(" ", "-")
        m = re.search(r'(SP\s*\d+)', txt)
        if m:
            return m.group(1).replace(" ", "-")
        return txt.strip()

    def process_folder(folder):
        nome = folder.find("kml:name", ns)
        nome_folder = nome.text if nome is not None else ""
        rodovia = None
        m = re.search(r'(SPA\s*\d+/\d+|SP\s*\d+)', nome_folder.upper())
        if m:
            rodovia = normalizar_rodovia(m.group())
        if rodovia:
            rodovias.setdefault(rodovia, [])
            for pm in folder.findall("kml:Placemark", ns):
                nm = pm.find("kml:name", ns)
                pt = pm.find(".//kml:Point/kml:coordinates", ns)
                if nm is None or pt is None:
                    continue
                km_match = re.search(r'(\d+(?:[.,]\d+)?)', str(nm.text))
                if not km_match:
                    continue
                km = float(km_match.group(1).replace(",", "."))
                lon, lat, *_ = map(float, pt.text.strip().split(","))
                rodovias[rodovia].append((km, lat, lon))
                todos_os_marcos.append({"rodovia": rodovia, "km": km, "lat": lat, "lon": lon})
        for sub in folder.findall("kml:Folder", ns):
            process_folder(sub)

    for folder in rootxml.findall(".//kml:Folder", ns):
        process_folder(folder)
    for rodovia in rodovias:
        rodovias[rodovia].sort(key=lambda x: x[0])
    return todos_os_marcos, rodovias


TODOS_OS_MARCOS, RODOVIAS = carregar_kmz()


def distancia(lat1, lon1, lat2, lon2):
    return np.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)


def descobrir_rodovia(lat, lon):
    menor = None
    for marco in TODOS_OS_MARCOS:
        d = distancia(lat, lon, marco["lat"], marco["lon"])
        if menor is None or d < menor[0]:
            menor = (d, marco["rodovia"])
    return menor[1]


def calcular_km_real(rodovia, lat, lon):
    dados = RODOVIAS[rodovia]
    melhor_dist, melhor_km = None, None
    for i in range(len(dados) - 1):
        km1, lat1, lon1 = dados[i]
        km2, lat2, lon2 = dados[i + 1]
        abx, aby = lon2 - lon1, lat2 - lat1
        apx, apy = lon - lon1, lat - lat1
        ab2 = abx * abx + aby * aby
        if ab2 == 0:
            continue
        t = max(0, min(1, (apx * abx + apy * aby) / ab2))
        dist = np.sqrt((lon - (lon1 + abx * t))**2 + (lat - (lat1 + aby * t))**2)
        km_real = km1 + (km2 - km1) * t
        if melhor_dist is None or dist < melhor_dist:
            melhor_dist, melhor_km = dist, km_real
    return round(melhor_km, 3)


# ═══════════════════════════════════════════════════════════════════
# BANCO
# ═══════════════════════════════════════════════════════════════════

def get_conn():
    """Retorna conexão PostgreSQL (Supabase) ou SQLite local como fallback."""
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url:
        import psycopg2
        return psycopg2.connect(db_url), "pg"
    else:
        return sqlite3.connect("banco.db"), "sqlite"

def criar_tabela():
    con, tipo = get_conn()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fotos (
            arquivo   TEXT,
            rodovia   TEXT,
            km_real   REAL,
            sentido   TEXT,
            latitude  REAL,
            longitude REAL,
            degrau    REAL,
            data      TEXT,
            ocr_bruto TEXT
        )
    """)
    con.commit()
    con.close()

criar_tabela()

@st.cache_data(ttl=30)
def carregar_dados():
    con, tipo = get_conn()
    try:
        df = pd.read_sql("SELECT * FROM fotos", con)
    except Exception:
        df = pd.DataFrame(columns=[
            "arquivo", "rodovia", "km_real", "sentido",
            "latitude", "longitude", "degrau", "data", "ocr_bruto"
        ])
    con.close()
    return df


def _header(icone, titulo, subtitulo=""):
    st.markdown(
        f"""<div class="vr-header">
            <div>
                <h1>{icone} {titulo}</h1>
                {"<p>" + subtitulo + "</p>" if subtitulo else ""}
            </div>
        </div>""",
        unsafe_allow_html=True
    )


def _section(texto):
    st.markdown(f'<p class="vr-section">{texto}</p>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# CARREGAR & PREPARAR
# ═══════════════════════════════════════════════════════════════════

df = carregar_dados().rename(columns={
    "arquivo": "Arquivo", "rodovia": "Rodovia Encontrada",
    "km_real": "KM Real", "sentido": "Sentido",
    "latitude": "Latitude", "longitude": "Longitude",
    "degrau": "Degrau", "data": "Data"
})
if len(df):
    df["KM Real"] = pd.to_numeric(df["KM Real"], errors="coerce")
    df["Degrau"]  = pd.to_numeric(df["Degrau"],  errors="coerce")

# ── Filtros sidebar (só aparecem no Dashboard) ─────────────────────
if pagina == "Dashboard":
    st.sidebar.markdown('<hr style="border-color:#F5A62366; margin:16px 0 10px 0;">', unsafe_allow_html=True)
    st.sidebar.markdown(
        '<p style="color:#F5A623; font-size:0.7rem; letter-spacing:2px; font-weight:700; margin-bottom:4px;">FILTROS</p>',
        unsafe_allow_html=True
    )
    rodovia_filtro = st.sidebar.multiselect("Rodovia", sorted(df["Rodovia Encontrada"].dropna().unique()))
    sentido_filtro = st.sidebar.multiselect("Sentido",  sorted(df["Sentido"].dropna().unique()))
    km_ini = st.sidebar.number_input("KM Inicial", value=0.0)
    km_fim = st.sidebar.number_input(
        "KM Final",
        value=float(df["KM Real"].max()) if len(df) and df["KM Real"].notna().any() else 0.0
    )
    dff = df.copy()
    if rodovia_filtro:
        dff = dff[dff["Rodovia Encontrada"].isin(rodovia_filtro)]
    if sentido_filtro:
        dff = dff[dff["Sentido"].isin(sentido_filtro)]
    dff = dff[(dff["KM Real"] >= km_ini) & (dff["KM Real"] <= km_fim)]
else:
    dff = df.copy()

# Rodapé sidebar
st.sidebar.markdown(
    f"""<div style="position:fixed; bottom:0; left:0; width:inherit;
                    padding:12px; border-top:1px solid #F5A62333;
                    background:{AZUL_DARK};">
        <p style="color:#8899cc; font-size:0.68rem; margin:0; text-align:center;">
            © Sistema de Inventário<br>Inventário de Degraus v1.0
        </p>
    </div>""",
    unsafe_allow_html=True
)


# ═══════════════════════════════════════════════════════════════════
# PÁGINA: DASHBOARD
# ═══════════════════════════════════════════════════════════════════

if pagina == "Dashboard":

    _header("🛣️", "Inventário de Degraus", "Sistema de Inventário — Monitoramento de Pavimento")

    # ── Métricas ───────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📸  Total de Fotos",   len(dff))
    c2.metric("📏  Degrau Médio",
              f"{dff['Degrau'].mean():.1f} mm" if dff["Degrau"].notna().any() else "—")
    c3.metric("⚠️  Degrau Máximo",
              f"{dff['Degrau'].max():.1f} mm"  if dff["Degrau"].notna().any() else "—")
    c4.metric("🔴  Críticos (>30mm)", int((dff["Degrau"] > 30).sum()))

    st.markdown("<hr class='vr-divider'>", unsafe_allow_html=True)

    # ── Mapa + Scatter ─────────────────────────────────────────────
    col_mapa, col_graf = st.columns([1.3, 1])

    with col_mapa:
        _section("📍 Localização dos Pontos")
        dff_mapa = dff.dropna(subset=["Latitude", "Longitude"])
        if len(dff_mapa):
            mapa = folium.Map(
                location=[dff_mapa["Latitude"].mean(), dff_mapa["Longitude"].mean()],
                zoom_start=11,
                tiles="CartoDB positron"
            )
            for _, row in dff_mapa.iterrows():
                d = row["Degrau"]
                cor = VERDE if not pd.notna(d) else (
                    VERMELHO if d > 30 else LARANJA if d > 20 else AMARELO if d > 10 else VERDE
                )
                popup = (f"<b style='color:{AZUL}'>{row['Arquivo']}</b><br>"
                         f"<b>Rodovia:</b> {row['Rodovia Encontrada']}<br>"
                         f"<b>KM:</b> {row['KM Real']}<br>"
                         f"<b>Degrau:</b> {row['Degrau']} mm<br>"
                         f"<b>Sentido:</b> {row['Sentido']}")
                folium.CircleMarker(
                    location=[row["Latitude"], row["Longitude"]],
                    radius=3,
                    color=cor,
                    fill=True,
                    fill_opacity=0.9,
                    weight=1,
                    popup=folium.Popup(popup, max_width=260)
                ).add_to(mapa)
            st_folium(mapa, width=None, height=520, use_container_width=True)
        else:
            st.info("Nenhum ponto com coordenadas válidas.")

    with col_graf:
        _section("📈 Degrau × KM")
        fig = px.scatter(
            dff, x="KM Real", y="Degrau",
            color="Rodovia Encontrada",
            hover_data=["Arquivo"],
            color_discrete_sequence=[AZUL, OURO, "#5c6bc0", "#26a69a"],
        )
        fig.update_layout(
            plot_bgcolor=BRANCO, paper_bgcolor=BRANCO,
            font_color=AZUL_DARK,
            legend=dict(orientation="h", y=-0.2),
            margin=dict(t=20, b=20, l=10, r=10),
        )
        fig.add_hline(y=30, line_dash="dash", line_color=VERMELHO,
                      annotation_text="Limite crítico (30mm)",
                      annotation_font_color=VERMELHO)
        st.plotly_chart(fig, use_container_width=True)

        _section("📊 Distribuição dos Degraus")
        fig2 = px.histogram(
            dff, x="Degrau", nbins=20,
            color_discrete_sequence=[AZUL]
        )
        fig2.update_layout(
            plot_bgcolor=BRANCO, paper_bgcolor=BRANCO,
            font_color=AZUL_DARK, margin=dict(t=10, b=10, l=10, r=10),
            bargap=0.06
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("<hr class='vr-divider'>", unsafe_allow_html=True)

    # ── Gráficos linha 2 ──────────────────────────────────────────
    g1, g2 = st.columns(2)
    with g1:
        _section("🛣️ Fotos por Rodovia")
        fig = px.bar(
            dff.groupby("Rodovia Encontrada", as_index=False).size().rename(columns={"size": "Qtd"}),
            x="Rodovia Encontrada", y="Qtd",
            color_discrete_sequence=[AZUL]
        )
        fig.update_layout(plot_bgcolor=BRANCO, paper_bgcolor=BRANCO, font_color=AZUL_DARK,
                          margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

    with g2:
        _section("🧭 Fotos por Sentido")
        fig = px.pie(
            dff.groupby("Sentido", as_index=False).size().rename(columns={"size": "Qtd"}),
            names="Sentido", values="Qtd",
            color_discrete_sequence=[AZUL, OURO, "#5c6bc0", "#26a69a"]
        )
        fig.update_layout(paper_bgcolor=BRANCO, font_color=AZUL_DARK,
                          margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<hr class='vr-divider'>", unsafe_allow_html=True)

    # ── Ranking ───────────────────────────────────────────────────
    _section("🏆 Top 20 Maiores Degraus")
    ranking = dff.sort_values("Degrau", ascending=False).head(20)
    st.dataframe(
        ranking[["Rodovia Encontrada", "KM Real", "Degrau", "Sentido", "Arquivo"]],
        use_container_width=True, hide_index=True,
        column_config={
            "KM Real": st.column_config.NumberColumn(format="%.3f"),
            "Degrau":  st.column_config.NumberColumn(format="%.1f mm"),
        }
    )

    st.markdown('<div class="vr-footer">Sistema de Inventário · Sistema de Inventário de Degraus · Todos os direitos reservados</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# PÁGINA: PONTOS CADASTRADOS
# ═══════════════════════════════════════════════════════════════════

elif pagina == "Pontos Cadastrados":

    _header("📋", "Pontos Cadastrados", "Gestão e edição de registros do banco de dados")

    df_banco = carregar_dados().rename(columns={
        "arquivo": "Arquivo", "rodovia": "Rodovia",
        "km_real": "KM Real", "sentido": "Sentido",
        "latitude": "Latitude", "longitude": "Longitude",
        "degrau": "Degrau (mm)", "data": "Data", "ocr_bruto": "OCR Bruto",
    })

    if len(df_banco) == 0:
        st.info("Nenhum ponto cadastrado ainda. Use '📷 Cadastrar Fotos' para adicionar.")
    else:
        df_banco["KM Real"]     = pd.to_numeric(df_banco["KM Real"],     errors="coerce")
        df_banco["Degrau (mm)"] = pd.to_numeric(df_banco["Degrau (mm)"], errors="coerce")

        # ── Filtros ──────────────────────────────────────────────
        fa, fb, fc, fd = st.columns(4)
        f_rod  = fa.multiselect("Rodovia", sorted(df_banco["Rodovia"].dropna().unique()), key="f_rod_pts")
        f_sent = fb.multiselect("Sentido", sorted(df_banco["Sentido"].dropna().unique()), key="f_sent_pts")
        f_dmin = fc.number_input("Degrau mín (mm)", value=0.0, key="f_dmin")
        f_dmax = fd.number_input(
            "Degrau máx (mm)",
            value=float(df_banco["Degrau (mm)"].max()) if df_banco["Degrau (mm)"].notna().any() else 0.0,
            key="f_dmax"
        )

        df_pts = df_banco.copy()
        if f_rod:  df_pts = df_pts[df_pts["Rodovia"].isin(f_rod)]
        if f_sent: df_pts = df_pts[df_pts["Sentido"].isin(f_sent)]
        df_pts = df_pts[
            (df_pts["Degrau (mm)"].isna()) |
            ((df_pts["Degrau (mm)"] >= f_dmin) & (df_pts["Degrau (mm)"] <= f_dmax))
        ].reset_index(drop=True)

        # ── Métricas ──────────────────────────────────────────────
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📸  Total de Pontos",  len(df_pts))
        m2.metric("📏  Degrau Médio",
                  f"{df_pts['Degrau (mm)'].mean():.1f} mm" if df_pts["Degrau (mm)"].notna().any() else "—")
        m3.metric("⚠️  Degrau Máximo",
                  f"{df_pts['Degrau (mm)'].max():.1f} mm"  if df_pts["Degrau (mm)"].notna().any() else "—")
        m4.metric("🔴  Críticos (>30mm)", int((df_pts["Degrau (mm)"] > 30).sum()))

        st.markdown("<hr class='vr-divider'>", unsafe_allow_html=True)

        # Estado da página
        if "pts_linha" not in st.session_state:
            st.session_state["pts_linha"] = 0
        if "pts_confirmar_exclusao" not in st.session_state:
            st.session_state["pts_confirmar_exclusao"] = False
        if "pts_df" not in st.session_state or len(st.session_state["pts_df"]) != len(df_pts):
            st.session_state["pts_df"]    = df_pts.copy()
            st.session_state["pts_linha"] = 0

        pts_df = st.session_state["pts_df"]
        colunas_exibir = ["Arquivo", "Rodovia", "KM Real", "Sentido", "Degrau (mm)", "Latitude", "Longitude", "Data"]

        col_tab, col_img = st.columns([2, 1])

        with col_tab:
            _section("📄 Registros — edite diretamente na tabela")

            pts_editado = st.data_editor(
                pts_df[colunas_exibir].sort_values(["Rodovia", "KM Real"]).reset_index(drop=True),
                use_container_width=True,
                num_rows="fixed",
                key="pts_tabela_sel",
                column_config={
                    "Arquivo":     st.column_config.TextColumn("Arquivo"),
                    "Rodovia":     st.column_config.TextColumn("Rodovia"),
                    "KM Real":     st.column_config.NumberColumn(format="%.3f"),
                    "Sentido":     st.column_config.SelectboxColumn(options=["Norte","Sul","Leste","Oeste"]),
                    "Degrau (mm)": st.column_config.NumberColumn(format="%.1f mm", min_value=0.0, step=1.0),
                    "Latitude":    st.column_config.NumberColumn(format="%.8f"),
                    "Longitude":   st.column_config.NumberColumn(format="%.8f"),
                    "Data":        st.column_config.TextColumn("Data"),
                }
            )

            idx_ativo = min(st.session_state.get("pts_linha", 0), max(0, len(pts_editado) - 1))
            row_ativo = pts_editado.iloc[idx_ativo] if len(pts_editado) > 0 else pts_df.iloc[0]

            ba, bb, bc = st.columns(3)

            if ba.button("✅ Aplicar edições", use_container_width=True, key="pts_aplicar"):
                st.session_state["pts_df"] = pts_editado.copy()
                st.success("Edições aplicadas.")
                st.rerun()


            # Seletor de linha para excluir
            st.markdown("<hr class='vr-divider'>", unsafe_allow_html=True)
            _section("🗑️ Excluir registro")

            nomes_disponiveis = pts_editado["Arquivo"].tolist()
            arquivo_excluir = st.selectbox(
                "Selecione o registro para excluir:",
                options=nomes_disponiveis,
                key="pts_sel_excluir"
            )

            if not st.session_state.get("pts_confirmar_exclusao", False):
                st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
                if st.button("🗑️ Apagar registro selecionado", use_container_width=True, key="pts_apagar_btn"):
                    st.session_state["pts_confirmar_exclusao"] = True
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.warning(f"⚠️ Confirma exclusão de **{arquivo_excluir}**?")
                col_sim, col_nao = st.columns(2)
                with col_sim:
                    st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
                    if st.button("✔️ Sim, apagar", use_container_width=True, key="pts_confirmar_sim"):
                        try:
                            con, tipo = get_conn()
                            cur = con.cursor()
                            ph = "%s" if tipo == "pg" else "?"
                            cur.execute(f"DELETE FROM fotos WHERE arquivo = {ph}", (arquivo_excluir,))
                            con.commit(); con.close()
                            carregar_dados.clear()
                            st.session_state.pop("pts_df", None)
                            st.session_state["pts_linha"] = 0
                            st.session_state["pts_confirmar_exclusao"] = False
                            st.success("Registro apagado.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")
                    st.markdown('</div>', unsafe_allow_html=True)
                with col_nao:
                    if st.button("✖️ Cancelar", use_container_width=True, key="pts_confirmar_nao"):
                        st.session_state["pts_confirmar_exclusao"] = False
                        st.rerun()


        # ── Foto à direita ─────────────────────────────────────────────────────
        with col_img:
            _section("📸 Foto selecionada")

            idx_foto  = min(st.session_state["pts_linha"], len(pts_df) - 1)
            row_foto  = pts_df.iloc[idx_foto]
            nome_foto = row_foto["Arquivo"]

            st.caption(f"**{nome_foto}**")
            st.markdown(
                f"**Rodovia:** {row_foto.get('Rodovia', '—')}  \n"
                f"**KM:** {row_foto.get('KM Real', '—')}  \n"
                f"**Sentido:** {row_foto.get('Sentido', '—')}  \n"
                f"**Degrau:** {row_foto.get('Degrau (mm)', '—')} mm"
            )

            img_encontrada = None
            for pasta in ["fotos", "uploads", "."]:
                caminho = os.path.join(pasta, nome_foto)
                if os.path.exists(caminho):
                    img_encontrada = caminho
                    break

            if img_encontrada:
                from PIL import Image as PILImage
                img_full = PILImage.open(img_encontrada)
                st.image(img_full, caption="Foto completa", use_column_width=True)
                larg, alt = img_full.size
                legenda_crop = img_full.crop((int(larg * 0.45), int(alt * 0.58), larg, alt))
                st.image(legenda_crop, caption="🔍 Recorte legenda", use_column_width=True)
            else:
                st.info("Foto não encontrada em disco.\nSalve as fotos na pasta `fotos/` do projeto.")

        st.markdown("<hr class='vr-divider'>", unsafe_allow_html=True)
        csv = pts_df[colunas_exibir].to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Exportar CSV", csv, "pontos_cadastrados.csv", "text/csv")

    st.markdown('<div class="vr-footer">Sistema de Inventário · Sistema de Inventário de Degraus</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# PÁGINA: CADASTRAR FOTOS
# ═══════════════════════════════════════════════════════════════════

elif pagina == "Cadastrar Fotos":

    from PIL import Image
    _header("📷", "Cadastrar Fotos", "Upload e processamento automático via OCR")

    fotos = st.file_uploader(
        "Selecione as fotos (JPG/PNG)",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True
    )

    # ── Funções de extração ─────────────────────────────────────────────────

    def recortar_legenda(img):
        largura, altura = img.size
        return img.crop((int(largura * 0.45), int(altura * 0.58), largura, altura))

    def ler_degrau_claude(img_pil):
        """Lê o degrau na interseção da borda inferior da régua metálica com a trena."""
        import anthropic, io
        buf = io.BytesIO()
        img_pil.save(buf, format="JPEG", quality=85)
        img_b64 = base64.b64encode(buf.getvalue()).decode()
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=20,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}},
                    {"type": "text", "text": (
                        "Nesta foto há uma régua metálica horizontal (barra de alumínio brilhante) "
                        "e uma trena vertical amarela. "
                        "A trena tem duas escalas: use APENAS a escala em CM (lado esquerdo da fita). "
                        "A base da trena (zero) está no chão mais baixo. "
                        "Localize a BORDA INFERIOR da régua de alumínio — a linha onde termina o metal brilhante. "
                        "Leia o valor em CM onde essa borda inferior cruza a escala CM da trena. "
                        "Converta para MM multiplicando por 10. "
                        "Exemplo: se a borda inferior está na marca 4.2 CM, retorne 42. "
                        "Retorne SOMENTE o número inteiro em mm, sem texto."
                    )}
                ]
            }]
        )
        try:
            return float(resp.content[0].text.strip().replace("mm","").replace(",","."))
        except Exception:
            return None

    def ocr_claude(img_pil):
        """Extrai texto da legenda usando Claude Haiku — rápido e preciso."""
        import anthropic, io

        buf = io.BytesIO()
        img_pil.save(buf, format="JPEG", quality=85)
        img_b64 = base64.b64encode(buf.getvalue()).decode()

        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}
                    },
                    {
                        "type": "text",
                        "text": (
                            "Esta é uma foto de campo de inspeção de rodovia. "
                            "No canto inferior direito há uma legenda com texto sobreposto. "
                            "Leia e retorne EXATAMENTE o texto dessa legenda, incluindo: "
                            "data/hora, coordenadas GPS (todos os dígitos), KM, número da rodovia e sentido. "
                            "Retorne apenas o texto lido, sem comentários ou explicações. "
                            "Se houver coordenadas com muitas casas decimais, copie todos os dígitos."
                        )
                    }
                ]
            }]
        )
        return resp.content[0].text

    def extrair_rodovia(texto):
        m = re.search(r'SP\s*-?\s*(\d+)', texto, re.I)
        return f"SP-{m.group(1)}" if m else None

    def extrair_sentido(texto):
        t = texto.upper()
        if re.search(r'\bPS\b', t): return "Sul"
        if re.search(r'\bPN\b', t): return "Norte"
        if re.search(r'\bPL\b', t): return "Leste"
        if re.search(r'\bPO\b', t): return "Oeste"
        return None

    def extrair_data(texto):
        m = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
        return m.group(1) if m else None

    def utm_para_dd(zona_num, zona_letra, easting, northing):
        """Converte coordenadas UTM para graus decimais."""
        import math
        # Constantes WGS84
        a  = 6378137.0
        f  = 1 / 298.257223563
        b  = a * (1 - f)
        e2 = 1 - (b/a)**2
        e  = math.sqrt(e2)
        k0 = 0.9996

        # Hemisfério
        hemisferio_sul = zona_letra.upper() < 'N'
        if hemisferio_sul:
            northing = northing - 10000000.0

        x = easting - 500000.0
        meridiano_central = (zona_num - 1) * 6 - 180 + 3

        M  = northing / k0
        mu = M / (a * (1 - e2/4 - 3*e2**2/64 - 5*e2**3/256))

        e1  = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
        phi = (mu + (3*e1/2 - 27*e1**3/32)*math.sin(2*mu)
                  + (21*e1**2/16 - 55*e1**4/32)*math.sin(4*mu)
                  + (151*e1**3/96)*math.sin(6*mu)
                  + (1097*e1**4/512)*math.sin(8*mu))

        N1   = a / math.sqrt(1 - e2*math.sin(phi)**2)
        T1   = math.tan(phi)**2
        C1   = e2/(1-e2) * math.cos(phi)**2
        R1   = a*(1-e2) / (1 - e2*math.sin(phi)**2)**1.5
        D    = x / (N1*k0)

        lat = phi - (N1*math.tan(phi)/R1) * (
            D**2/2 - (5 + 3*T1 + 10*C1 - 4*C1**2 - 9*e2/(1-e2))*D**4/24
            + (61 + 90*T1 + 298*C1 + 45*T1**2 - 252*e2/(1-e2) - 3*C1**2)*D**6/720
        )
        lon = (D - (1 + 2*T1 + C1)*D**3/6
                 + (5 - 2*C1 + 28*T1 - 3*C1**2 + 8*e2/(1-e2) + 24*T1**2)*D**5/120
              ) / math.cos(phi)

        lat_dd = math.degrees(lat)
        lon_dd = math.degrees(lon) + meridiano_central

        return round(lat_dd, 8), round(lon_dd, 8)

    def extrair_coordenadas(texto):
        """
        Aceita todos os formatos:
          -23.289552 -49.157809          (sinal negativo)
          23.289552S 49.157809W          (letra S/W)
          22K 696581 7419224             (UTM)
          23°17'22"S 49°09'28"W          (graus/minutos/segundos)
        Sempre retorna (lat_negativa, lon_negativa) para Brasil
        """
        # Corrigir erros típicos do Tesseract
        texto = texto.replace(",", ".").replace("O", "0").replace("l", "1")

        # ── Padrão UTM: 22K 696581 7419224 ────────────────────────────────────
        m = re.search(r'(\d{1,2})([A-Za-z])\s+(\d{6,7})\s+(\d{6,7})', texto)
        if m:
            zona_num    = int(m.group(1))
            zona_letra  = m.group(2)
            easting     = float(m.group(3))
            northing    = float(m.group(4))
            # Validar faixas UTM Brasil
            if 18 <= zona_num <= 25 and 100000 <= easting <= 900000:
                try:
                    return utm_para_dd(zona_num, zona_letra, easting, northing)
                except Exception:
                    pass

        # ── Padrão 1: sinal negativo  -XX.XXXX -YY.XXXX ──────────────────────
        # Captura TODAS as casas decimais presentes na foto
        m = re.search(r'(-\d{1,3}\.\d+)\s+(-\d{1,3}\.\d+)', texto)
        if m:
            v1, v2 = float(m.group(1)), float(m.group(2))
            if 5 <= abs(v1) <= 34 and 34 <= abs(v2) <= 74:
                return round(v1, 15), round(v2, 15)

        # ── Padrão 2: XX.XXXXS YY.XXXXW  ou  XX.XXXXS YY.XXXXE ──────────────
        m = re.search(r'(\d{1,3}\.\d+)\s*([SsNn])\s*(\d{1,3}\.\d+)\s*([WwEe])', texto)
        if m:
            lat = float(m.group(1)) * (-1 if m.group(2).upper() == "S" else 1)
            lon = float(m.group(3)) * (-1 if m.group(4).upper() == "W" else 1)
            return round(lat, 15), round(lon, 15)

        # ── Padrão 3: graus minutos segundos  23°17'22"S  49°09'28"W ─────────
        m = re.search(
            r'(\d{1,3})[°\s](\d{1,2})[\'\s](\d{1,2}(?:\.\d+)?)["\'\s]*([SsNn])\s*'
            r'(\d{1,3})[°\s](\d{1,2})[\'\s](\d{1,2}(?:\.\d+)?)["\'\s]*([WwEe])',
            texto
        )
        if m:
            lat = (float(m.group(1)) + float(m.group(2))/60 + float(m.group(3))/3600)
            lon = (float(m.group(5)) + float(m.group(6))/60 + float(m.group(7))/3600)
            lat *= -1 if m.group(4).upper() == "S" else 1
            lon *= -1 if m.group(8).upper() == "W" else 1
            return lat, lon

        # ── Padrão 4: fallback — qualquer número com 5+ casas decimais ────────
        numeros = re.findall(r'-?\d+\.\d{5,}', texto)
        lat = lon = None
        for n in numeros:
            try:
                v = float(n)
                # Preservar todas as casas decimais originais
                if lon is None and 34 <= abs(v) <= 74: lon = round(-abs(v), 15); continue
                if lat is None and 5  <= abs(v) <= 34: lat = round(-abs(v), 15); continue
            except Exception:
                pass
        return lat, lon

    # ── Processar ───────────────────────────────────────────────────────────

    if fotos:
        if st.button("▶️ Processar Fotos", use_container_width=False):
            st.session_state["fila_fotos"]    = list(range(len(fotos)))
            st.session_state["dados_ocr"]     = []
            st.session_state["processando"]   = True
            st.rerun()

        # ── Processamento incremental (uma foto por rerun) ─────────────────
        if st.session_state.get("processando") and st.session_state.get("fila_fotos"):
            import PIL.ImageFilter

            fila  = st.session_state["fila_fotos"]
            dados = st.session_state["dados_ocr"]
            total = len(fotos)
            idx   = fila[0]
            foto  = fotos[idx]

            prog = (total - len(fila)) / total
            st.progress(prog, text=f"Processando {idx+1}/{total} — {foto.name}")

            try:
                img         = Image.open(foto)
                # Envia foto inteira para o Gemini — ele localiza a legenda sozinho
                texto    = ocr_claude(img)
                lat, lon = extrair_coordenadas(texto)
                dados.append({
                    "Arquivo": foto.name, "Rodovia": extrair_rodovia(texto),
                    "Sentido": extrair_sentido(texto), "Latitude": lat,
                    "Longitude": lon, "Data": extrair_data(texto),
                    "Degrau": None, "KM Real": None, "OCR Bruto": texto
                })
            except Exception as e:
                dados.append({
                    "Arquivo": foto.name, "Rodovia": None, "Sentido": None,
                    "Latitude": None, "Longitude": None, "Data": None,
                    "Degrau": None, "KM Real": None, "OCR Bruto": str(e)
                })

            # Avançar fila
            st.session_state["dados_ocr"]   = dados
            st.session_state["fila_fotos"]  = fila[1:]

            if st.session_state["fila_fotos"]:
                st.rerun()  # processa próxima foto
            else:
                # Todas processadas
                st.session_state["processando"]        = False
                st.session_state["resultado_editado"]  = pd.DataFrame(dados)
                st.session_state["fotos_dict"]         = {f.name: f for f in fotos}
                st.success(f"✅ {len(dados)} fotos processadas")

        # ── Tabela + Foto ────────────────────────────────────────────────────

        if "resultado_editado" in st.session_state:

            tabela = st.session_state["resultado_editado"]
            fotos_dict = st.session_state.get("fotos_dict", {})

            if "linha_selecionada" not in st.session_state:
                st.session_state["linha_selecionada"] = 0

            col_tabela, col_foto = st.columns([2, 1])

            with col_tabela:
                _section("📄 Resultados — clique para ver a foto")

                evento = st.dataframe(
                    tabela[["Arquivo", "Rodovia", "Sentido", "KM Real",
                             "Latitude", "Longitude", "Degrau", "Data", "OCR Bruto"]],
                    use_container_width=True, hide_index=False,
                    on_select="rerun", selection_mode="single-row",
                    key="tabela_sel",
                )
                sel_rows = evento.selection.rows if evento.selection.rows else []
                if sel_rows:
                    st.session_state["linha_selecionada"] = sel_rows[0]

                idx_ativo = st.session_state["linha_selecionada"]
                row_ativo = tabela.iloc[idx_ativo]

                st.markdown("<hr class='vr-divider'>", unsafe_allow_html=True)
                _section(f"✏️ Editando linha {idx_ativo} — {row_ativo['Arquivo']}")

                ed1, ed2, ed3 = st.columns(3)
                novo_lat = ed1.number_input(
                    "Latitude",  value=float(row_ativo["Latitude"])  if pd.notna(row_ativo["Latitude"])  else 0.0,
                    format="%.6f", key=f"lat_{idx_ativo}")
                novo_lon = ed2.number_input(
                    "Longitude", value=float(row_ativo["Longitude"]) if pd.notna(row_ativo["Longitude"]) else 0.0,
                    format="%.6f", key=f"lon_{idx_ativo}")
                novo_degrau = ed3.number_input(
                    "Degrau (mm)", value=float(row_ativo["Degrau"]) if pd.notna(row_ativo["Degrau"]) else 0.0,
                    min_value=0.0, step=1.0, key=f"deg_{idx_ativo}")

                if st.button("✅ Aplicar edição na linha", key="aplicar_edicao"):
                    tabela.at[idx_ativo, "Latitude"]  = novo_lat
                    tabela.at[idx_ativo, "Longitude"] = novo_lon
                    tabela.at[idx_ativo, "Degrau"]    = novo_degrau
                    st.session_state["resultado_editado"] = tabela
                    st.success(f"Linha {idx_ativo} atualizada.")
                    st.rerun()

            with col_foto:
                _section("📸 Foto selecionada")
                idx_foto  = st.session_state["linha_selecionada"]
                row_foto  = st.session_state["resultado_editado"].iloc[idx_foto]
                nome_foto = row_foto["Arquivo"]

                st.caption(f"**{nome_foto}**")
                st.markdown(
                    f"**Rodovia:** {row_foto.get('Rodovia', '—')}  \n"
                    f"**KM:** {row_foto.get('KM Real', '—')}  \n"
                    f"**Sentido:** {row_foto.get('Sentido', '—')}  \n"
                    f"**Degrau:** {row_foto.get('Degrau', '—')} mm"
                )
                if nome_foto in fotos_dict:
                    arq = fotos_dict[nome_foto]
                    arq.seek(0)
                    img_full = Image.open(arq)

                    # Tabs para organizar as 3 visões
                    tab1, tab2, tab3 = st.tabs(["📷 Completa", "🔍 Legenda OCR", "🔎 Zoom Trena"])

                    with tab1:
                        st.image(img_full, caption="Foto completa", use_column_width=True)

                    with tab2:
                        st.image(recortar_legenda(img_full), caption="Recorte OCR", use_column_width=True)

                    with tab3:
                        # Zoom automático na região da trena (centro-direita da foto)
                        # onde normalmente fica a fita métrica
                        larg, alt = img_full.size
                        # Crop centro vertical, terço direito horizontal
                        zoom_trena = img_full.crop((
                            int(larg * 0.25),  # começa em 25% da largura
                            int(alt  * 0.15),  # começa em 15% da altura
                            int(larg * 0.80),  # vai até 80% da largura
                            int(alt  * 0.85),  # vai até 85% da altura
                        ))
                        st.image(zoom_trena, caption="🔎 Zoom na trena — leia o valor e informe abaixo", use_column_width=True)
                        st.markdown(
                            f"""<div style="background:#1a2535; border-radius:8px; padding:10px;
                                          border:1px solid #F5A623; text-align:center; margin-top:6px;">
                                <span style="color:#F5A623; font-size:0.7rem; font-weight:700; 
                                             letter-spacing:1px;">DEGRAU LIDO NA TRENA</span><br>
                                <span style="color:#fff; font-size:2rem; font-weight:900;">
                                    {row_foto.get('Degrau', '—')} mm
                                </span>
                            </div>""",
                            unsafe_allow_html=True
                        )
                else:
                    st.info("Foto não disponível.")

            # ── Ações ─────────────────────────────────────────────────────────
            st.markdown("<hr class='vr-divider'>", unsafe_allow_html=True)
            col_b1, col_b2 = st.columns(2)

            with col_b1:
                if st.button("🔄 Recalcular KM", use_container_width=True):
                    tabela_calc = st.session_state["resultado_editado"].copy()
                    for idx, row in tabela_calc.iterrows():
                        try:
                            lat = float(row["Latitude"]); lon = float(row["Longitude"])
                            rod    = descobrir_rodovia(lat, lon)
                            km_real = calcular_km_real(rod, lat, lon)
                            tabela_calc.at[idx, "Rodovia"]  = rod
                            tabela_calc.at[idx, "KM Real"]  = km_real
                        except Exception:
                            pass
                    st.session_state["resultado_editado"] = tabela_calc
                    st.success("KM recalculado.")
                    st.rerun()

            with col_b2:
                if st.button("💾 Salvar Cadastro", use_container_width=True):
                    tabela_salvar = st.session_state["resultado_editado"].copy()
                    try:
                        con, tipo = get_conn()
                        cur = con.cursor()
                        ph = "%s" if tipo == "pg" else "?"
                        for _, row in tabela_salvar.iterrows():
                            cur.execute(
                                f"INSERT INTO fotos (arquivo,rodovia,km_real,sentido,latitude,longitude,degrau,data,ocr_bruto) VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})",
                                (row.get("Arquivo"), row.get("Rodovia"), row.get("KM Real"),
                                 row.get("Sentido"), row.get("Latitude"), row.get("Longitude"),
                                 row.get("Degrau"), row.get("Data"), row.get("OCR Bruto"))
                            )
                        con.commit(); con.close()
                        carregar_dados.clear()
                        st.success(f"✅ {len(tabela_salvar)} registros salvos.")
                        st.session_state.pop("resultado_editado", None)
                        st.session_state.pop("fotos_dict", None)
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

    st.markdown('<div class="vr-footer">Sistema de Inventário · Sistema de Inventário de Degraus</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# PÁGINA: IMPORTAR SD
# ═══════════════════════════════════════════════════════════════

elif pagina == "Importar SD":

    _header("📲", "Importar do SD", "Importe leituras coletadas offline pela régua inteligente")

    st.markdown("""
    <div style="background:#1a2535; border-radius:10px; padding:16px; margin-bottom:20px;
                border-left:4px solid #F5A623; font-size:0.9rem; line-height:1.6;">
        <b>Como usar:</b><br>
        1. Conecte o celular/notebook no WiFi <b>Regua-Degraus</b> (senha: <b>regua1234</b>)<br>
        2. Acesse <b>http://192.168.4.1</b> para ver a interface da régua<br>
        3. Após a coleta, remova o cartão SD e copie o arquivo <b>leituras.json</b><br>
        4. Faça upload do arquivo abaixo para importar para o banco
    </div>
    """, unsafe_allow_html=True)

    arquivo_sd = st.file_uploader(
        "Selecione o arquivo leituras.json do cartão SD",
        type=["json"],
        key="upload_sd"
    )

    if arquivo_sd:
        try:
            import json as json_lib
            conteudo = arquivo_sd.read().decode("utf-8")
            linhas = [l.strip() for l in conteudo.splitlines() if l.strip()]
            registros = [json_lib.loads(l) for l in linhas]

            df_sd = pd.DataFrame(registros)
            df_sd = df_sd.rename(columns={
                "degrau_mm": "Degrau (mm)",
                "latitude":  "Latitude",
                "longitude": "Longitude",
                "hdop":      "HDOP",
                "satelites": "Satélites",
                "data_hora": "Data/Hora"
            })

            # Métricas
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📋 Registros",      len(df_sd))
            m2.metric("📏 Degrau Médio",   f"{df_sd['Degrau (mm)'].mean():.1f} mm")
            m3.metric("⚠️ Degrau Máximo",  f"{df_sd['Degrau (mm)'].max():.1f} mm")
            m4.metric("🔴 Críticos >30mm", int((df_sd["Degrau (mm)"] > 30).sum()))

            st.markdown("<hr class='vr-divider'>", unsafe_allow_html=True)
            _section("📄 Registros importados")

            st.dataframe(
                df_sd[["Data/Hora", "Degrau (mm)", "Latitude", "Longitude", "HDOP", "Satélites"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Degrau (mm)": st.column_config.NumberColumn(format="%.1f mm"),
                    "Latitude":    st.column_config.NumberColumn(format="%.8f"),
                    "Longitude":   st.column_config.NumberColumn(format="%.8f"),
                    "HDOP":        st.column_config.NumberColumn(format="%.1f"),
                }
            )

            st.markdown("<hr class='vr-divider'>", unsafe_allow_html=True)

            if st.button("💾 Salvar todos no banco", use_container_width=False):
                try:
                    con, tipo = get_conn()
                    cur = con.cursor()
                    ph = "%s" if tipo == "pg" else "?"
                    salvos = 0
                    for _, row in df_sd.iterrows():
                        # Calcular KM real e rodovia via GPS
                        lat = row.get("Latitude")
                        lon = row.get("Longitude")
                        rodovia = None
                        km_real = None
                        try:
                            rodovia = descobrir_rodovia(lat, lon)
                            km_real = calcular_km_real(rodovia, lat, lon)
                        except Exception:
                            pass

                        cur.execute(
                            f"INSERT INTO fotos (arquivo,rodovia,km_real,sentido,latitude,longitude,degrau,data,ocr_bruto) VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})",
                            (
                                f"SD_{row.get('Data/Hora','').replace('/','').replace(' ','_').replace(':','')}",
                                rodovia,
                                km_real,
                                None,
                                lat,
                                lon,
                                row.get("Degrau (mm)"),
                                row.get("Data/Hora"),
                                f"Importado SD · HDOP:{row.get('HDOP','?')} · {row.get('Satélites','?')} satélites"
                            )
                        )
                        salvos += 1

                    con.commit()
                    con.close()
                    carregar_dados.clear()
                    st.success(f"✅ {salvos} registros salvos no banco!")

                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")

    st.markdown('<div class="vr-footer">Sistema de Inventário de Degraus · Todos os direitos reservados</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# PÁGINA: UPLOAD EM MASSA
# ═══════════════════════════════════════════════════════════════════

elif pagina == "Upload em Massa":

    from PIL import Image

    _header("📦", "Upload em Massa", "Processe e salve centenas de fotos de uma vez")

    st.markdown("""
    <div style="background:#1a2535; border-radius:10px; padding:16px; margin-bottom:20px;
                border-left:4px solid #F5A623; font-size:0.9rem; line-height:1.8;">
        <b>Como funciona:</b><br>
        1. Selecione todas as fotos de uma vez<br>
        2. O sistema processa automaticamente: OCR da legenda, coordenadas e KM<br>
        3. Revise o resumo e clique em <b>Salvar Tudo</b><br>
        4. Fotos com erro ficam marcadas para correção manual
    </div>
    """, unsafe_allow_html=True)

    fotos_massa = st.file_uploader(
        "Selecione as fotos (JPG/PNG) — sem limite de quantidade",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="upload_massa"
    )

    if fotos_massa:
        st.info(f"📸 {len(fotos_massa)} fotos selecionadas")

        col_op1, col_op2 = st.columns(2)
        ignorar_erros = col_op1.checkbox("Ignorar fotos com erro e continuar", value=True)
        salvar_auto   = col_op2.checkbox("Salvar automaticamente ao terminar", value=False)

        if st.button("▶️ Iniciar Processamento em Massa", use_container_width=True):
            st.session_state["massa_fila"]      = list(range(len(fotos_massa)))
            st.session_state["massa_dados"]     = []
            st.session_state["massa_erros"]     = []
            st.session_state["massa_total"]     = len(fotos_massa)
            st.session_state["massa_processando"] = True
            st.session_state["massa_salvar_auto"] = salvar_auto
            st.rerun()

    # ── Processamento incremental ──────────────────────────────────
    if st.session_state.get("massa_processando") and st.session_state.get("massa_fila") and fotos_massa:

        fila    = st.session_state["massa_fila"]
        dados   = st.session_state["massa_dados"]
        erros   = st.session_state["massa_erros"]
        total   = st.session_state["massa_total"]
        idx     = fila[0]
        foto    = fotos_massa[idx]
        feitos  = total - len(fila)

        # Barra de progresso
        prog = feitos / total
        st.progress(prog)
        st.markdown(
            f"<div style='text-align:center; color:#F5A623; font-weight:700; margin-bottom:8px;'>"
            f"Processando {feitos+1} de {total} — {foto.name}"
            f"</div>",
            unsafe_allow_html=True
        )

        # Métricas em tempo real
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("✅ Processados", feitos)
        mc2.metric("❌ Erros",       len(erros))
        mc3.metric("⏳ Restantes",   len(fila))

        try:
            img     = Image.open(foto)
            texto   = ocr_claude(img)
            lat, lon = extrair_coordenadas(texto)
            rodovia  = extrair_rodovia(texto)
            sentido  = extrair_sentido(texto)
            data     = extrair_data(texto)

            # Calcular KM automaticamente se coordenadas válidas
            km_real = None
            if lat and lon:
                try:
                    rod_calc = descobrir_rodovia(lat, lon)
                    km_real  = calcular_km_real(rod_calc, lat, lon)
                    if not rodovia:
                        rodovia = rod_calc
                except Exception:
                    pass

            dados.append({
                "Arquivo":  foto.name,
                "Rodovia":  rodovia,
                "KM Real":  km_real,
                "Sentido":  sentido,
                "Latitude": lat,
                "Longitude":lon,
                "Degrau":   None,
                "Data":     data,
                "OCR Bruto":texto,
                "Status":   "✅ OK" if lat and lon else "⚠️ Sem coordenada"
            })

        except Exception as e:
            erros.append(foto.name)
            dados.append({
                "Arquivo":  foto.name,
                "Rodovia":  None, "KM Real": None, "Sentido": None,
                "Latitude": None, "Longitude": None, "Degrau": None,
                "Data":     None, "OCR Bruto": str(e),
                "Status":   f"❌ Erro: {str(e)[:50]}"
            })

        st.session_state["massa_dados"] = dados
        st.session_state["massa_fila"]  = fila[1:]

        if st.session_state["massa_fila"]:
            st.rerun()
        else:
            st.session_state["massa_processando"] = False
            st.success(f"✅ Processamento concluído! {total - len(erros)} OK · {len(erros)} erros")

            # Salvar automaticamente se marcado
            if st.session_state.get("massa_salvar_auto"):
                st.session_state["massa_salvar_agora"] = True
            st.rerun()

    # ── Resultado + ações ──────────────────────────────────────────
    if (not st.session_state.get("massa_processando") and
            st.session_state.get("massa_dados") and
            not st.session_state.get("massa_fila")):

        dados  = st.session_state["massa_dados"]
        df_res = pd.DataFrame(dados)

        # Métricas finais
        total   = len(df_res)
        ok      = len(df_res[df_res["Status"].str.startswith("✅")])
        sem_coord = len(df_res[df_res["Status"].str.startswith("⚠️")])
        erros   = len(df_res[df_res["Status"].str.startswith("❌")])

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📸 Total",        total)
        m2.metric("✅ Com coord.",    ok)
        m3.metric("⚠️ Sem coord.",   sem_coord)
        m4.metric("❌ Erros",        erros)

        st.markdown("<hr class='vr-divider'>", unsafe_allow_html=True)
        _section("📄 Resultado do processamento")

        # Colorir status
        st.dataframe(
            df_res[["Arquivo", "Rodovia", "KM Real", "Sentido",
                    "Latitude", "Longitude", "Data", "Status"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "KM Real":   st.column_config.NumberColumn(format="%.3f"),
                "Latitude":  st.column_config.NumberColumn(format="%.8f"),
                "Longitude": st.column_config.NumberColumn(format="%.8f"),
                "Status":    st.column_config.TextColumn("Status"),
            }
        )

        st.markdown("<hr class='vr-divider'>", unsafe_allow_html=True)

        # Filtro do que salvar
        opcao_salvar = st.radio(
            "O que salvar no banco?",
            ["Apenas com coordenadas válidas", "Todos (incluindo erros)"],
            horizontal=True
        )

        ba, bb = st.columns(2)

        if ba.button("💾 Salvar no Banco", use_container_width=True):
            if opcao_salvar == "Apenas com coordenadas válidas":
                df_salvar = df_res[df_res["Latitude"].notna() & df_res["Longitude"].notna()]
            else:
                df_salvar = df_res

            try:
                con, tipo = get_conn()
                cur = con.cursor()
                ph  = "%s" if tipo == "pg" else "?"
                salvos = 0
                for _, row in df_salvar.iterrows():
                    cur.execute(
                        f"INSERT INTO fotos (arquivo,rodovia,km_real,sentido,latitude,longitude,degrau,data,ocr_bruto) VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})",
                        (row.get("Arquivo"), row.get("Rodovia"), row.get("KM Real"),
                         row.get("Sentido"), row.get("Latitude"), row.get("Longitude"),
                         row.get("Degrau"),  row.get("Data"),    row.get("OCR Bruto"))
                    )
                    salvos += 1
                con.commit(); con.close()
                carregar_dados.clear()
                st.success(f"✅ {salvos} registros salvos no banco!")
                st.session_state.pop("massa_dados", None)
                st.session_state.pop("massa_fila",  None)
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

        if bb.button("🗑️ Limpar e recomeçar", use_container_width=True):
            for k in ["massa_dados", "massa_fila", "massa_processando",
                      "massa_total", "massa_erros", "massa_salvar_auto"]:
                st.session_state.pop(k, None)
            st.rerun()

        # Exportar resultado como CSV
        csv = df_res[["Arquivo","Rodovia","KM Real","Sentido",
                      "Latitude","Longitude","Data","Status"]].to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Exportar resultado CSV", csv, "resultado_massa.csv", "text/csv")

    st.markdown('<div class="vr-footer">Sistema de Inventário de Degraus · Todos os direitos reservados</div>', unsafe_allow_html=True)
