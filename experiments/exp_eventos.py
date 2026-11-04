from src.agent.eventos import notificar, mostrar_evento

notificar(
    mostrar_evento,
    "pesquisar_linhas",
    "executando",
    "Pesquisando 444L",
)

notificar(
    mostrar_evento,
    "pesquisar_linhas",
    "concluida",
    "1 linha encontrada",
)
