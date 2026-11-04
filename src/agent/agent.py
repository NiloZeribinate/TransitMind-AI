import os

from google import genai
from google.genai import types

from src.agent.tools import (
    pesquisar_linhas as _pesquisar_linhas,
    analisar_validacoes_por_veiculo as _analisar_validacoes,
)

from time import perf_counter, time

from src.agent.eventos import Notificador, notificar


INSTRUCOES = """
    Você é o TransitMind AI, um assistente
    de análise dos transportes do Rio de Janeiro.

    Responda em português brasileiro.

    Utilize pesquisar_linhas quando precisar
    identificar nomes de linhas disponíveis.

    Se houver apenas uma correspondência,
    considere a linha identificada.

    Se houver várias correspondências,
    apresente as opções e peça ao usuário
    que especifique qual deseja.

    A ferramenta pode retornar até 10 opções,
    portanto não presuma que sejam todas.

    Nunca invente nomes de linhas ou valores.
    Não faça análises numéricas sem uma
    ferramenta apropriada.

    Ao interpretar resultados analíticos:

    - Diferencie ausência de validações registradas de
    ausência de operação do transporte.

    - Os dados disponíveis podem cobrir apenas parte
    do período solicitado.

    - Não atribua quedas de validações a horários de
    operação, demanda ou outros fatores sem evidências.

    - Use "veículos distintos observados", não "frota ativa".

    - Quando não houver evidências suficientes para explicar
    um padrão, apresente hipóteses como não verificadas.

    - Se o período não estiver definido, pergunte ao usuário
    antes de chamar qualquer ferramenta analítica.

    - Nunca invente datas, horários ou períodos padrão para
    preencher informações ausentes.

    - Não tente consultar períodos aleatórios para descobrir
    quais dados estão disponíveis.

    - Você pode interpretar datas em linguagem natural,
    como "amanhã", "dia seguinte" ou "das 7h às 9h",
    desde que haja contexto suficiente.

    - Caso uma consulta falhe por ausência de dados,
    informe o problema e peça outro período.

    - Não interprete ausência de registros como ausência
    de operação dos transportes.

    - BU significa Bilhete Único.
"""


def criar_chat(cliente: genai.Client, callback: Notificador | None = None):
    def pesquisar_linhas(termo: str) -> dict:
        """Pesquisa linhas de transporte pelo nome ou trecho informado."""
        iniciado_em = time()

        notificar(
            callback,
            "pesquisar_linhas",
            "executando",
            termo,
            iniciado_em=iniciado_em,
        )

        inicio_medicao = perf_counter()

        try:
            resultado = _pesquisar_linhas(termo)
            quantidade = len(resultado.get("linhas", []))

            notificar(
                callback,
                "pesquisar_linhas",
                "concluida",
                f"{quantidade} linha(s) encontrada(s)",
                iniciado_em=iniciado_em,
                tempo=perf_counter() - inicio_medicao,
            )

            return resultado

        except Exception as erro:
            notificar(
                callback,
                "pesquisar_linhas",
                "erro",
                str(erro),
                iniciado_em=iniciado_em,
                tempo=perf_counter() - inicio_medicao,
            )
            raise

    def analisar_validacoes_por_veiculo(linha: str, inicio: str, fim: str, sentido: str = "todos") -> dict:
        """Analisa as validações por veículo de uma linha em um período."""
        iniciado_em = time()

        notificar(
            callback,
            "analisar_validacoes_por_veiculo",
            "executando",
            linha,
            iniciado_em=iniciado_em,
        )

        inicio_medicao = perf_counter()

        try:
            resultado = _analisar_validacoes(
                linha, inicio, fim, sentido
            )

            houve_erro = resultado.get("status") == "erro"

            notificar(
                callback,
                "analisar_validacoes_por_veiculo",
                "erro" if houve_erro else "concluida",
                (
                    resultado.get("mensagem", linha)
                    if houve_erro else linha
                ),
                iniciado_em=iniciado_em,
                tempo=perf_counter() - inicio_medicao,
            )

            return resultado

        except Exception as erro:
            notificar(
                callback,
                "analisar_validacoes_por_veiculo",
                "erro",
                str(erro),
                iniciado_em=iniciado_em,
                tempo=perf_counter() - inicio_medicao,
            )
            raise
    
    configuracao = types.GenerateContentConfig(
        tools=[
            pesquisar_linhas,
            analisar_validacoes_por_veiculo,
        ],
        system_instruction=INSTRUCOES,
    )

    chat = cliente.chats.create(
        model=os.getenv(
            "GEMINI_MODEL", "gemini-3.5-flash-lite"
        ),
        config=configuracao
    )

    return chat
