from google import genai
from google.genai import types

# 1. Guarda a chave de API da Google
client = genai.Client()


# 2. A funcao deve ter esse Docstring dizendo o que faz
def obter_status_automacao(dispositivo: str) -> str:
    """
        Busca o status atual de um dispositivo inteligente na casa do usuario.

        Args: dispositivo: Nome do aparelho, ex: lampada, ar-condicionado

    """
    return f"O dispositivo {dispositivo} esta ligado."


# 3. Configuracao com as funcoes que a IA vai poder usar
configuracao = types.GenerateContentConfig(
    tools=[obter_status_automacao], 
    max_output_tokens=500
)

# 4. Cria o chat que vai tracar a conversa
chat = client.chats.create(
    model="gemini-3.5-flash-lite",
    config=configuracao
)

# 5. Pergunta vinda do input
pergunta = input("O que voce gostaria de perguntar ao modelo? ");

# 4. mande a mensagem ao modelo e aguarde a resposta
resposta = chat.send_message(pergunta)

print(resposta.text)
