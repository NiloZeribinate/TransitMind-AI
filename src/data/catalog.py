
from pathlib import Path
import unicodedata

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from src.data.config import NOMES_BASES


def normalizar_busca(texto: str) -> str:
    """
    Normaliza um texto para pesquisas por nome.

    Remove acentos, ignora diferenças entre maiúsculas e
    minúsculas e padroniza espaços em branco.

    Args:
        texto: Texto original.

    Returns:
        str: Texto normalizado para pesquisa.
    """
    texto = unicodedata.normalize("NFKD", texto)

    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )

    return " ".join(texto.casefold().split())


def arquivos_concluidos(destino: str | Path) -> list[str]:
    """
    Obtém os Parquets associados aos lotes concluídos.

    Consulta os marcadores .done das três bases, verificando
    a existência dos arquivos registrados em cada marcador.

    Args:
        destino: Diretório principal dos dados processados.

    Returns:
        list[str]: Caminhos absolutos dos Parquets concluídos,
            sem duplicações.

    Raises:
        ValueError: Se algum marcador contiver caminhos inválidos.
        FileNotFoundError: Se algum arquivo estiver ausente ou
            nenhum lote concluído for encontrado.
    """
    raiz = Path(destino).resolve()
    arquivos = set()

    for tipo, nome_base in NOMES_BASES.items():
        pasta_marcadores = raiz / "_completed" / tipo
        pasta_base = (raiz / nome_base).resolve()

        for marcador in sorted(pasta_marcadores.glob("*.done")):
            caminhos = [
                linha.strip()
                for linha in marcador.read_text(
                    encoding="utf-8"
                ).splitlines()
                if linha.strip()
            ]

            if not caminhos:
                raise ValueError(
                    f"Marcador vazio: {marcador}"
                )

            for relativo in caminhos:
                arquivo = (raiz / relativo).resolve()

                if (
                    not arquivo.is_relative_to(pasta_base)
                    or arquivo.name != f"{marcador.stem}.parquet"
                ):
                    raise ValueError(
                        f"Caminho inválido em {marcador}: {relativo}"
                    )

                if not arquivo.is_file():
                    raise FileNotFoundError(
                        f"Parquet ausente: {arquivo}"
                    )

                arquivos.add(str(arquivo))

    if not arquivos:
        raise FileNotFoundError(
            "Nenhum lote concluído foi encontrado."
        )

    return sorted(arquivos)


def gerar_catalogo(
    destino: str | Path = "data/processed",
) -> Path:
    """
    Gera o catálogo de linhas, operadoras e sindicatos únicos.

    Consulta os Parquets de lotes concluídos utilizando
    DuckDB. Preserva os nomes originais e produz chaves
    normalizadas para futuras pesquisas.

    O catálogo é compartilhado pelas três bases, sem
    distinguir a origem dos nomes.

    Args:
        destino: Diretório principal dos dados processados.

    Returns:
        Path: Caminho do catálogo Parquet gerado.

    Raises:
        FileNotFoundError: Se não houver lotes concluídos.
        ValueError: Se houver marcadores inválidos.
    """
    arquivos = arquivos_concluidos(destino)

    con = duckdb.connect()

    try:
        registros = con.execute(
            """
            WITH entidades AS (
                UNPIVOT (
                    SELECT linha, operadora, sindicato
                    FROM read_parquet(
                        ?,
                        union_by_name = true
                    )
                )
                ON linha, operadora, sindicato
                INTO
                    NAME campo
                    VALUE valor_original
            )
            SELECT DISTINCT
                campo,
                valor_original
            FROM entidades
            WHERE valor_original IS NOT NULL
              AND TRIM(valor_original) <> ''
            ORDER BY campo, valor_original
            """,
            [arquivos],
        ).fetchall()
    finally:
        con.close()

    dados = [
        {
            "campo": campo,
            "valor_original": valor_original,
            "chave_busca": normalizar_busca(valor_original),
        }
        for campo, valor_original in registros
    ]

    schema = pa.schema([
        ("campo", pa.string()),
        ("valor_original", pa.string()),
        ("chave_busca", pa.string()),
    ])

    tabela = pa.Table.from_pylist(dados, schema=schema)

    caminho = Path(destino) / "_catalogo" / "entidades.parquet"
    caminho.parent.mkdir(parents=True, exist_ok=True)

    temporario = caminho.with_suffix(".parquet.part")

    try:
        pq.write_table(
            tabela,
            temporario,
            compression="snappy",
        )

        metadata = pq.read_metadata(temporario)

        if metadata.num_rows != tabela.num_rows:
            raise ValueError(
                "Quantidade de registros divergente no catálogo."
            )

        if not pq.read_schema(temporario).equals(
            tabela.schema, check_metadata=False
        ):
            raise ValueError(
                "Esquema divergente no catálogo."
            )

        temporario.replace(caminho)

    finally:
        temporario.unlink(missing_ok=True)

    return caminho
