import os

from google import genai
from google.genai import types
from src.agent.agent import criar_chat

def mostrar_evento(evento):
    print(
        f"[EVENTO] {evento['ferramenta']} "
        f"→ {evento['estado']} "
        f"({evento['detalhes']})"
    )

def main() -> None:
    """Inicia uma conversa com o agente TransitMind AI."""
    with genai.Client() as client:
        chat = criar_chat(
            client,
            callback=mostrar_evento,
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