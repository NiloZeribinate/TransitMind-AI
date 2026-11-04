from datetime import datetime
from typing import get_args
from time import perf_counter

from src.data.types import FiltroSentido
from src.analytics.queries import validacoes_por_veiculo_hora
from src.analytics.linhas import (
    buscar_linhas,
    LinhaNaoEncontradaError,
)


def pesquisar_linhas(termo: str) -> dict:
    """
    Pesquisa linhas de transporte disponíveis no TransitMind AI.

    A pesquisa aceita nomes parciais, sem diferenciar letras
    maiúsculas, minúsculas ou acentos.

    Args:
        termo: Nome ou trecho do nome da linha desejada.

    Returns:
        dict: Status da pesquisa e lista de nomes oficiais
            encontrados no catálogo.
    """
    print(f"[TOOL] pesquisar_linhas(termo={termo!r})")

    try:
        linhas = buscar_linhas(termo=termo)

        return {
            "status": "encontradas",
            "linhas": linhas,
        }

    except LinhaNaoEncontradaError:
        return {
            "status": "nao_encontrada",
            "linhas": [],
        }


def analisar_validacoes_por_veiculo(
    linha: str,
    inicio: str,
    fim: str,
    sentido: str = "todos",
) -> dict:
    """
    Analisa as validações por veículo de uma linha de transporte.

    Exige o nome oficial exato da linha, obtido previamente
    pela ferramenta de pesquisa. Utiliza a base BU.

    Args:
        linha: Nome oficial completo da linha.
        inicio: Data e hora inicial em formato ISO 8601.
        fim: Data e hora final em formato ISO 8601.
        sentido: "todos", "0", "1" ou "2".

    Returns:
        dict: Resultado horário da análise ou erro estruturado.
    """
    print(
        f"[TOOL] analisar_validacoes_por_veiculo("
        f"linha={linha!r}, inicio={inicio!r}, "
        f"fim={fim!r}, sentido={sentido!r})"
    )

    try:
        inicio_dt = datetime.fromisoformat(inicio)
        fim_dt = datetime.fromisoformat(fim)

        opcoes = {
            str(valor): valor
            for valor in get_args(FiltroSentido)
        }

        if sentido not in opcoes:
            raise ValueError(f"Sentido inválido: {sentido}")

        sentido_convertido = opcoes[sentido]

        inicio = perf_counter()

        resultado = validacoes_por_veiculo_hora(
            inicio_dt, fim_dt, linha, sentido_convertido, "BU"
        )

        print(
            f"[PERF] DuckDB + análise: "
            f"{perf_counter() - inicio:.2f}s"
        )
        print(f"[TOOL RESULT] {len(resultado)} horários retornados")

        resultado["horario"] = (
            resultado["horario"]
            .dt.strftime("%Y-%m-%dT%H:%M:%S")
        )

        registros = resultado.to_dict(orient="records")

        return {
            "status": "sucesso",
            "linha": linha,
            "base": "BU",
            "registros": registros
        }
    except (ValueError, FileNotFoundError) as erro:
        return {
            "status": "erro",
            "mensagem": str(erro)
        }
