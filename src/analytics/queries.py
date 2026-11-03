import duckdb
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Literal, get_args

from src.data.types import TipoBase
from src.data.config import (
    NOMES_BASES,
    SINDICATOS_SEM_SENTIDO,
    OPERADORAS_SEM_SENTIDO,
    SINDICATOS_EXCLUIDOS_VEICULOS,
    OPERADORAS_EXCLUIDAS_VEICULOS,
)
from src.data.catalog import normalizar_busca
from src.analytics.linhas import validar_linha_exata

FiltroSentido = Literal["todos", 0, 1, 2]


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

    arquivos = arquivos_do_periodo(tipo, data_inicio, data_fim, destino)

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


def validacoes_por_veiculo_hora(
    data_inicio: datetime,
    data_fim: datetime,
    linha: str,
    sentido: FiltroSentido = "todos",
    tipo: TipoBase = "BU",
    destino: str | Path = "data/processed",
) -> pd.DataFrame:
    """
    Calcula validações por veículo observado, agrupadas por hora.

    Exige o nome oficial da linha, validado no catálogo.
    Considera somente modais em que numero_carro identifica
    um veículo, utilizando operadora e numero_carro como chave.

    O intervalo inclui data_inicio e exclui data_fim.
    Horas sem validações são preenchidas com zero, desde que
    a linha possua registros nos meses carregados.

    O indicador não representa ocupação ou passageiros únicos.

    Args:
        data_inicio: Início inclusivo do intervalo.
        data_fim: Fim exclusivo do intervalo.
        linha: Nome oficial exato da linha.
        sentido: "todos", 0 (não informado), 1 ou 2.
        tipo: Base consultada, BU ou BE.
        destino: Diretório principal dos dados processados.

    Returns:
        pd.DataFrame: Resultados ordenados por horário, contendo
            horario, total_validacoes, total_veiculos e
            validacoes_por_veiculo.

    Raises:
        ValueError: Se os parâmetros forem inválidos, não houver
            dados da linha nos meses carregados ou o modal/sentido
            não permitir a análise.
        LinhaNaoEncontradaError: Se a linha não existir no catálogo.
        FileNotFoundError: Se faltarem catálogo ou Parquets.
    """
    if tipo not in ("BU", "BE"):
        raise ValueError("A análise aceita apenas BU ou BE.")

    if not isinstance(data_inicio, datetime) or not isinstance(
        data_fim, datetime
    ):
        raise ValueError("O intervalo deve utilizar datetime.")

    if data_inicio.tzinfo is not None or data_fim.tzinfo is not None:
        raise ValueError("Utilize datetimes sem fuso horário.")

    if data_inicio >= data_fim:
        raise ValueError("O início deve ser anterior ao fim.")

    # Reutiliza os valores declarados em FiltroSentido.
    opcoes = get_args(FiltroSentido)

    if not any(
        type(sentido) is type(opcao) and sentido == opcao
        for opcao in opcoes
    ):
        raise ValueError(
            f"Sentido inválido. Valores permitidos: {opcoes}"
        )

    # Verifica somente o nome oficial.
    # Não realiza busca aproximada.
    validar_linha_exata(linha, destino)

    arquivos = arquivos_do_periodo(
        tipo, data_inicio, data_fim, destino
    )

    sindicatos_excluidos = sorted(
        SINDICATOS_EXCLUIDOS_VEICULOS
    )
    operadoras_excluidas = sorted(
        OPERADORAS_EXCLUIDAS_VEICULOS
    )

    con = duckdb.connect()

    try:
        # Verifica a presença da linha nos meses carregados.
        #
        # Não filtramos pelo horário aqui: uma linha pode ter
        # registros no mês, mas nenhuma validação entre 3h e 4h.
        origens = con.execute(
            """
            SELECT DISTINCT sindicato, operadora
            FROM read_parquet(?, hive_partitioning = true)
            WHERE linha = ?
            """,
            [arquivos, linha],
        ).fetchall()

        if not origens:
            raise ValueError(
                f"A linha '{linha}' existe no catálogo, mas "
                f"não possui registros nos meses consultados "
                f"da base {tipo}."
            )

        origens_elegiveis = [
            (sindicato, operadora)
            for sindicato, operadora in origens
            if sindicato not in SINDICATOS_EXCLUIDOS_VEICULOS
            and operadora not in OPERADORAS_EXCLUIDAS_VEICULOS
        ]

        if not origens_elegiveis:
            raise ValueError(
                f"A linha '{linha}' pertence a um modal "
                "não elegível para análise por veículo."
            )

        # Sentido 0 e "todos" são aceitos mesmo em modais
        # cujo sentido foi normalizado como não confiável.
        if sentido in (1, 2):
            sentido_nao_confiavel = any(
                sindicato in SINDICATOS_SEM_SENTIDO
                or operadora in OPERADORAS_SEM_SENTIDO
                for sindicato, operadora in origens_elegiveis
            )

            if sentido_nao_confiavel:
                raise ValueError(
                    f"A linha '{linha}' possui registros "
                    "com sentido não confiável. "
                    "Utilize sentido='todos' ou sentido=0."
                )

        # Os conjuntos de exclusão são definidos internamente.
        # Seus valores são parametrizados, assim como os filtros.
        marcas_s = ", ".join(
            "?" for _ in sindicatos_excluidos
        )
        marcas_o = ", ".join(
            "?" for _ in operadoras_excluidas
        )

        parametros = [
            arquivos,
            data_inicio,
            data_fim,
            linha,
            *sindicatos_excluidos,
            *operadoras_excluidas,
        ]

        filtro_sentido = ""

        if sentido != "todos":
            filtro_sentido = "AND sentido = ?"
            parametros.append(sentido)

        resultado = con.execute(
            f"""
            WITH por_hora AS (
                SELECT
                    DATE_TRUNC('hour', data_transacao)
                        AS horario,

                    COUNT(*) AS total_validacoes,

                    COUNT(
                        DISTINCT (operadora, numero_carro)
                    ) AS total_veiculos

                FROM read_parquet(
                    ?, hive_partitioning = true
                )

                WHERE data_transacao >= ?
                  AND data_transacao < ?
                  AND linha = ?

                  AND sindicato NOT IN ({marcas_s})
                  AND operadora NOT IN ({marcas_o})

                  AND numero_carro IS NOT NULL
                  AND TRIM(numero_carro) <> ''
                  AND operadora IS NOT NULL

                  {filtro_sentido}

                GROUP BY horario
            )

            SELECT
                horario,
                total_validacoes,
                total_veiculos,
                total_validacoes * 1.0
                    / NULLIF(total_veiculos, 0)
                    AS validacoes_por_veiculo
            FROM por_hora
            ORDER BY horario
            """,
            parametros,
        ).df()

    finally:
        con.close()

    # Impede interpretar problemas de identificação
    # de veículos como uma média igual a zero.
    inconsistente = (
        (resultado["total_validacoes"] > 0)
        & (resultado["total_veiculos"] == 0)
    )

    if inconsistente.any():
        raise ValueError(
            "Existem validações sem veículos identificáveis."
        )

    # Inclui todas as horas que intersectam o intervalo.
    horas = pd.date_range(
        start=pd.Timestamp(data_inicio).floor("h"),
        end=pd.Timestamp(data_fim).ceil("h"),
        freq="h",
        inclusive="left",
    )

    resultado = (
        resultado
        .set_index("horario")
        .reindex(horas)
        .rename_axis("horario")
    )

    resultado["total_validacoes"] = (
        resultado["total_validacoes"]
        .fillna(0)
        .astype("int64")
    )

    resultado["total_veiculos"] = (
        resultado["total_veiculos"]
        .fillna(0)
        .astype("int64")
    )

    resultado["validacoes_por_veiculo"] = (
        resultado["validacoes_por_veiculo"]
        .fillna(0.0)
    )

    return resultado.reset_index()


