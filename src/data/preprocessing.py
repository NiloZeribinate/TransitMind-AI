import pandas as pd

from .types import TipoBase
from .schemas import ESQUEMAS, REGRAS

def padronizar_colunas(df: pd.DataFrame, tipo: TipoBase) -> pd.DataFrame:
    """
    Padroniza os nomes e a seleção de colunas de uma base.

    Utiliza o esquema definido para BU, BE ou GRATUIDADE,
    descarta colunas não selecionadas e cria colunas opcionais
    ausentes, preenchendo-as com valores nulos.

    Args:
        df: DataFrame contendo as colunas originais da base.
        tipo: Identificador da base a ser processada.

    Returns:
        Cópia do DataFrame com as colunas selecionadas e renomeadas.

    Raises:
        ValueError: Se o tipo for desconhecido ou alguma coluna
            obrigatória estiver ausente.
    """
    if tipo not in ESQUEMAS:
        raise ValueError(f"Base desconhecida: {tipo}")

    esquema = ESQUEMAS[tipo]

    colunas = esquema["colunas"]
    opcionais = esquema.get("colunas_opcionais", set())

    obrigatorias = set(colunas) - opcionais
    faltantes = obrigatorias - set(df.columns)

    if faltantes:
        raise ValueError(
            f"Colunas obrigatórias ausentes em {tipo}: {sorted(faltantes)}"
        )

    return (
        df.reindex(columns=list(colunas))
        .rename(columns=colunas)
        .copy()
    )

def converter_datas(df: pd.DataFrame, tipo: TipoBase) -> pd.DataFrame:
    """
    Converte as colunas de data de uma base para o tipo datetime.

    Utiliza os formatos definidos em REGRAS para cada base.
    Interrompe o processamento caso encontre uma data inválida
    ou incompatível com o formato esperado.

    Args:
        df (pd.DataFrame): DataFrame com as colunas padronizadas.
        tipo (str): Identificador da base (BU, BE ou GRATUIDADE).

    Returns:
        pd.DataFrame: Cópia do DataFrame com as datas convertidas.

    Raises:
        KeyError: Se a base não existir em REGRAS ou faltar uma coluna.
        ValueError: Se alguma data não corresponder ao formato esperado.
    """

    df = df.copy()

    formatos = REGRAS[tipo]["datas"]

    for coluna, formato in formatos.items():
        df[coluna] = pd.to_datetime(
            df[coluna],
            format=formato,
            errors="raise",
        )

    return df