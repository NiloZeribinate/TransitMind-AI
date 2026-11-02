import duckdb
from datetime import datetime
import glob
from pathlib import Path

from src.data.types import TipoBase
from src.data.config import NOMES_BASES


def linhas_mais_utilizadas(
    tipo: TipoBase,
    data_inicio: datetime,
    data_fim: datetime,
    limite: int = 5,
    destino: str | Path = "data/processed",
) -> list[tuple[str, int]]:
    """
    Consulta as linhas com mais validações em um intervalo temporal.

    Executa a consulta diretamente nos arquivos Parquet da base
    escolhida, utilizando a data e hora reais das transações.

    O intervalo inclui data_inicio e exclui data_fim.

    Args:
        tipo: Base de origem (BU, BE ou GRATUIDADE).
        data_inicio: Instante inicial da consulta, inclusivo.
        data_fim: Instante final da consulta, exclusivo.
        limite: Quantidade máxima de linhas retornadas.
        destino: Diretório principal dos dados processados.

    Returns:
        list[tuple[str, int]]: Linhas e quantidades de validações
        ordenadas de forma decrescente.

    Raises:
        ValueError: Se o tipo, o intervalo ou o limite forem inválidos.
        FileNotFoundError: Se não houver arquivos Parquet disponíveis.
    """
    if tipo not in NOMES_BASES:
        raise ValueError(f"Base desconhecida: {tipo}")

    if data_inicio >= data_fim:
        raise ValueError("O início deve ser anterior ao fim.")

    if limite <= 0:
        raise ValueError("O limite deve ser positivo.")

    arquivos = arquivos_do_periodo(
        tipo,
        data_inicio,
        data_fim,
        destino,
    )

    con = duckdb.connect()

    try:
        resultado = con.execute(
            """
            SELECT
                linha,
                COUNT(*) AS total_validacoes
            FROM read_parquet(?, hive_partitioning = true)
            WHERE data_transacao >= ?
            AND data_transacao < ?
            GROUP BY linha
            ORDER BY total_validacoes DESC
            LIMIT ?
            """,
            [arquivos, data_inicio, data_fim, limite],
        ).fetchall()

    finally:
        con.close()

    return resultado


def arquivos_do_periodo(
    tipo: TipoBase,
    data_inicio: datetime,
    data_fim: datetime,
    destino: str | Path = "data/processed",
) -> list[str]:
    """
    Localiza os Parquets dos meses abrangidos pelo intervalo.

    O intervalo inclui data_inicio e exclui data_fim.
    Retorna somente arquivos das partições mensais necessárias.

    Args:
        tipo: Base consultada.
        data_inicio: Início inclusivo do intervalo.
        data_fim: Fim exclusivo do intervalo.
        destino: Diretório principal dos dados processados.

    Returns:
        list[str]: Caminhos dos arquivos Parquet encontrados.

    Raises:
        ValueError: Se o intervalo for inválido.
        FileNotFoundError: Se nenhum Parquet for encontrado.
    """
    if data_inicio >= data_fim:
        raise ValueError("Intervalo de datas inválido.")

    raiz = Path(destino) / NOMES_BASES[tipo]
    atual = datetime(data_inicio.year, data_inicio.month, 1)

    arquivos = []

    while atual < data_fim:
        pasta = (
            raiz
            / f"ano={atual.year}"
            / f"mes={atual.month:02d}"
        )

        arquivos.extend(
            str(arquivo)
            for arquivo in sorted(pasta.glob("*.parquet"))
        )

        # Avança para o primeiro dia do próximo mês.
        if atual.month == 12:
            atual = datetime(atual.year + 1, 1, 1)
        else:
            atual = datetime(atual.year, atual.month + 1, 1)

    if not arquivos:
        raise FileNotFoundError(
            "Nenhum Parquet encontrado no período."
        )

    return arquivos