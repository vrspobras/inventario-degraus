import pandas as pd
import streamlit as st
import plotly.express as px
import folium

from streamlit_folium import st_folium

# =========================================
# Página
# =========================================

st.set_page_config(
    page_title="Inventário de Degraus",
    layout="wide"
)

# =========================================
# Selecionar planilha
# =========================================

@st.cache_data
def carregar():

    st.sidebar.title("Dados")

arquivo = st.sidebar.file_uploader(
    "Selecione fotos_processadas_km_real.xlsx",
    type=["xlsx"]
)

if arquivo is None:

    st.info(
        "Selecione a planilha para iniciar."
    )

    st.stop()

df = pd.read_excel(arquivo)

    return df

df = carregar()

# =========================================
# Tratamento
# =========================================

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
