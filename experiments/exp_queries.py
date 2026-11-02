from datetime import datetime
from src.analytics.queries import linhas_mais_utilizadas

resultado = linhas_mais_utilizadas(
    tipo="BU",
    data_inicio=datetime(2026, 3, 1, 7),
    data_fim=datetime(2026, 3, 1, 9),
    limite=5,
)

for linha, quantidade in resultado:
    print(f"{linha}: {quantidade} registros")