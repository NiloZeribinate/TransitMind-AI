
import pandas as pd
import streamlit as st


def desenhar_grafico(
    dados: pd.DataFrame,
    coluna: str,
    titulo: str,
    tipo: str = "linha",
    eixo_x: str = "horario",
    horizontal: bool = False,
    ordenar: bool | str = True,
    altura: int = 240,
) -> None:
    """Renderiza um gráfico de linha ou barras."""
    st.markdown(f"**{titulo}**")

    if tipo == "linha":
        st.line_chart(
            dados,
            x=eixo_x,
            y=coluna,
            height=altura,
        )

    elif tipo == "barra":
        st.bar_chart(
            dados,
            x=eixo_x,
            y=coluna,
            horizontal=horizontal,
            sort=ordenar,
            height=altura,
        )

    else:
        raise ValueError(f"Tipo de gráfico inválido: {tipo}")


def renderizar_validacoes(resultado: dict) -> None:
    """Renderiza as três métricas da análise por veículo."""
    dados = pd.DataFrame(resultado.get("registros", []))

    if dados.empty:
        st.info("Nenhum registro disponível para visualização.")
        return

    dados["horario"] = pd.to_datetime(
        dados["horario"],
        errors="coerce",
    )

    dados = (
        dados.dropna(subset=["horario"])
        .sort_values("horario")
    )

    if dados.empty:
        st.info("Nenhum horário válido para visualização.")
        return

    metricas = {
        "total_validacoes": "Total de validações",
        "total_veiculos": "Veículos distintos observados",
        "validacoes_por_veiculo": "Validações por veículo observado",
    }

    with st.expander(
        f"📊 Gráficos — {resultado['linha']}",
        expanded=True,
    ):
        for coluna, titulo in metricas.items():
            desenhar_grafico(
                dados,
                coluna=coluna,
                titulo=titulo,
            )

        st.caption(
            f"Fonte: {resultado.get('base', 'BU')}. "
            "Os valores refletem os registros disponíveis. "
            "A ausência de registros não comprova ausência de serviço."
        )


def renderizar_ranking(resultado: dict) -> None:
    """Renderiza as linhas mais utilizadas por validações."""
    dados = pd.DataFrame(resultado.get("ranking", []))

    if dados.empty:
        st.info("Nenhuma linha encontrada para esse período.")
        return

    dados["total_validacoes"] = pd.to_numeric(
        dados["total_validacoes"],
        errors="coerce",
    )

    dados = (
        dados.dropna(subset=["linha", "total_validacoes"])
        .sort_values("total_validacoes", ascending=False)
        .reset_index(drop=True)
    )

    if dados.empty:
        st.info("Não há dados válidos para o ranking.")
        return

    altura = max(260, min(700, len(dados) * 45 + 80))

    with st.expander(
        f"🏆 Ranking de linhas — {resultado['base']}",
        expanded=True,
    ):
        desenhar_grafico(
            dados,
            coluna="total_validacoes",
            titulo="Linhas com mais validações registradas",
            tipo="barra",
            eixo_x="linha",
            horizontal=True,
            ordenar="-total_validacoes",
            altura=altura,
        )

        # Tabela para consultar as quantidades exatas.
        tabela = dados.copy()
        tabela.insert(
            0,
            "Posição",
            range(1, len(tabela) + 1),
        )

        tabela = tabela.rename(columns={
            "linha": "Linha",
            "total_validacoes": "Validações",
        })

        st.dataframe(
            tabela,
            hide_index=True,
            use_container_width=True,
        )

        st.caption(
            f"Fonte: {resultado['base']}. "
            "Ranking calculado por quantidade de validações "
            "registradas nos arquivos disponíveis no período. "
            "Não representa passageiros distintos."
        )


def renderizar_resultado(resultado: dict) -> None:
    """Escolhe a visualização conforme o tipo de resultado."""
    tipo = resultado.get("tipo")

    if tipo == "validacoes_por_veiculo":
        renderizar_validacoes(resultado)

    elif tipo == "ranking_linhas":
        renderizar_ranking(resultado)
