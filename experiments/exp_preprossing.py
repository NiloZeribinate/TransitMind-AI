from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq
import duckdb
from src.data.preprocessing import preprocessar

# Pasta de experimentos
destino = Path("./data/processed")
destino.mkdir(parents=True, exist_ok=True)

arquivo = destino / "_teste_bu.parquet"

# Primeiro teste com uma amostra pequena

df = pd.read_csv("./data/raw/BU/extracted/transacao_bu_publico_2026_03_01.csv/TRANSACAO_BU_PUBLICO_2026_03_01.csv", sep=";", dtype=str)
df_processado = preprocessar(df, "BU")

amostra = df_processado.head(1000)

amostra.to_parquet(
    arquivo,
    engine="pyarrow",
    compression="snappy",
    index=False,
)

print(f"Tamanho: {arquivo.stat().st_size / 1024:.2f} KB")

print("\nEsquema do Parquet:")
print(pq.read_schema(arquivo))


con = duckdb.connect()

resultado = con.execute(
    """
    SELECT
        COUNT(*) AS total_transacoes,
        SUM(valor_subsidio) AS total_subsidio
    FROM read_parquet(?)
    """,
    [str(arquivo)],
).fetchone()

print("Transações:", resultado[0])
print("Subsídio total:", resultado[1])

con.close()

assert resultado[0] == len(amostra)

assert resultado[1] == amostra["valor_subsidio"].sum()
