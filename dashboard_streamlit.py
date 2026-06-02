import pandas as pd
import streamlit as st
import plotly.express as px
import folium
import zipfile
import xml.etree.ElementTree as ET
import numpy as np
import re

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

# =========================================
# KMZ
# =========================================

@st.cache_resource
def carregar_kmz():

    todos_os_marcos = []
    rodovias = {}

    with zipfile.ZipFile(
        "kmz_rodovias.kmz",
        "r"
    ) as z:

        kml_file = [
            x for x in z.namelist()
            if x.endswith(".kml")
        ][0]

        conteudo = z.read(
            kml_file
        )

    rootxml = ET.fromstring(
        conteudo
    )

    ns = {
        "kml":
        "http://www.opengis.net/kml/2.2"
    }

    def normalizar_rodovia(txt):

        txt = str(txt).upper()

        m = re.search(
            r'(SPA\s*\d+/\d+)',
            txt
        )

        if m:
            return m.group(1).replace(
                " ",
                "-"
            )

        m = re.search(
            r'(SP\s*\d+)',
            txt
        )

        if m:
            return m.group(1).replace(
                " ",
                "-"
            )

        return txt.strip()

    def process_folder(folder):

        nome = folder.find(
            "kml:name",
            ns
        )

        nome_folder = (
            nome.text
            if nome is not None
            else ""
        )

        rodovia = None

        m = re.search(
            r'(SPA\s*\d+/\d+|SP\s*\d+)',
            nome_folder.upper()
        )

        if m:

            rodovia = normalizar_rodovia(
                m.group()
            )

        if rodovia:

            rodovias.setdefault(
                rodovia,
                []
            )

            for pm in folder.findall(
                "kml:Placemark",
                ns
            ):

                nm = pm.find(
                    "kml:name",
                    ns
                )

                pt = pm.find(
                    ".//kml:Point/kml:coordinates",
                    ns
                )

                if nm is None or pt is None:
                    continue

                km_match = re.search(
                    r'(\d+(?:[.,]\d+)?)',
                    str(nm.text)
                )

                if not km_match:
                    continue

                km = float(
                    km_match.group(1)
                    .replace(",", ".")
                )

                lon, lat, *_ = map(
                    float,
                    pt.text.strip().split(",")
                )

                registro = (
                    km,
                    lat,
                    lon
                )

                rodovias[
                    rodovia
                ].append(
                    registro
                )

                todos_os_marcos.append({

                    "rodovia": rodovia,

                    "km": km,

                    "lat": lat,

                    "lon": lon

                })

        for sub in folder.findall(
            "kml:Folder",
            ns
        ):
            process_folder(sub)

    for folder in rootxml.findall(
        ".//kml:Folder",
        ns
    ):
        process_folder(folder)

    for rodovia in rodovias:

        rodovias[
            rodovia
        ].sort(
            key=lambda x: x[0]
        )

    return (
        todos_os_marcos,
        rodovias
    )

TODOS_OS_MARCOS, RODOVIAS = carregar_kmz()
   def distancia(
    lat1,
    lon1,
    lat2,
    lon2
):

    return np.sqrt(
        (lat1 - lat2)**2 +
        (lon1 - lon2)**2
    )

def descobrir_rodovia(
    lat,
    lon
):

    menor = None

    for marco in TODOS_OS_MARCOS:

        d = distancia(
            lat,
            lon,
            marco["lat"],
            marco["lon"]
        )

        if (
            menor is None
            or d < menor[0]
        ):

            menor = (
                d,
                marco["rodovia"]
            )

    return menor[1]

def calcular_km_real(
    rodovia,
    lat,
    lon
):

    dados = RODOVIAS[
        rodovia
    ]

    melhor_dist = None
    melhor_km = None

    for i in range(
        len(dados)-1
    ):

        km1, lat1, lon1 = dados[i]
        km2, lat2, lon2 = dados[i+1]

        abx = lon2 - lon1
        aby = lat2 - lat1

        apx = lon - lon1
        apy = lat - lat1

        ab2 = (
            abx*abx +
            aby*aby
        )

        if ab2 == 0:
            continue

        t = (
            apx*abx +
            apy*aby
        ) / ab2

        t = max(
            0,
            min(1, t)
        )

        dist = np.sqrt(
            (lon -
             (lon1 + abx*t)
            )**2 +
            (
                lat -
                (lat1 + aby*t)
            )**2
        )

        km_real = (
            km1 +
            (km2-km1)*t
        )

        if (
            melhor_dist is None
            or dist < melhor_dist
        ):

            melhor_dist = dist
            melhor_km = km_real

    return round(
        melhor_km,
        3
    ) 
)
import sqlite3

@st.cache_data
def carregar_dados():

    con = sqlite3.connect(
        "banco.db"
    )

    try:

        df = pd.read_sql(
            "SELECT * FROM fotos",
            con
        )

    except:

        df = pd.DataFrame(
            columns=[
                "arquivo",
                "rodovia",
                "km_real",
                "sentido",
                "latitude",
                "longitude",
                "degrau",
                "data",
                "ocr_bruto"
            ]
        )

    con.close()

    return df

df = carregar_dados()

# padronizar nomes para o dashboard antigo

df = df.rename(
    columns={
        "arquivo":"Arquivo",
        "rodovia":"Rodovia Encontrada",
        "km_real":"KM Real",
        "sentido":"Sentido",
        "latitude":"Latitude",
        "longitude":"Longitude",
        "degrau":"Degrau",
        "data":"Data"
    }
)
# =========================================
# Tratamento
# =========================================

if len(df):

    df["KM Real"] = pd.to_numeric(
        df["KM Real"],
        errors="coerce"
    )

    df["Degrau"] = pd.to_numeric(
        df["Degrau"],
        errors="coerce"
    )
# =========================================
# Sidebar
# =========================================

st.sidebar.title("Filtros")

rodovia = st.sidebar.multiselect(
    "Rodovia",

    sorted(
        df[
            "Rodovia Encontrada"
        ]
        .dropna()
        .unique()
    )
)

sentido = st.sidebar.multiselect(
    "Sentido",

    sorted(
        df[
            "Sentido"
        ]
        .dropna()
        .unique()
    )
)

km_ini = st.sidebar.number_input(
    "KM Inicial",
    value=0.0
)

km_fim = st.sidebar.number_input(
    "KM Final",
    value=float(
        df["KM Real"].max()
    )
)

# =========================================
# Filtrar
# =========================================

dff = df.copy()

if rodovia:

    dff = dff[
        dff[
            "Rodovia Encontrada"
        ]
        .isin(
            rodovia
        )
    ]

if sentido:

    dff = dff[
        dff[
            "Sentido"
        ]
        .isin(
            sentido
        )
    ]

dff = dff[
    (
        dff["KM Real"] >= km_ini
    )
    &
    (
        dff["KM Real"] <= km_fim
    )
]

# =========================================
# Título
# =========================================

if pagina == "Dashboard":

    st.title(
        "🚧 Inventário de Degraus"
    )

# =========================================
# Cards
# =========================================

c1,c2,c3,c4 = st.columns(4)

c1.metric(
    "Fotos",
    len(dff)
)

c2.metric(
    "Degrau Médio",
    round(
        dff["Degrau"].mean(),
        1
    )
)

c3.metric(
    "Degrau Máximo",
    round(
        dff["Degrau"].max(),
        1
    )
)

c4.metric(
    "Críticos (>30mm)",
    len(
        dff[
            dff["Degrau"] > 30
        ]
    )
)

# =========================================
# Layout principal
# =========================================

col_mapa, col_graf = st.columns(
    [1.3,1]
)

# =========================================
# MAPA
# =========================================

with col_mapa:

    st.subheader(
        "Mapa"
    )

    if len(dff):

        lat = dff[
            "Latitude"
        ].mean()

        lon = dff[
            "Longitude"
        ].mean()

        mapa = folium.Map(
            location=[
                lat,
                lon
            ],
            zoom_start=11
        )

        for _, row in dff.iterrows():

            degrau = row["Degrau"]

            cor = "green"

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
                location=[
                    row["Latitude"],
                    row["Longitude"]
                ],
                radius=4,
                color=cor,
                fill=True,
                popup=popup
            ).add_to(
                mapa
            )

        st_folium(
            mapa,
            width=900,
            height=650
        )

# =========================================
# GRÁFICOS
# =========================================

with col_graf:

    st.subheader(
        "Degrau x KM"
    )

    fig = px.scatter(
        dff,
        x="KM Real",
        y="Degrau",

        color="Rodovia Encontrada",

        hover_data=[
            "Arquivo"
        ]
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# =========================================
# LINHA 2
# =========================================

g1,g2 = st.columns(2)

with g1:

    fig = px.histogram(
        dff,
        x="Rodovia Encontrada",
        title="Fotos por Rodovia"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

with g2:

    fig = px.histogram(
        dff,
        x="Sentido",
        title="Fotos por Sentido"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# =========================================
# HISTOGRAMA
# =========================================

fig = px.histogram(
    dff,
    x="Degrau",

    nbins=20,

    title="Distribuição dos Degraus"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# =========================================
# Piores pontos
# =========================================

st.subheader(
    "Top 20 Maiores Degraus"
)

ranking = dff.sort_values(
    "Degrau",
    ascending=False
)

st.dataframe(

    ranking[
        [
            "Rodovia Encontrada",
            "KM Real",
            "Degrau",
            "Sentido",
            "Arquivo"
        ]
    ]
    .head(20),

    use_container_width=True
)
# =========================================
# CADASTRO
# =========================================

if pagina == "Cadastrar Fotos":

    import re
    import numpy as np
    import pandas as pd
    from PIL import Image
    import easyocr

    st.title(
        "📷 Cadastrar Fotos"
    )

    fotos = st.file_uploader(

        "Selecione as fotos",

        type=[
            "jpg",
            "jpeg",
            "png"
        ],

        accept_multiple_files=True

    )

    # =====================================
    # OCR
    # =====================================

    @st.cache_resource
    def carregar_ocr():

        return easyocr.Reader(
            ['en'],
            gpu=False
        )

    reader = carregar_ocr()

    # =====================================
    # Funções
    # =====================================

    def recortar_legenda(img):

        largura, altura = img.size

        x1 = int(largura * 0.60)
        y1 = int(altura * 0.65)

        return img.crop(
            (
                x1,
                y1,
                largura,
                altura
            )
        )

    def extrair_rodovia(texto):

        m = re.search(
            r'SP\s*-?\s*(\d+)',
            texto,
            re.I
        )

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

        m = re.search(
            r'(\d{2}/\d{2}/\d{4})',
            texto
        )

        if m:
            return m.group(1)

        return None

    def extrair_coordenadas(texto):

        texto = texto.replace(",", ".")

        numeros = re.findall(
            r'-?\d*\.\d{5,}',
            texto
        )

        lat = None
        lon = None

        for n in numeros:

            try:

                valor = float(n)

                if (
                    lon is None and
                    40 <= abs(valor) <= 80
                ):

                    lon = -abs(valor)

                    continue

                if (
                    lat is None and
                    18 <= abs(valor) <= 35
                ):

                    lat = -abs(valor)

                    continue

                if (
                    lat is None and
                    1 <= abs(valor) <= 5
                ):

                    lat = -(20 + abs(valor))

                    continue

                if (
                    lat is None and
                    0 < abs(valor) < 1
                ):

                    lat = -(22 + abs(valor))

            except:
                pass

        return lat, lon

# =====================================
# PROCESSAR
# =====================================

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

                    rodovia = extrair_rodovia(texto)

                    sentido = extrair_sentido(texto)

                    data = extrair_data(texto)

                    lat, lon = extrair_coordenadas(texto)

                    dados.append({

                        "Arquivo": foto.name,
                        "Rodovia": rodovia,
                        "Sentido": sentido,
                        "Latitude": lat,
                        "Longitude": lon,
                        "Data": data,
                        "OCR Bruto": texto

                    })

                except Exception as e:

                    dados.append({

                        "Arquivo": foto.name,
                        "Rodovia": None,
                        "Sentido": None,
                        "Latitude": None,
                        "Longitude": None,
                        "Data": None,
                        "OCR Bruto": str(e)

                    })

                barra.progress((i + 1) / total)

            resultado = pd.DataFrame(dados)

            resultado["KM Real"] = None
            resultado["Degrau"] = None

            st.success(
                f"{len(resultado)} fotos processadas"
            )

            resultado_editado = st.data_editor(
                resultado,
                use_container_width=True,
                num_rows="fixed",
                key="editor_ocr"
            )

            st.session_state[
                "resultado_editado"
            ] = resultado_editado

            if st.button(
    "Recalcular KM"
):

    tabela = st.session_state[
        "resultado_editado"
    ].copy()

    for idx, row in tabela.iterrows():

        try:

            lat = float(
                row["Latitude"]
            )

            lon = float(
                row["Longitude"]
            )

            rodovia = descobrir_rodovia(
                lat,
                lon
            )

            km_real = calcular_km_real(
                rodovia,
                lat,
                lon
            )

            tabela.at[
                idx,
                "Rodovia"
            ] = rodovia

            tabela.at[
                idx,
                "KM Real"
            ] = km_real

        except:
            pass

    st.session_state[
        "resultado_editado"
    ] = tabela

    st.success(
        "KM recalculado."
    )

    st.data_editor(
        tabela,
        use_container_width=True,
        key="editor_ocr_recalc"
    )

            if st.button(
                "Salvar Cadastro"
            ):

                st.warning(
                    "Integração SQLite ainda será feita"
                )
