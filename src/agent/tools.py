from datetime import datetime, timedelta
from typing import get_args
from time import perf_counter

from src.data.types import FiltroSentido
from src.analytics.queries import validacoes_por_veiculo_hora, linhas_mais_utilizadas
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



def ranking_linhas_por_validacoes(
    inicio: str,
    fim: str,
    limite: int = 10,
    tipo: str = "BU",
) -> dict:
    """
    Retorna as linhas com mais validações registradas.

    Args:
        inicio: Início do período em formato ISO 8601.
        fim: Fim do período em formato ISO 8601.
            Uma data sem horário inclui o dia inteiro.
        limite: Quantidade máxima de linhas, de 1 a 20.
        tipo: Base de dados: BU, BE ou GRATUIDADE.

    Returns:
        dict: Ranking ordenado ou mensagem de erro.
    """
    try:
        if tipo not in {"BU", "BE", "GRATUIDADE"}:
            raise ValueError("Base de dados inválida.")

        if not 1 <= limite <= 20:
            raise ValueError("O limite deve estar entre 1 e 20.")

        data_inicio = datetime.fromisoformat(inicio)
        data_fim = datetime.fromisoformat(fim)

        # Data sem horário significa o dia inteiro.
        if len(fim) == 10:
            data_fim += timedelta(days=1)

        if data_inicio >= data_fim:
            raise ValueError(
                "A data inicial deve ser anterior à final."
            )

        linhas = linhas_mais_utilizadas(
            tipo, data_inicio, data_fim, limite
        )

        return {
            "status": "sucesso",
            "base": tipo,
            "inicio": data_inicio.isoformat(),
            "fim_exclusivo": data_fim.isoformat(),
            "ranking": [
                {
                    "linha": linha,
                    "total_validacoes": int(quantidade),
                }
                for linha, quantidade in linhas
            ],
        }

    except (ValueError, FileNotFoundError) as erro:
        return {
            "status": "erro",
            "mensagem": str(erro),
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
