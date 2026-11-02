
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse, unquote
import re
import shutil
import zipfile

import requests


# Identificadores dos conjuntos de dados no portal CKAN
DATASETS = {
    "BE": "setram_sbe",
    "BU": "setram_sbu",
    "GRATUIDADE": "setram_sgr",
}

API_URL = "https://dadosabertos.rj.gov.br/api/3/action/package_show"


def converter_data(valor: str | date) -> date:
    """Converte uma string YYYY-MM-DD ou date em date."""
    if isinstance(valor, date):
        return valor

    return datetime.strptime(valor, "%Y-%m-%d").date()


def obter_recursos(
    session: requests.Session,
    tipo: str,
    data_inicio: date,
    data_fim: date,
) -> list[dict]:
    """Consulta o CKAN e retorna os arquivos do período informado."""

    if tipo not in DATASETS:
        raise ValueError(f"Tipo de dado desconhecido: {tipo}")

    response = session.get(
        API_URL,
        params={"id": DATASETS[tipo]},
        timeout=(10, 60),
    )
    response.raise_for_status()

    resultado = response.json()

    if not resultado.get("success"):
        raise RuntimeError(f"Falha ao consultar o conjunto {tipo}")

    recursos = resultado["result"]["resources"]

    # Exemplo: TRANSACAO_BU_PUBLICO_2026_03_01
    prefixo = re.escape(f"TRANSACAO_{tipo}_PUBLICO")
    padrao = re.compile(
        prefixo + r"_(\d{4})_(\d{2})_(\d{2})"
    )

    encontrados = []

    for recurso in recursos:
        nome = recurso.get("name", "")
        correspondencia = padrao.search(nome)

        if not correspondencia:
            continue

        ano, mes, dia = map(int, correspondencia.groups())

        try:
            data_arquivo = date(ano, mes, dia)
        except ValueError:
            print(f"Aviso: data inválida no recurso {nome}")
            continue

        if data_inicio <= data_arquivo <= data_fim:
            encontrados.append(recurso)

    return encontrados


def nome_arquivo(recurso: dict) -> str:
    """Obtém um nome de arquivo a partir da URL do recurso."""

    url = recurso["url"]
    nome = Path(unquote(urlparse(url).path)).name

    if not nome:
        raise ValueError(f"Não foi possível obter o nome do arquivo: {url}")

    return nome


def baixar_arquivo(
    session: requests.Session,
    recurso: dict,
    destino: Path,
) -> Path:
    """Baixa um arquivo sem deixar um download incompleto como definitivo."""

    destino.mkdir(parents=True, exist_ok=True)

    nome = nome_arquivo(recurso)
    arquivo = destino / nome
    temporario = destino / f"{nome}.part"

    # Não baixa novamente um arquivo já existente.
    if arquivo.exists() and arquivo.stat().st_size > 0:
        return arquivo

    # Remove eventual download incompleto de uma execução anterior.
    temporario.unlink(missing_ok=True)

    url = recurso["url"]

    try:
        with session.get(
            url,
            stream=True,
            timeout=(10, 120),
        ) as response:
            response.raise_for_status()

            tamanho_esperado = response.headers.get("Content-Length")
            tamanho_esperado = (
                int(tamanho_esperado) if tamanho_esperado else None
            )

            espaco_livre = shutil.disk_usage(destino).free

            if tamanho_esperado is not None:
                if tamanho_esperado > espaco_livre:
                    raise OSError("Espaço insuficiente em disco.")

            tamanho_baixado = 0

            with temporario.open("wb") as arquivo_temp:
                for bloco in response.iter_content(chunk_size=1024 * 1024):
                    if not bloco:
                        continue

                    arquivo_temp.write(bloco)
                    tamanho_baixado += len(bloco)

            if (
                tamanho_esperado is not None
                and tamanho_baixado != tamanho_esperado
            ):
                raise IOError(
                    f"Download incompleto de {nome}: "
                    f"{tamanho_baixado} de {tamanho_esperado} bytes."
                )

        temporario.replace(arquivo)

    except Exception:
        temporario.unlink(missing_ok=True)
        raise

    return arquivo


def extrair_zip(arquivo: Path, destino: Path) -> Path | None:
    """Extrai um ZIP para uma pasta própria, verificando os caminhos."""

    if not zipfile.is_zipfile(arquivo):
        return None

    pasta = destino / "extracted" / arquivo.stem
    marcador = pasta / ".complete"

    if marcador.exists():
        return pasta

    with zipfile.ZipFile(arquivo, "r") as zip_ref:
        tamanho_extraido = sum(
            info.file_size for info in zip_ref.infolist()
        )

        espaco_livre = shutil.disk_usage(destino).free

        if tamanho_extraido > espaco_livre:
            raise OSError(
                f"Espaço insuficiente para extrair {arquivo.name}."
            )

        pasta.parent.mkdir(parents=True, exist_ok=True)

        # Evita extração de arquivos para fora da pasta de destino.
        for info in zip_ref.infolist():
            caminho = (pasta / info.filename).resolve()

            try:
                caminho.relative_to(pasta.resolve())
            except ValueError:
                raise ValueError(
                    f"Caminho inseguro no ZIP: {info.filename}"
                )

        zip_ref.extractall(pasta)
        marcador.touch()

    return pasta


def baixar_periodo(
    data_inicio: str | date,
    data_fim: str | date,
    destino: str | Path,
    tipos: tuple[str, ...] = ("BE", "BU", "GRATUIDADE"),
    extrair: bool = True,
    manter_zip: bool = False
) -> dict:
    """
    Baixa os arquivos publicados em um período.

    Args:
        data_inicio: Primeiro dia do período (inclusive).
        data_fim: Último dia do período (inclusive).
        destino: Diretório onde os arquivos serão armazenados.
        tipos: Conjuntos de dados que serão baixados.
        extrair: Se True, extrai os ZIPs.
        manter_zip: Se False, deleta os ZIPs originais.

    Returns:
        Dicionário com arquivos baixados, ignorados e datas sem publicação.
    """

    inicio = converter_data(data_inicio)
    fim = converter_data(data_fim)

    if inicio > fim:
        raise ValueError("A data inicial deve ser anterior à data final.")

    for tipo in tipos:
        if tipo not in DATASETS:
            raise ValueError(f"Tipo de dado desconhecido: {tipo}")

    destino = Path(destino)

    relatorio = {}

    with requests.Session() as session:
        for tipo in tipos:
            pasta_tipo = destino / tipo
            pasta_tipo.mkdir(parents=True, exist_ok=True)

            recursos = obter_recursos(
                session,
                tipo,
                inicio,
                fim,
            )

            datas_encontradas = set()
            baixados = []
            ignorados = []

            for recurso in recursos:
                arquivo = pasta_tipo / nome_arquivo(recurso)
                pasta_extraida = pasta_tipo / "extracted" / arquivo.stem
                marcador = pasta_extraida / ".complete"

                if extrair and marcador.exists():
                    ignorados.append(arquivo)
                    continue

                if arquivo.exists() and arquivo.stat().st_size > 0:
                    ignorados.append(arquivo)
                else:
                    arquivo = baixar_arquivo(session, recurso, pasta_tipo)
                    baixados.append(arquivo)

                if extrair:
                    extrair_zip(arquivo, pasta_tipo)

                    if not manter_zip:
                        arquivo.unlink(missing_ok=True)

                padrao = re.compile(
                    rf"^TRANSACAO_{re.escape(tipo)}_PUBLICO_"
                    r"(\d{4})_(\d{2})_(\d{2})\.csv$",
                    re.IGNORECASE,
                )

                if padrao:
                    correspondencia = re.search(
                        r"_(\d{4})_(\d{2})_(\d{2})(?=\.|$)",
                        recurso.get("name", ""),
                    )

                    if correspondencia:
                        ano, mes, dia = map(int, correspondencia.groups())
                        datas_encontradas.add(date(ano, mes, dia))

            datas_esperadas = set()
            atual = inicio

            while atual <= fim:
                datas_esperadas.add(atual)
                atual += timedelta(days=1)

            relatorio[tipo] = {
                "baixados": baixados,
                "ignorados": ignorados,
                "sem_publicacao": sorted(
                    datas_esperadas - datas_encontradas
                ),
            }

    return relatorio
