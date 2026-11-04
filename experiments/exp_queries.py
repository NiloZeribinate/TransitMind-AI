from datetime import datetime
from src.analytics.queries import linhas_mais_utilizadas, validacoes_por_veiculo_hora
from src.analytics.linhas import (
    buscar_linhas,
    validar_linha_exata,
)

resultado = linhas_mais_utilizadas(
    tipo="BU",
    data_inicio=datetime(2026, 3, 1, 7),
    data_fim=datetime(2026, 3, 1, 9),
    limite=5,
)

for linha, quantidade in resultado:
    print(f"{linha}: {quantidade} registros")
print("\n")


opcoes = buscar_linhas("444L")
print("Linhas encontradas:", opcoes)

if len(opcoes) == 1:
    linha = opcoes[0]

    validar_linha_exata(linha)

    resultado = validacoes_por_veiculo_hora(
        data_inicio=datetime(2026, 3, 1, 7),
        data_fim=datetime(2026, 3, 1, 10),
        linha=linha,
        sentido="todos",
        tipo="BU",
    )

    print(resultado)
else:
    print("É necessário selecionar uma das linhas encontradas.")
