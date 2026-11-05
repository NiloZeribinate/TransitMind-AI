import os

from google import genai
from google.genai import types
from time import perf_counter, time
from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo


from src.agent.tools import (
    pesquisar_linhas as _pesquisar_linhas,
    analisar_validacoes_por_veiculo as _analisar_validacoes,
    ranking_linhas_por_validacoes as _ranking_linhas,
)

from src.agent.eventos import Notificador, notificar

ResultadoCallback = Callable[[dict], None]

hoje = datetime.now(
    ZoneInfo("America/Sao_Paulo")
).strftime("%d/%m/%Y")

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

    APRESENTAÇÃO DE ANÁLISES:

    Quando a ferramenta de validações por veículo retornar sucesso,
    a interface web poderá apresentar automaticamente três gráficos:
    - Total de validações por hora;
    - Veículos distintos observados por hora;
    - Validações por veículo observado.

    Seu papel é interpretar os resultados, não reproduzir
    uma longa lista de valores horários.

    Destaque os principais padrões, horários de pico e
    variações relevantes, sempre com base nos dados retornados.

    Evite repetir todos os registros. Cite números específicos
    apenas quando ajudarem a explicar uma conclusão.

    Não afirme que você gerou os gráficos: a visualização
    é responsabilidade da interface.

    Use "validações registradas", não "passageiros únicos".
    Veículos observados não representam necessariamente
    a frota total em operação.

    Horas sem registros não comprovam ausência de serviço.
    Reconheça possíveis limitações de cobertura dos dados.
"""


def criar_chat(cliente: genai.Client, callback: Notificador | None = None, registrar_resultado: ResultadoCallback | None = None):
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
            resultado = _analisar_validacoes(linha, inicio, fim, sentido)

            if (resultado.get("status") == "sucesso" and registrar_resultado is not None):

                registrar_resultado({
                    "tipo": "validacoes_por_veiculo",
                    "linha": linha,
                    "base": resultado.get("base", "BU"),
                    "registros": resultado["registros"],
                })

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

    def ranking_linhas_por_validacoes(inicio: str, fim: str, limite: int = 10, tipo: str = "BU") -> dict:
        """
        Consulta as linhas com mais validações registradas.

        Args:
            inicio: Início do período em ISO 8601.
            fim: Final do período em ISO 8601.
            limite: Quantidade de linhas, de 1 a 20.
            tipo: Base BU, BE ou GRATUIDADE.

        Returns:
            dict: Ranking calculado ou erro estruturado.
        """
        iniciado_em = time()

        notificar(
            callback,
            "pesquisar_linhas",
            "executando",
            f"{limite} linhas mais usadas",
            iniciado_em=iniciado_em,
        )

        inicio_medicao = perf_counter()
        
        resultado = _ranking_linhas(inicio, fim, limite, tipo)

        if (
            resultado.get("status") == "sucesso"
            and registrar_resultado is not None
        ):
            registrar_resultado({
                "tipo": "ranking_linhas",
                "base": resultado["base"],
                "ranking": resultado["ranking"],
                "inicio": resultado["inicio"],
                "fim_exclusivo": resultado["fim_exclusivo"],
            })

        notificar(
            callback,
            "pesquisar_linhas",
            "concluida",
            f"{limite} linhas mais usadas",
            iniciado_em=iniciado_em,
            tempo=perf_counter() - inicio_medicao
        )

        return resultado
    
    configuracao = types.GenerateContentConfig(
        tools=[
            pesquisar_linhas,
            analisar_validacoes_por_veiculo,
            ranking_linhas_por_validacoes,
        ],
        system_instruction=(
            f"A data atual é {hoje}, no fuso horário de Brasília.\n"
            "Use essa data como referência temporal. "
            "Não presuma que os dados disponíveis cobrem a data atual. "
            "Quando o usuário não informar o período de uma análise, "
            "solicite essa informação, sem inventar datas.\n\n"
            + INSTRUCOES
        ),
    )

    chat = cliente.chats.create(
        model=os.getenv(
            "GEMINI_MODEL", "gemini-3.5-flash-lite"
        ),
        config=configuracao
    )

    return chat
