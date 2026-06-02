import pandas as pd
import streamlit as st
import plotly.express as px
import folium
import zipfile
import xml.etree.ElementTree as ET
import numpy as np
import re
import sqlite3

from streamlit_folium import st_folium

# =========================================
# Página
# =========================================

st.set_page_config(
    page_title="Inventário de Degraus",
    layout="wide"
)

pagina = st.sidebar.radio(
    "Menu",
    [
        "Dashboard",
        "Cadastrar Fotos"
    ]
)

# =========================================
# KMZ
# =========================================

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

                registro = (km, lat, lon)
                rodovias[rodovia].append(registro)

                # FIX: estava com indentação incorreta — deve estar dentro do for pm
                todos_os_marcos.append({
                    "rodovia": rodovia,
                    "km": km,
                    "lat": lat,
                    "lon": lon
                })

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
    melhor_dist = None
    melhor_km = None

    for i in range(len(dados) - 1):
        km1, lat1, lon1 = dados[i]
        km2, lat2, lon2 = dados[i + 1]

        abx = lon2 - lon1
        aby = lat2 - lat1
        apx = lon - lon1
        apy = lat - lat1

        ab2 = abx * abx + aby * aby
        if ab2 == 0:
            continue

        t = (apx * abx + apy * aby) / ab2
        t = max(0, min(1, t))

        dist = np.sqrt(
            (lon - (lon1 + abx * t))**2 +
            (lat - (lat1 + aby * t))**2
        )

        km_real = km1 + (km2 - km1) * t

        if melhor_dist is None or dist < melhor_dist:
            melhor_dist = dist
            melhor_km = km_real

    return round(melhor_km, 3)


# =========================================
# Carregar dados do banco
# =========================================

@st.cache_data
def carregar_dados():
    con = sqlite3.connect("banco.db")
    try:
        df = pd.read_sql("SELECT * FROM fotos", con)
    except Exception:
        df = pd.DataFrame(columns=[
            "arquivo", "rodovia", "km_real", "sentido",
            "latitude", "longitude", "degrau", "data", "ocr_bruto"
        ])
    con.close()
    return df


df = carregar_dados()

# Padronizar nomes para o dashboard
df = df.rename(columns={
    "arquivo": "Arquivo",
    "rodovia": "Rodovia Encontrada",
    "km_real": "KM Real",
    "sentido": "Sentido",
    "latitude": "Latitude",
    "longitude": "Longitude",
    "degrau": "Degrau",
    "data": "Data"
})

# =========================================
# Tratamento
# =========================================

if len(df):
    df["KM Real"] = pd.to_numeric(df["KM Real"], errors="coerce")
    df["Degrau"] = pd.to_numeric(df["Degrau"], errors="coerce")

# =========================================
# Sidebar – Filtros
# =========================================

st.sidebar.title("Filtros")

rodovia_filtro = st.sidebar.multiselect(
    "Rodovia",
    sorted(df["Rodovia Encontrada"].dropna().unique())
)

sentido_filtro = st.sidebar.multiselect(
    "Sentido",
    sorted(df["Sentido"].dropna().unique())
)

km_ini = st.sidebar.number_input("KM Inicial", value=0.0)
km_fim = st.sidebar.number_input(
    "KM Final",
    value=float(df["KM Real"].max()) if len(df) and df["KM Real"].notna().any() else 0.0
)

# =========================================
# Filtrar
# =========================================

dff = df.copy()

if rodovia_filtro:
    dff = dff[dff["Rodovia Encontrada"].isin(rodovia_filtro)]

if sentido_filtro:
    dff = dff[dff["Sentido"].isin(sentido_filtro)]

dff = dff[(dff["KM Real"] >= km_ini) & (dff["KM Real"] <= km_fim)]

# =========================================
# DASHBOARD
# =========================================

if pagina == "Dashboard":

    st.title("🚧 Inventário de Degraus")

    # Cards
    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Fotos", len(dff))

    c2.metric(
        "Degrau Médio",
        round(dff["Degrau"].mean(), 1) if dff["Degrau"].notna().any() else "—"
    )

    c3.metric(
        "Degrau Máximo",
        round(dff["Degrau"].max(), 1) if dff["Degrau"].notna().any() else "—"
    )

    c4.metric(
        "Críticos (>30mm)",
        len(dff[dff["Degrau"] > 30])
    )

    # Layout principal
    col_mapa, col_graf = st.columns([1.3, 1])

    # Mapa
    with col_mapa:
        st.subheader("Mapa")

        dff_mapa = dff.dropna(subset=["Latitude", "Longitude"])

        if len(dff_mapa):
            lat_center = dff_mapa["Latitude"].mean()
            lon_center = dff_mapa["Longitude"].mean()

            mapa = folium.Map(location=[lat_center, lon_center], zoom_start=11)

            for _, row in dff_mapa.iterrows():
                degrau = row["Degrau"]
                cor = "green"
                if pd.notna(degrau):
                    if degrau > 30:
                        cor = "red"
                    elif degrau > 20:
                        cor = "orange"
                    elif degrau > 10:
                        cor = "yellow"

                popup = f"""
                <b>Arquivo:</b> {row['Arquivo']}<br>
                <b>Rodovia:</b> {row['Rodovia Encontrada']}<br>
                <b>KM:</b> {row['KM Real']}<br>
                <b>Degrau:</b> {row['Degrau']} mm<br>
                <b>Sentido:</b> {row['Sentido']}
                """

                folium.CircleMarker(
                    location=[row["Latitude"], row["Longitude"]],
                    radius=4,
                    color=cor,
                    fill=True,
                    popup=popup
                ).add_to(mapa)

            st_folium(mapa, width=900, height=650)
        else:
            st.info("Nenhum ponto com coordenadas válidas para exibir no mapa.")

    # Gráfico Degrau x KM
    with col_graf:
        st.subheader("Degrau x KM")

        fig = px.scatter(
            dff,
            x="KM Real",
            y="Degrau",
            color="Rodovia Encontrada",
            hover_data=["Arquivo"]
        )
        st.plotly_chart(fig, use_container_width=True)

    # Linha 2 de gráficos
    g1, g2 = st.columns(2)

    with g1:
        fig = px.histogram(dff, x="Rodovia Encontrada", title="Fotos por Rodovia")
        st.plotly_chart(fig, use_container_width=True)

    with g2:
        fig = px.histogram(dff, x="Sentido", title="Fotos por Sentido")
        st.plotly_chart(fig, use_container_width=True)

    # Histograma de degraus
    fig = px.histogram(dff, x="Degrau", nbins=20, title="Distribuição dos Degraus")
    st.plotly_chart(fig, use_container_width=True)

    # Ranking
    st.subheader("Top 20 Maiores Degraus")

    ranking = dff.sort_values("Degrau", ascending=False)

    st.dataframe(
        ranking[["Rodovia Encontrada", "KM Real", "Degrau", "Sentido", "Arquivo"]].head(20),
        use_container_width=True
    )

# =========================================
# CADASTRO
# =========================================

elif pagina == "Cadastrar Fotos":

    from PIL import Image
    import easyocr

    st.title("📷 Cadastrar Fotos")

    fotos = st.file_uploader(
        "Selecione as fotos",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True
    )

    @st.cache_resource
    def carregar_ocr():
        return easyocr.Reader(['en'], gpu=False)

    reader = carregar_ocr()

    # ─── Funções de extração ──────────────────────────────────────────────────

    def recortar_legenda(img):
        largura, altura = img.size
        x1 = int(largura * 0.60)
        y1 = int(altura * 0.65)
        return img.crop((x1, y1, largura, altura))

    def extrair_rodovia(texto):
        m = re.search(r'SP\s*-?\s*(\d+)', texto, re.I)
        if m:
            return f"SP-{m.group(1)}"
        return None

    def extrair_sentido(texto):
        texto = texto.upper()
        if re.search(r'\bPS\b', texto):
            return "Sul"
        if re.search(r'\bPN\b', texto):
            return "Norte"
        if re.search(r'\bPL\b', texto):
            return "Leste"
        if re.search(r'\bPO\b', texto):
            return "Oeste"
        return None

    def extrair_data(texto):
        m = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
        if m:
            return m.group(1)
        return None

    def extrair_coordenadas(texto):
        texto = texto.replace(",", ".")
        numeros = re.findall(r'-?\d*\.\d{5,}', texto)
        lat = None
        lon = None

        for n in numeros:
            try:
                valor = float(n)
                if lon is None and 40 <= abs(valor) <= 80:
                    lon = -abs(valor)
                    continue
                if lat is None and 18 <= abs(valor) <= 35:
                    lat = -abs(valor)
                    continue
                if lat is None and 1 <= abs(valor) <= 5:
                    lat = -(20 + abs(valor))
                    continue
                if lat is None and 0 < abs(valor) < 1:
                    lat = -(22 + abs(valor))
            except Exception:
                pass

        return lat, lon

    # ─── Processar fotos ──────────────────────────────────────────────────────

    if fotos:

        if st.button("Processar Fotos"):

            dados = []
            barra = st.progress(0)
            total = len(fotos)

            for i, foto in enumerate(fotos):
                try:
                    img = Image.open(foto)
                    legenda = recortar_legenda(img)

                    texto_lido = reader.readtext(
                        np.array(legenda),
                        detail=0,
                        paragraph=False
                    )

                    texto = "\n".join(texto_lido)

                    dados.append({
                        "Arquivo":   foto.name,
                        "Rodovia":   extrair_rodovia(texto),
                        "Sentido":   extrair_sentido(texto),
                        "Latitude":  extrair_coordenadas(texto)[0],
                        "Longitude": extrair_coordenadas(texto)[1],
                        "Data":      extrair_data(texto),
                        "Degrau":    None,          # editável pelo usuário
                        "KM Real":   None,
                        "OCR Bruto": texto
                    })

                except Exception as e:
                    dados.append({
                        "Arquivo":   foto.name,
                        "Rodovia":   None,
                        "Sentido":   None,
                        "Latitude":  None,
                        "Longitude": None,
                        "Data":      None,
                        "Degrau":    None,
                        "KM Real":   None,
                        "OCR Bruto": str(e)
                    })

                barra.progress((i + 1) / total)

            st.session_state["resultado_editado"] = pd.DataFrame(dados)
            # Guardar as imagens originais para exibição na tabela
            st.session_state["fotos_dict"] = {
                f.name: f for f in fotos
            }
            st.success(f"{len(dados)} fotos processadas")

        # ─── Tabela editável + visualizador de foto ──────────────────────────

        if "resultado_editado" in st.session_state:

            tabela = st.session_state["resultado_editado"]
            fotos_dict = st.session_state.get("fotos_dict", {})

            nomes = tabela["Arquivo"].tolist()

            # Layout: tabela à esquerda, foto à direita
            col_tabela, col_foto = st.columns([2, 1])

            with col_tabela:
                st.markdown("**Edite Latitude, Longitude e Degrau conforme necessário:**")

                tabela_editada = st.data_editor(
                    tabela,
                    use_container_width=True,
                    num_rows="fixed",
                    key="editor_principal",
                    column_config={
                        "Latitude": st.column_config.NumberColumn(
                            "Latitude",
                            help="Latitude capturada pelo OCR (editável)",
                            format="%.6f",
                        ),
                        "Longitude": st.column_config.NumberColumn(
                            "Longitude",
                            help="Longitude capturada pelo OCR (editável)",
                            format="%.6f",
                        ),
                        "Degrau": st.column_config.NumberColumn(
                            "Degrau (mm)",
                            help="Altura do degrau em milímetros (editável)",
                            min_value=0,
                            format="%d mm",
                        ),
                        # colunas somente-leitura
                        "Arquivo":   st.column_config.TextColumn(disabled=True),
                        "Rodovia":   st.column_config.TextColumn(disabled=True),
                        "Sentido":   st.column_config.TextColumn(disabled=True),
                        "Data":      st.column_config.TextColumn(disabled=True),
                        "KM Real":   st.column_config.NumberColumn(disabled=True, format="%.3f"),
                        "OCR Bruto": st.column_config.TextColumn(disabled=True),
                    }
                )

                # Salvar edições de volta no session_state
                st.session_state["resultado_editado"] = tabela_editada

            # ─── Painel de foto à direita ──────────────────────────────────────
            with col_foto:
                st.markdown("**📸 Visualizar foto**")

                foto_selecionada = st.selectbox(
                    "Selecione a linha para ver a foto:",
                    options=nomes,
                    key="foto_sel"
                )

                idx_sel = nomes.index(foto_selecionada)
                row_sel = st.session_state["resultado_editado"].iloc[idx_sel]

                # Exibir metadados resumidos
                st.markdown(
                    f"**Rodovia:** {row_sel.get('Rodovia', '—')}  \n"
                    f"**KM:** {row_sel.get('KM Real', '—')}  \n"
                    f"**Sentido:** {row_sel.get('Sentido', '—')}  \n"
                    f"**Degrau:** {row_sel.get('Degrau', '—')} mm  \n"
                    f"**OCR:** {str(row_sel.get('OCR Bruto', ''))[:200]}"
                )

                if foto_selecionada in fotos_dict:
                    arq = fotos_dict[foto_selecionada]
                    arq.seek(0)
                    img_full = Image.open(arq)

                    # Foto completa
                    st.image(img_full, caption="Foto completa", use_container_width=True)

                    # Recorte da legenda (mesmo crop do OCR)
                    legenda_crop = recortar_legenda(img_full)
                    st.image(
                        legenda_crop,
                        caption="🔍 Recorte da legenda (OCR)",
                        use_container_width=True
                    )
                else:
                    st.info("Foto não disponível (recarregue e reprocesse as imagens).")

            # ─── Botões de ação ────────────────────────────────────────────────

            col_b1, col_b2 = st.columns(2)

            with col_b1:
                if st.button("🔄 Recalcular KM", use_container_width=True):

                    tabela_calc = st.session_state["resultado_editado"].copy()

                    for idx, row in tabela_calc.iterrows():
                        try:
                            lat = float(row["Latitude"])
                            lon = float(row["Longitude"])
                            rod = descobrir_rodovia(lat, lon)
                            km_real = calcular_km_real(rod, lat, lon)
                            tabela_calc.at[idx, "Rodovia"] = rod
                            tabela_calc.at[idx, "KM Real"] = km_real
                        except Exception:
                            pass

                    st.session_state["resultado_editado"] = tabela_calc
                    st.success("KM recalculado com sucesso.")
                    st.rerun()

            with col_b2:
                if st.button("💾 Salvar Cadastro", use_container_width=True):

                    tabela_salvar = st.session_state["resultado_editado"].copy()

                    try:
                        con = sqlite3.connect("banco.db")
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

                        for _, row in tabela_salvar.iterrows():
                            cur.execute("""
                                INSERT INTO fotos
                                (arquivo, rodovia, km_real, sentido,
                                 latitude, longitude, degrau, data, ocr_bruto)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                row.get("Arquivo"),
                                row.get("Rodovia"),
                                row.get("KM Real"),
                                row.get("Sentido"),
                                row.get("Latitude"),
                                row.get("Longitude"),
                                row.get("Degrau"),
                                row.get("Data"),
                                row.get("OCR Bruto"),
                            ))

                        con.commit()
                        con.close()

                        carregar_dados.clear()

                        st.success(f"{len(tabela_salvar)} registros salvos no banco.")
                        st.session_state.pop("resultado_editado", None)
                        st.session_state.pop("fotos_dict", None)

                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
