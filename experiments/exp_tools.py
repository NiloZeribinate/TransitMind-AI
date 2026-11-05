from src.agent.tools import analisar_validacoes_por_veiculo, ranking_linhas_por_validacoes

# resultado = analisar_validacoes_por_veiculo(
#     linha="444L - PIABETA X PENHA",
#     inicio="2026-02-32T07:00:00",
#     fim="2026-03-01T09:00:00",
#     sentido="1",
# )

resultado = ranking_linhas_por_validacoes(
    inicio="2026-03-01",
    fim="2026-03-01",
    limite=10,
    tipo="BU",
)

print(resultado)
