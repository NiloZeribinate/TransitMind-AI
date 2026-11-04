
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from src.analytics.linhas import (
    buscar_linhas,
    LinhaNaoEncontradaError,
)

from .tools import analisar_validacoes_por_veiculo


def pesquisar_linhas(termo: str) -> dict:
    """
    Pesquisa linhas de transporte disponíveis no TransitMind AI.

    A pesquisa aceita nomes parciais, sem diferenciar letras
    maiúsculas, minúsculas ou acentos.

    Args:
        termo: Nome ou trecho do nome da linha desejada.

    Returns:
        dict: Status da pesquisa e lista de nomes oficiais
            encontrados no catálogo.
    """
    print(f"[TOOL] pesquisar_linhas(termo={termo!r})")

    try:
        linhas = buscar_linhas(termo=termo)

        return {
            "status": "encontradas",
            "linhas": linhas,
        }

    except LinhaNaoEncontradaError:
        return {
            "status": "nao_encontrada",
            "linhas": [],
        }


def main() -> None:
    """Inicia uma conversa com o agente TransitMind AI."""
    load_dotenv()

    modelo = os.getenv(
        "GEMINI_MODEL", "gemini-3.5-flash-lite"
    )

    with genai.Client() as client:
        configuracao = types.GenerateContentConfig(
            tools=[
                pesquisar_linhas,
                analisar_validacoes_por_veiculo,
            ],
            system_instruction="""
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

                Por enquanto, você só pode pesquisar linhas.
            """,
        )

        chat = client.chats.create(
            model=modelo,
            config=configuracao,
        )

        print("TransitMind AI iniciado!")
        print("Digite 'sair' para encerrar.")

        while True:
            pergunta = input("\nVocê: ").strip()

            if pergunta.lower() == "sair":
                break

            if not pergunta:
                continue

            resposta = chat.send_message(pergunta)

            print(
                "\nTransitMind AI:",
                resposta.text or "(Sem resposta textual)",
            )


if __name__ == "__main__":
    main()
