import pandas as pd
import pyarrow.parquet as pq
from typing import get_args

from src.data.storage import (
    salvar_particionado,
    lote_concluido,
    registrar_lote,
)
from src.data.types import TipoBase
from src.data.preprocessing import preprocessar

destino = "data/processed"

df_caminho = {
    "BU": "./data/raw/BU/extracted/transacao_bu_publico_2026_03_01.csv/TRANSACAO_BU_PUBLICO_2026_03_01.csv",
    "BE": "./data/raw/BE/extracted/transacao_be_publico_2026_03_01.csv/TRANSACAO_BE_PUBLICO_2026_03_01.csv",
    "GRATUIDADE": "./data/raw/GRATUIDADE/extracted/transacao_gratuidade_publico_2026_03_01.csv/TRANSACAO_GRATUIDADE_PUBLICO_2026_03_01.csv"
}

identificador = {
    "BU": "TRANSACAO_BU_PUBLICO_2026_03_01",
    "BE": "TRANSACAO_BE_PUBLICO_2026_03_01",
    "GRATUIDADE": "TRANSACAO_GRATUIDADE_PUBLICO_2026_03_01"
}

for tipo in get_args(TipoBase):
    lote = identificador[tipo]

    if lote_concluido(tipo, lote, destino):
        print(f"{lote} já foi processado. Ignorando...")
        continue

    df = pd.read_csv(
        df_caminho[tipo],
        sep=";",
        dtype=str,
    )

    df_processado = preprocessar(df, tipo)

    arquivos = salvar_particionado(
        df_processado,
        tipo,
        destino=destino,
        identificador_lote=lote,
    )

    total = sum(
        pq.read_metadata(arquivo).num_rows
        for arquivo in arquivos
    )

    if total != len(df_processado):
        raise ValueError(
            f"Lote {lote}: quantidade de registros divergente."
        )

    registrar_lote(
        tipo,
        lote,
        destino,
        arquivos,
    )

    print(f"{lote} concluído com sucesso!")