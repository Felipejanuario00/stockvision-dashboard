from textwrap import dedent

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="StockVision | Controle de Estoque",
    page_icon="📦",
    layout="wide",
)

st.markdown(
    """
    <style>
        .stApp {
            background-color: #f4f7fb;
        }

        [data-testid="stMetric"] {
            background: white;
            border-left: 5px solid #1f77b4;
            padding: 18px;
            border-radius: 12px;
            box-shadow: 0 3px 12px rgba(0, 0, 0, 0.08);
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def moeda_brasileira(valor):
    formatado = f"{valor:,.2f}"
    formatado = formatado.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatado}"


@st.cache_data
def carregar_dados(arquivo):
    if arquivo is None:
        return pd.read_csv("estoque.csv")

    if arquivo.name.lower().endswith(".csv"):
        return pd.read_csv(arquivo)

    return pd.read_excel(arquivo)


banner = dedent(
    """
    <div style="
        background: linear-gradient(135deg, #102a43, #1f77b4);
        padding: 32px;
        border-radius: 18px;
        color: white;
        margin-bottom: 28px;
        box-shadow: 0 8px 24px rgba(16, 42, 67, 0.25);
    ">
        <div style="
            display: inline-block;
            background-color: #ffb703;
            color: #102a43;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: bold;
            margin-bottom: 12px;
        ">PROJETO DE PORTFÓLIO</div>
        <h1 style="margin: 0; font-size: 46px; color: white;">
            📦 StockVision
        </h1>
        <p style="margin: 8px 0 0; font-size: 18px; color: #d9ecff;">
            Transformando dados de estoque em decisões mais inteligentes.
        </p>
    </div>
    """
)

st.markdown(banner, unsafe_allow_html=True)

st.sidebar.title("⚙️ Painel de controle")

arquivo = st.sidebar.file_uploader(
    "Envie uma planilha CSV ou Excel",
    type=["csv", "xlsx"],
)

df = carregar_dados(arquivo)

colunas_obrigatorias = [
    "Produto",
    "Categoria",
    "Quantidade",
    "Estoque mínimo",
    "Preço unitário",
    "Entradas",
    "Saídas",
]

colunas_faltando = [
    coluna for coluna in colunas_obrigatorias if coluna not in df.columns
]

if colunas_faltando:
    st.error(
        "A planilha não possui todas as colunas necessárias: "
        + ", ".join(colunas_faltando)
    )
    st.stop()

df["Valor em estoque"] = df["Quantidade"] * df["Preço unitário"]

df["Status"] = df.apply(
    lambda linha: (
        "Crítico"
        if linha["Quantidade"] <= linha["Estoque mínimo"]
        else "Normal"
    ),
    axis=1,
)

categorias = st.sidebar.multiselect(
    "Categorias",
    options=sorted(df["Categoria"].unique()),
    default=sorted(df["Categoria"].unique()),
)

busca = st.sidebar.text_input(
    "Buscar produto",
    placeholder="Digite o nome do produto",
)

df_filtrado = df[df["Categoria"].isin(categorias)].copy()

if busca:
    df_filtrado = df_filtrado[
        df_filtrado["Produto"].str.contains(busca, case=False, na=False)
    ]

total_produtos = df_filtrado["Produto"].nunique()
total_unidades = int(df_filtrado["Quantidade"].sum())
valor_total = df_filtrado["Valor em estoque"].sum()
itens_criticos = int((df_filtrado["Status"] == "Crítico").sum())

col1, col2, col3, col4 = st.columns(4)

col1.metric("Produtos cadastrados", total_produtos)
col2.metric("Unidades em estoque", total_unidades)
col3.metric("Valor do estoque", moeda_brasileira(valor_total))
col4.metric("Itens críticos", itens_criticos)

st.divider()

aba1, aba2, aba3 = st.tabs(
    ["📊 Visão geral", "⚠️ Reposição", "📋 Dados completos"]
)

with aba1:
    grafico1, grafico2 = st.columns(2)

    with grafico1:
        st.subheader("Quantidade por produto")
        fig_quantidade = px.bar(
            df_filtrado,
            x="Produto",
            y="Quantidade",
            color="Status",
            color_discrete_map={
                "Normal": "#22a06b",
                "Crítico": "#e5484d",
            },
            template="plotly_white",
        )
        st.plotly_chart(fig_quantidade, use_container_width=True)

    with grafico2:
        st.subheader("Valor por categoria")
        valor_categoria = (
            df_filtrado
            .groupby("Categoria", as_index=False)["Valor em estoque"]
            .sum()
        )
        fig_categoria = px.pie(
            valor_categoria,
            names="Categoria",
            values="Valor em estoque",
            hole=0.55,
            template="plotly_white",
        )
        st.plotly_chart(fig_categoria, use_container_width=True)

    st.subheader("Movimentação de produtos")

    movimentacao = df_filtrado.melt(
        id_vars="Produto",
        value_vars=["Entradas", "Saídas"],
        var_name="Movimentação",
        value_name="Quantidade movimentada",
    )

    fig_movimentacao = px.bar(
        movimentacao,
        x="Produto",
        y="Quantidade movimentada",
        color="Movimentação",
        barmode="group",
        template="plotly_white",
    )
    st.plotly_chart(fig_movimentacao, use_container_width=True)

with aba2:
    estoque_critico = df_filtrado[df_filtrado["Status"] == "Crítico"].copy()

    estoque_critico["Sugestão de compra"] = (
        estoque_critico["Estoque mínimo"] * 2
        - estoque_critico["Quantidade"]
    ).clip(lower=0)

    if estoque_critico.empty:
        st.success("Todos os produtos estão com estoque saudável.")
    else:
        st.warning(
            f"{len(estoque_critico)} produto(s) precisam de atenção."
        )

        st.dataframe(
            estoque_critico[
                [
                    "Produto",
                    "Categoria",
                    "Quantidade",
                    "Estoque mínimo",
                    "Sugestão de compra",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

with aba3:
    st.dataframe(
        df_filtrado,
        use_container_width=True,
        hide_index=True,
    )

    relatorio_csv = df_filtrado.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label="⬇️ Baixar relatório filtrado",
        data=relatorio_csv,
        file_name="relatorio_estoque.csv",
        mime="text/csv",
    )

st.caption(
    "Projeto de portfólio desenvolvido com Python, Pandas, Streamlit e Plotly."
)
