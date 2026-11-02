import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from typing import get_args

from src.data.preprocessing import preprocessar
from src.data.storage import salvar_particionado

from src.data.types import TipoBase

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
    print(tipo)

    df = pd.read_csv(df_caminho[tipo], sep=";", dtype=str)
    df_processado = preprocessar(df, tipo)

    arquivos = salvar_particionado(
        df_processado,
        tipo,
        destino="data/processed",
        identificador_lote=identificador[tipo],
    )

    total = sum(pq.read_metadata(arquivo).num_rows for arquivo in arquivos)

    print("Arquivos produzidos:", len(arquivos))
    print("Registros preservados:", total)

    assert total == len(df_processado)
