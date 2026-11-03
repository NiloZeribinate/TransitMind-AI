
from pathlib import Path

import duckdb

from src.data.catalog import normalizar_busca


class LinhaNaoEncontradaError(ValueError):
    """Indica que uma linha não existe no catálogo."""


def _caminho_catalogo(destino: str | Path) -> Path:
    caminho = (
        Path(destino)
        / "_catalogo"
        / "entidades.parquet"
    )

    if not caminho.is_file():
        raise FileNotFoundError(
            f"Catálogo não encontrado: {caminho}"
        )

    return caminho


def buscar_linhas(
    termo: str,
    limite: int = 10,
    destino: str | Path = "data/processed",
) -> list[str]:
    """
    Busca linhas por nome completo ou correspondência parcial.

    A pesquisa ignora acentos e diferenças de caixa.
    Correspondências exatas são priorizadas.

    Args:
        termo: Nome ou trecho do nome da linha.
        limite: Máximo de opções retornadas, no mínimo 2.
        destino: Diretório principal dos dados processados.

    Returns:
        list[str]: Nomes oficiais das linhas encontradas.

    Raises:
        ValueError: Se os parâmetros forem inválidos.
        LinhaNaoEncontradaError: Se não houver correspondências.
        FileNotFoundError: Se o catálogo não existir.
    """
    if not isinstance(termo, str) or not termo.strip():
        raise ValueError("Informe um termo de busca válido.")

    if type(limite) is not int or limite < 2:
        raise ValueError("O limite deve ser um inteiro >= 2.")

    caminho = _caminho_catalogo(destino)
    chave = normalizar_busca(termo)

    con = duckdb.connect()

    try:
        registros = con.execute(
            """
            SELECT valor_original, chave_busca
            FROM read_parquet(?)
            WHERE campo = 'linha'
              AND strpos(chave_busca, ?) > 0
            ORDER BY
                CASE
                    WHEN valor_original = ? THEN 0
                    WHEN chave_busca = ? THEN 1
                    ELSE 2
                END,
                LENGTH(chave_busca),
                valor_original
            LIMIT ?
            """,
            [str(caminho), chave, termo, chave, limite],
        ).fetchall()

    finally:
        con.close()

    if not registros:
        raise LinhaNaoEncontradaError(
            f"Nenhuma linha encontrada para '{termo}'."
        )

    # O nome oficial exato tem prioridade.
    for nome, _ in registros:
        if nome == termo:
            return [nome]

    # Uma única correspondência normalizada exata
    # também tem prioridade sobre resultados parciais.
    exatas_normalizadas = [
        nome
        for nome, chave_catalogo in registros
        if chave_catalogo == chave
    ]

    if len(exatas_normalizadas) == 1:
        return exatas_normalizadas

    return [nome for nome, _ in registros]


def validar_linha_exata(
    linha: str,
    destino: str | Path = "data/processed",
) -> None:
    """
    Verifica se um nome oficial de linha existe no catálogo.

    Não realiza pesquisa aproximada nem altera o nome.

    Args:
        linha: Nome oficial exato da linha.
        destino: Diretório dos dados processados.

    Raises:
        ValueError: Se o nome for inválido.
        LinhaNaoEncontradaError: Se a linha não existir.
        FileNotFoundError: Se o catálogo não existir.
    """
    if not isinstance(linha, str) or not linha.strip():
        raise ValueError("Informe o nome oficial da linha.")

    caminho = _caminho_catalogo(destino)

    con = duckdb.connect()

    try:
        existe = con.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM read_parquet(?)
                WHERE campo = 'linha'
                  AND valor_original = ?
            )
            """,
            [str(caminho), linha],
        ).fetchone()[0]

    finally:
        con.close()

    if not existe:
        raise LinhaNaoEncontradaError(
            f"A linha '{linha}' não existe no catálogo. "
            "Utilize buscar_linhas() para pesquisar."
        )
