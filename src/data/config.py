NOMES_BASES = {
    "BU": "bilhete_unico",
    "BE": "bilhetagem_eletronica",
    "GRATUIDADE": "gratuidade",
}

# Modais cujos dados de sentido não são confiáveis.
SINDICATOS_SEM_SENTIDO = frozenset({
    "BARCAS",
    "METRÔ RIO",
    "SUPERVIA",
    "VANS INTERMUNICIPAIS",
    "VLT",
})

OPERADORAS_SEM_SENTIDO = frozenset({
    "BRT RIO S.A.",
})

# Modais excluídos do indicador por veículo.
SINDICATOS_EXCLUIDOS_VEICULOS = frozenset({
    "BARCAS",
    "METRÔ RIO",
    "SUPERVIA",
    "VLT",
})

OPERADORAS_EXCLUIDAS_VEICULOS = frozenset({
    "BRT RIO S.A.",
})
