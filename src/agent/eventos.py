from collections.abc import Callable
from typing import Literal, NotRequired, TypedDict


EstadoFerramenta = Literal["executando", "concluida", "erro"]


class EventoFerramenta(TypedDict):
    ferramenta: str
    estado: EstadoFerramenta
    detalhes: str
    iniciado_em: NotRequired[float | None]
    tempo: NotRequired[float | None]


Notificador = Callable[[EventoFerramenta], None]


def notificar(
    callback: Notificador | None,
    ferramenta: str,
    estado: EstadoFerramenta,
    detalhes: str = "",
    iniciado_em: float | None = None,
    tempo: float | None = None,
) -> None:
    """
    Envia um evento de execução para um observador.

    Args:
        callback: Função responsável por receber o evento.
            Se None, nenhuma notificação é enviada.
        ferramenta: Nome da ferramenta executada.
        estado: Estado atual da execução.
        detalhes: Informações adicionais sobre o evento.
    """
    if callback is None:
        return

    callback({
        "ferramenta": ferramenta,
        "estado": estado,
        "detalhes": detalhes,
        "iniciado_em": iniciado_em,
        "tempo": tempo,
    })


def mostrar_evento(evento: EventoFerramenta):
    print(
        f"[{evento['estado']}] "
        f"{evento['ferramenta']}: "
        f"{evento['detalhes']}"
    )

