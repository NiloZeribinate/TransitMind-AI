import duckdb

con = duckdb.connect()

caminho = "data/processed/bilhete_unico/ano=*/mes=*/*.parquet"

resultado = con.execute(
    """
    SELECT
        ano,
        mes,
        COUNT(*) AS total_validacoes,
        SUM(valor_subsidio) AS total_subsidio
    FROM read_parquet(?, hive_partitioning = true)
    GROUP BY ano, mes
    ORDER BY ano, mes
    """,
    [caminho],
).fetchall()

for linha in resultado:
    print(linha)

resultado = con.execute(
    """
    SELECT
        linha,
        COUNT(*) AS total_validacoes
    FROM read_parquet(?, hive_partitioning = true)
    WHERE ano = 2026 AND mes = 3
    GROUP BY linha
    ORDER BY total_validacoes DESC
    LIMIT 5
    """,
    [caminho],
).fetchall()

for linha in resultado:
    print(linha)

con.close()