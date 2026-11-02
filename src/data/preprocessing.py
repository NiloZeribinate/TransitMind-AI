import pandas as pd
from decimal import Decimal, InvalidOperation

from .types import TipoBase
from .schemas import ESQUEMAS, REGRAS, TIPOS_FINANCEIROS, SINDICATOS_SEM_SENTIDO, OPERADORAS_SEM_SENTIDO

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

def converter_valores_monetarios(df: pd.DataFrame, tipo: TipoBase) -> pd.DataFrame:
    """
    Converte as colunas monetárias para Decimal.

    Utiliza as regras da base para tratar valores ausentes
    e rejeita valores incompatíveis com a conversão.

    Args:
        df: DataFrame com colunas previamente padronizadas.
        tipo: Identificador da base.

    Returns:
        pd.DataFrame: Cópia com os valores monetários convertidos.

    Raises:
        ValueError: Se encontrar valores monetários inválidos.
    """

    df = df.copy()

    colunas_monetarias = [
        coluna
        for coluna in ESQUEMAS[tipo]['colunas'].values()
        if coluna in TIPOS_FINANCEIROS
    ]

    for coluna in colunas_monetarias:
        nulos_como_zero = REGRAS[tipo]['nulos_como_zero']

        df[coluna] = df[coluna].map(
            lambda valor: converter_decimal(
                valor, 
                nulos_como_zero=nulos_como_zero
            )
        )

    return df


def converter_decimal(valor: str | None, nulos_como_zero: bool = False) -> Decimal:
    """
    Converte um valor monetário para Decimal com duas casas decimais.

    Aceita vírgula como separador decimal. Valores ausentes
    são convertidos para zero somente quando permitido.

    Args:
        valor: Representação textual do valor monetário.
        nulos_como_zero: Permite interpretar valores ausentes como zero.

    Returns:
        Decimal: Valor monetário com duas casas decimais.

    Raises:
        ValueError: Se o valor for inválido, ausente sem permissão
            ou possuir precisão superior a duas casas decimais.
    """
    if pd.isna(valor) or (
        isinstance(valor, str) and not valor.strip()
    ):
        if nulos_como_zero:
            return Decimal("0.00")

        raise ValueError("Valor monetário ausente.")

    try:
        numero = Decimal(str(valor).strip().replace(",", "."))

        if not numero.is_finite():
            raise ValueError(f"Valor monetário inválido: {valor!r}")

        resultado = numero.quantize(Decimal("0.01"))

        if resultado != numero:
            raise ValueError(
                f"Valor possui mais de duas casas decimais: {valor!r}"
            )

        return resultado

    except InvalidOperation as erro:
        raise ValueError(
            f"Valor monetário inválido: {valor!r}"
        ) from erro

def normalizar_sentido(df: pd.DataFrame, tipo: TipoBase) -> pd.DataFrame:
    """
    Normaliza o sentido de modais sem informação confiável.

    Para registros identificados pelos sindicatos ou operadoras
    configurados, atribui sentido 0 (não informado), preservando
    o valor original em uma coluna separada.

    Args:
        df: DataFrame com colunas previamente padronizadas.
        tipo: Identificador da base (BU, BE ou GRATUIDADE).

    Returns:
        pd.DataFrame: Cópia com o sentido normalizado.

    Raises:
        ValueError: Se houver valores de sentido não numéricos.
    """
    df = df.copy()

    if tipo == "GRATUIDADE":
        return df

    df["sentido_original"] = pd.to_numeric(
        df["sentido"], errors="raise"
    ).astype("Int64")

    sindicatos = df["sindicato"].astype("string").str.strip().str.upper()
    operadoras = df["operadora"].astype("string").str.strip().str.upper()

    mascara = (
        sindicatos.isin(SINDICATOS_SEM_SENTIDO)
        | operadoras.isin(OPERADORAS_SEM_SENTIDO)
    )

    df["sentido"] = df["sentido_original"].mask(mascara, 0)

    return df

def preprocessar(df: pd.DataFrame, tipo: TipoBase) -> pd.DataFrame:
    """Executa as transformações de uma base na ordem definida."""

    df = padronizar_colunas(df, tipo)
    df = converter_datas(df, tipo)
    df = converter_valores_monetarios(df, tipo)
    df = normalizar_sentido(df, tipo)

    if tipo == "BU":
        df["indice_integracao"] = pd.to_numeric(
            df["indice_integracao"],
            errors="raise"
        ).astype("Int64")

    return df
