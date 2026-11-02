
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse, unquote
import re
import shutil
import zipfile

import requests

from .types import TipoBase


# Identificadores dos conjuntos de dados no portal CKAN
DATASETS = {
    "BE": "setram_sbe",
    "BU": "setram_sbu",
    "GRATUIDADE": "setram_sgr",
}

API_URL = "https://dadosabertos.rj.gov.br/api/3/action/package_show"


def converter_data(valor: str | date) -> date:
    """
    Converte uma data para o tipo datetime.date.

    Aceita uma string no formato YYYY-MM-DD ou um objeto date,
    permitindo padronizar as datas recebidas pelo pipeline.

    Args:
        valor: Data a ser convertida.

    Returns:
        date: Data convertida.

    Raises:
        ValueError: Se a string não representar uma data válida.
        TypeError: Se o valor não for compatível com a conversão.
    """
    if isinstance(valor, date):
        return valor

    return datetime.strptime(valor, "%Y-%m-%d").date()


def obter_recursos(
    session: requests.Session,
    tipo: TipoBase,
    data_inicio: date,
    data_fim: date,
) -> list[dict]:
    """
    Consulta a API CKAN e identifica os recursos de uma base
    publicados no intervalo solicitado.

    Obtém a lista de recursos do conjunto de dados correspondente
    e filtra aqueles cujos nomes contêm uma data dentro do período,
    incluindo as datas inicial e final.

    O intervalo considera a data indicada no nome do recurso,
    não necessariamente a data das transações contidas nele.

    Args:
        session: Sessão HTTP utilizada para consultar a API.
        tipo: Identificador da base (BU, BE ou GRATUIDADE).
        data_inicio: Data inicial do período de publicação.
        data_fim: Data final do período de publicação.

    Returns:
        list[dict]: Recursos encontrados, contendo seus metadados,
        incluindo nomes e URLs de download.

    Raises:
        ValueError: Se a base informada for desconhecida.
        requests.RequestException: Se ocorrer uma falha HTTP.
        RuntimeError: Se a API indicar falha na consulta.
    """

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
    """
    Extrai o nome do arquivo a partir da URL de um recurso.

    Remove os componentes da URL que não pertencem ao caminho
    e decodifica caracteres especiais antes de obter o nome.

    Args:
        recurso: Dicionário de metadados contendo a URL do arquivo.

    Returns:
        str: Nome do arquivo com sua extensão.

    Raises:
        KeyError: Se o recurso não contiver a chave 'url'.
        ValueError: Se não for possível identificar um nome.
    """

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
    """
    Baixa um recurso para o diretório de destino.

    Realiza o download em blocos para evitar carregar o arquivo
    inteiro na memória RAM.

    O conteúdo é gravado inicialmente em um arquivo temporário
    com extensão .part, renomeado após a conclusão do download.

    Se o arquivo definitivo já existir e não estiver vazio,
    o download será ignorado.

    Quando o servidor fornece Content-Length, o tamanho recebido
    é comparado ao esperado. Essa verificação não garante,
    isoladamente, a integridade do conteúdo.

    Args:
        session: Sessão HTTP utilizada no download.
        recurso: Metadados do recurso, incluindo a URL.
        destino: Diretório onde o arquivo será armazenado.

    Returns:
        Path: Caminho do arquivo baixado ou reutilizado.

    Raises:
        requests.RequestException: Se ocorrer uma falha HTTP.
        OSError: Se houver erro de escrita ou espaço insuficiente.
        IOError: Se o tamanho recebido divergir do esperado.
    """

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
    """
    Extrai o conteúdo de um arquivo ZIP para uma pasta própria.

    Organiza os arquivos extraídos em um diretório associado
    ao nome do ZIP e verifica o espaço disponível antes de
    iniciar a extração.

    Também verifica os caminhos internos do arquivo para
    evitar que arquivos sejam escritos fora do destino previsto.

    Args:
        arquivo: Caminho do arquivo ZIP.
        destino: Diretório que receberá os arquivos extraídos.

    Returns:
        Path | None: Caminho da pasta extraída ou None caso
        o arquivo não seja reconhecido como ZIP.

    Raises:
        OSError: Se houver espaço insuficiente ou erro de escrita.
        ValueError: Se o ZIP contiver caminhos inseguros.
        zipfile.BadZipFile: Se o arquivo ZIP estiver corrompido.
    """

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
    tipos: tuple[TipoBase, ...] = ("BE", "BU", "GRATUIDADE"),
    extrair: bool = True,
    manter_zip: bool = False
) -> dict:
    """
    Baixa os recursos de uma ou mais bases publicados em um período.

    Coordena a consulta à API CKAN, a seleção dos recursos,
    o download dos arquivos e sua extração opcional.

    Organiza os arquivos em subdiretórios por base e retorna
    um relatório com os downloads realizados, os recursos
    ignorados e as datas sem publicações encontradas.

    As datas inicial e final são inclusivas. O período se refere
    à publicação dos arquivos, não às datas das transações.

    Args:
        data_inicio: Data inicial no formato YYYY-MM-DD ou date.
        data_fim: Data final no formato YYYY-MM-DD ou date.
        destino: Diretório principal para armazenamento.
        tipos: Bases que serão baixadas.
        extrair: Define se os arquivos ZIP serão extraídos.
        manter_zip: Define se os ZIPs serão preservados após
            uma extração bem-sucedida.

    Returns:
        dict: Relatório por base, contendo:
            - baixados: Caminhos dos arquivos baixados.
            - ignorados: Recursos que não exigiram novo download.
            - sem_publicacao: Datas sem recursos correspondentes.

    Raises:
        ValueError: Se o intervalo ou uma base forem inválidos.
        requests.RequestException: Se ocorrer uma falha HTTP.
        OSError: Se houver problemas no armazenamento.
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
