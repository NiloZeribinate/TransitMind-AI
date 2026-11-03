import pandas as pd
import pyarrow.parquet as pq
from typing import get_args
from pathlib import Path

from src.data.storage import (
    salvar_particionado,
    lote_concluido,
    registrar_lote,
)
from src.data.types import TipoBase
from src.data.preprocessing import preprocessar
from src.data.catalog import gerar_catalogo, normalizar_busca

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

novos_lotes = 0
for tipo in get_args(TipoBase):
    lote = identificador[tipo]

    if lote_concluido(tipo, lote, destino):
        print(f"{lote} já foi processado. Ignorando...")
        novos_lotes += 1
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

caminho_catalogo = (
    Path(destino) / "_catalogo" / "entidades.parquet"
)

if novos_lotes > 0 or not caminho_catalogo.is_file():
    caminho = gerar_catalogo(destino)
    print(f"Catálogo atualizado: {caminho}")
else:
    print("Catálogo já atualizado.")

caminho = gerar_catalogo("data/processed")
catalogo = pd.read_parquet(caminho)

print(catalogo.groupby("campo").size())
print(catalogo.head(10))

assert set(catalogo["campo"]) == {
    "linha", "operadora", "sindicato"
}

assert not catalogo.duplicated(
    subset=["campo", "valor_original"]
).any()

assert all(
    catalogo["chave_busca"]
    == catalogo["valor_original"].map(normalizar_busca)
)