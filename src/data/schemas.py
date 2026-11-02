COLUNAS_COMUNS = {
    "Cartão Hash": "cartao_hash",
    "Data da Transação": "data_transacao",
    "Data do Processamento": "data_processamento",
    "Descrição da Aplicação": "descricao_aplicacao",
    "Sindicato": "sindicato",
    "Operadora": "operadora",
    "Linha": "linha",
    "Nº Carro": "numero_carro",
    "Nº Validador": "numero_validador",
}

COLUNAS_FINANCEIRAS = {
    "Vl Linha": "valor_linha",
    "Vl Trans": "valor_transacao",
    "Vl Subsídio": "valor_subsidio",
}

COLUNAS_SENTIDO = {
    "Sentido": "sentido",
}

COLUNAS_BU = {
    "Qtde Integrações": "indice_integracao",
    "Data da Ordem": "data_ordem",
    "Nº Ordem": "numero_ordem",
}

COLUNAS_GRATUIDADE = {
    "Escola": "escola",
    "Nº Censo Escola": "numero_censo_escola",
}


ESQUEMAS = {
    "BU": {
        "colunas": {
            **COLUNAS_COMUNS,
            **COLUNAS_FINANCEIRAS,
            **COLUNAS_SENTIDO,
            **COLUNAS_BU,
        },
        "descartar": ["Nº Cartão"],
        "colunas_opcionais": {"Cartão Hash"},
    },

    "BE": {
        "colunas": {
            **COLUNAS_COMUNS,
            **COLUNAS_FINANCEIRAS,
            **COLUNAS_SENTIDO,
        },
        "descartar": ["Nº Cartão"],
        "colunas_opcionais": {"Cartão Hash"},
    },

    "GRATUIDADE": {
        "colunas": {
            **COLUNAS_COMUNS,
            **COLUNAS_GRATUIDADE,
        },
        "descartar": [
            "Nº Cartão",
            "Transações",
        ],
        "colunas_opcionais": {"Cartão Hash"},
    },
}


TIPOS_COMUNS = {
    "cartao_hash": "string",
    "data_transacao": "datetime",
    "data_processamento": "datetime",
    "descricao_aplicacao": "string",
    "sindicato": "string",
    "operadora": "string",
    "linha": "string",
    "numero_carro": "string",
    "numero_validador": "string",
}

TIPOS_FINANCEIROS = {
    "valor_linha": "decimal(12,2)",
    "valor_transacao": "decimal(12,2)",
    "valor_subsidio": "decimal(12,2)",
}

REGRAS = {
    "BU": {
        "nulos_como_zero": [],
        "datas": {
            "data_transacao": "%d/%m/%Y %H:%M:%S",
            "data_processamento": "%d/%m/%Y %H:%M:%S",
            "data_ordem": "%Y-%m-%d",
        },
    },

    "BE": {
        "nulos_como_zero": ["valor_subsidio"],
        "datas": {
            "data_transacao": "%d/%m/%Y %H:%M:%S",
            "data_processamento": "%d/%m/%Y %H:%M:%S",
        },
    },

    "GRATUIDADE": {
        "nulos_como_zero": [],
        "datas": {
            "data_transacao": "%Y-%m-%d %H:%M:%S",
            "data_processamento": "%Y-%m-%d %H:%M:%S",
        },
    },
}


SINDICATOS_SEM_SENTIDO = {
    "BARCAS",
    "METRÔ RIO",
    "VANS INTERMUNICIPAIS",
    "SUPERVIA",
}

OPERADORAS_SEM_SENTIDO = {
    "BRT RIO S.A.",
}
