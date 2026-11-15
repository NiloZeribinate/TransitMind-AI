
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from src.data.ingestion import baixar_periodo
from src.data.preprocessing import preprocessar
from src.data.storage import (
    salvar_particionado,
    lote_concluido,
    registrar_lote,
)
from src.data.catalog import gerar_catalogo


RAIZ = Path(__file__).resolve().parents[1]
RAW = RAIZ / "data" / "raw"
PROCESSED = RAIZ / "data" / "processed"


def main():
    baixar_periodo(
        data_inicio="2026-03-01",
        data_fim="2026-03-05",
        destino=RAW,
        tipos=("BU",),
    )

    # Localiza os CSVs extraídos sem fixar o nome da pasta.
    csvs = {
        caminho.stem.upper(): caminho
        for caminho in (RAW / "BU" / "extracted").rglob("*.csv")
    }

    novos_lotes = 0

    for dia in range(1, 6):
        lote = f"TRANSACAO_BU_PUBLICO_2026_03_{dia:02d}"

        if lote_concluido("BU", lote, PROCESSED):
            print(f"{lote}: já processado.")
            continue

        caminho_csv = csvs.get(lote)

        if caminho_csv is None:
            raise FileNotFoundError(
                f"CSV não encontrado para {lote}"
            )

        print(f"Processando {lote}...")

        df = pd.read_csv(
            caminho_csv,
            sep=";",
            dtype=str,
        )

        df_processado = preprocessar(df, "BU")

        arquivos = salvar_particionado(
            df_processado,
            "BU",
            destino=PROCESSED,
            identificador_lote=lote,
        )

        total = sum(
            pq.read_metadata(arquivo).num_rows
            for arquivo in arquivos
        )

        if total != len(df_processado):
            raise ValueError(
                f"Contagem divergente no lote {lote}"
            )

        registrar_lote("BU", lote, PROCESSED, arquivos)
        novos_lotes += 1

        del df, df_processado

    catalogo = PROCESSED / "_catalogo" / "entidades.parquet"

    if novos_lotes or not catalogo.exists():
        gerar_catalogo(PROCESSED)

    print("Dados de demonstração preparados!")


if __name__ == "__main__":
    main()
