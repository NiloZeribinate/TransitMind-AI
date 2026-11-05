from scr.data.ingestion import baixar_periodo

relatorio = baixar_periodo(
    data_inicio="2026-03-01",
    data_fim="2026-03-05",
    destino="data/raw",
    tipos=("BU","BE", "GRATUIDADE")
)

for tipo, resultado in relatorio.items():
    print(f"\n{tipo}")
    print("Baixados:", len(resultado["baixados"]))
    print("Já existentes:", len(resultado["ignorados"]))
    print("Datas sem publicações:", len(resultado["sem_publicacao"]))
