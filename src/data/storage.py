from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .schemas import ESQUEMAS
from .types import TipoBase

NOMES_BASES = {
    "BU": "bilhete_unico",
    "BE": "bilhetagem_eletronica",
    "GRATUIDADE": "gratuidade",
}

TIPOS_ARROW = {
    # Textos e identificadores
    "cartao_hash": pa.string(),
    "descricao_aplicacao": pa.string(),
    "sindicato": pa.string(),
    "operadora": pa.string(),
    "linha": pa.string(),
    "numero_carro": pa.string(),
    "numero_validador": pa.string(),
    "numero_ordem": pa.string(),
    "escola": pa.string(),
    "numero_censo_escola": pa.string(),

    # Datas
    "data_transacao": pa.timestamp("ns"),
    "data_processamento": pa.timestamp("ns"),
    "data_ordem": pa.date32(),

    # Valores monetários
    "valor_linha": pa.decimal128(12, 2),
    "valor_transacao": pa.decimal128(12, 2),
    "valor_subsidio": pa.decimal128(12, 2),

    # Inteiros
    "sentido": pa.int64(),
    "sentido_original": pa.int64(),
    "indice_integracao": pa.int64(),
}

def obter_schema_arrow(tipo: TipoBase) -> pa.Schema:
    """
    Constrói o esquema PyArrow de uma base processada.

    Utiliza as colunas definidas em ESQUEMAS e os tipos
    de armazenamento estabelecidos em TIPOS_ARROW.

    Args:
        tipo: Identificador da base (BU, BE ou GRATUIDADE).

    Returns:
        pa.Schema: Esquema utilizado na exportação para Parquet.

    Raises:
        ValueError: Se a base informada for desconhecida.
        KeyError: Se uma coluna não tiver tipo Arrow definido.
    """
    if tipo not in ESQUEMAS:
        raise ValueError(f"Base desconhecida: {tipo}")

    colunas = list(ESQUEMAS[tipo]["colunas"].values())

    if tipo in ("BU", "BE"):
        colunas.append("sentido_original")

    campos = [
        pa.field(coluna, TIPOS_ARROW[coluna])
        for coluna in colunas
    ]

    return pa.schema(campos)


def salvar_parquet(tabela: pa.Table, destino: str | Path) -> Path:
    """
    Salva uma tabela PyArrow em formato Parquet.

    Grava inicialmente em um arquivo temporário, verifica
    o esquema e a quantidade de registros e somente então
    substitui o arquivo de destino.

    Args:
        tabela: Tabela PyArrow com esquema definido.
        destino: Caminho do arquivo Parquet de saída.

    Returns:
        Path: Caminho do arquivo salvo.

    Raises:
        OSError: Se houver falha na escrita ou armazenamento.
        ValueError: Se o arquivo gravado não passar na validação.
    """
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)

    temporario = destino.with_suffix(".parquet.part")

    try:
        pq.write_table(
            tabela,
            temporario,
            compression="snappy",
            row_group_size=250_000,
        )

        metadata = pq.read_metadata(temporario)
        schema = pq.read_schema(temporario)

        if metadata.num_rows != tabela.num_rows:
            raise ValueError("Quantidade de registros divergente.")

        if not schema.equals(tabela.schema, check_metadata=False):
            raise ValueError("Esquema do Parquet divergente.")

        temporario.replace(destino)

    finally:
        temporario.unlink(missing_ok=True)

    return destino

def salvar_particionado(df: pd.DataFrame, tipo: TipoBase, destino: str | Path, identificador_lote: str,) -> list[Path]:
    """
    Armazena um lote de transações em arquivos Parquet particionados.

    Agrupa os registros pelo ano e mês da data de transação,
    convertendo cada grupo para uma tabela PyArrow com esquema
    explícito e salvando-o no diretório correspondente.

    Um mesmo lote pode produzir arquivos em diferentes meses,
    pois a data de transação pode ser anterior à publicação.

    Args:
        df: DataFrame previamente processado e validado.
        tipo: Base de origem (BU, BE ou GRATUIDADE).
        destino: Diretório principal dos dados processados.
        identificador_lote: Nome único do lote de origem,
            sem extensão, usado nos arquivos produzidos.

    Returns:
        list[Path]: Caminhos dos arquivos Parquet produzidos.

    Raises:
        KeyError: Se faltarem colunas necessárias.
        ValueError: Se o tipo ou identificador for inválido,
            ou se a gravação falhar na validação.
        OSError: Se ocorrer erro de escrita ou armazenamento.
    """

    if tipo not in NOMES_BASES:
        raise ValueError(f"Base desconhecida: {tipo}")

    if not identificador_lote or Path(identificador_lote).name != identificador_lote:
        raise ValueError("Identificador de lote inválido.")

    df = df.copy()

    if "data_ordem" in df.columns:
        df["data_ordem"] = df["data_ordem"].dt.date

    if df["data_transacao"].isna().any():
        raise ValueError("Existem transações sem data válida.")

    arquivos = [];

    for (ano, mes), grupo in df.groupby([
        df["data_transacao"].dt.year,
        df["data_transacao"].dt.month,
    ]):
        tabela = pa.Table.from_pandas(
            grupo,
            schema=obter_schema_arrow(tipo),
            preserve_index=False,
            safe=True
        )

        caminho = (
            Path(destino)
            / NOMES_BASES[tipo]
            / f"ano={ano}"
            / f"mes={mes:02d}"
            / f"{identificador_lote}.parquet"
        )

        arquivo = salvar_parquet(tabela, caminho)

        print(f"{len(grupo)} registros salvos em {arquivo}");
        
        arquivos.append(arquivo)

    return arquivos


