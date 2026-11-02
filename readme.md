# TransitMind-AI — Análise de Dados de Transporte com IA

## Sobre o projeto

Este projeto investiga o uso de inteligência artificial para facilitar a exploração de dados públicos do transporte do estado do Rio de Janeiro.

A proposta é desenvolver um protótipo que permita realizar perguntas em linguagem natural sobre os dados e obter análises fundamentadas em consultas executadas por ferramentas de processamento de dados.

O objetivo é tornar a exploração de grandes volumes de informações mais acessível, especialmente para perguntas que não foram previstas em dashboards tradicionais.

**Status:** Em desenvolvimento — estruturação e tratamento dos dados.

## Bases utilizadas

Os dados são obtidos do Portal de Dados Abertos do Estado do Rio de Janeiro, a partir de três conjuntos:

- **BU:** Bilhete Único
- **BE:** Bilhetagem Eletrônica
- **GRATUIDADE:** Transações de gratuidade

Cada conjunto possui características e limitações próprias, documentadas no projeto.

## Arquitetura planejada

1. **Ingestão:** obtenção dos arquivos publicados no portal.
2. **Pré-processamento:** padronização de colunas, tipos e regras de qualidade.
3. **Armazenamento:** conversão para Parquet, com particionamento temporal.
4. **Análise:** consultas estruturadas utilizando DuckDB.
5. **Agente de IA:** interpretação de perguntas em linguagem natural e utilização de ferramentas de consulta controladas.
6. **Interface:** apresentação das análises e resultados.

Nem todas as etapas estão implementadas.

## Tecnologias

- Python
- Pandas
- Requests
- PyArrow (planejado)
- DuckDB (planejado)

## Estrutura do projeto

```text
src/
  data/
    ingestion.py
    preprocessing.py
    schemas.py
    types.py

data/
  raw/
  processed/

docs/
  decisoes_tecnicas.md

tests/
```

## Estado atual

- [x] Implementação inicial da ingestão de dados.
- [x] Definição dos esquemas das três bases.
- [x] Padronização dos nomes das colunas.
- [x] Compatibilidade inicial com arquivos históricos sem `Cartão Hash`.
- [x] Conversão inicial de datas.
- [ ] Conversão e validação completa dos tipos.
- [ ] Exportação para Parquet.
- [ ] Consultas analíticas com DuckDB.
- [ ] Integração com um agente de IA.
- [ ] Interface de exploração.

## Limitações

O projeto utiliza dados públicos que podem conter inconsistências, diferenças históricas de estrutura e campos cuja interpretação depende de regras operacionais.

A presença de um dado no arquivo não garante sua confiabilidade semântica. As análises deverão respeitar essas limitações e as restrições de privacidade.

Este é um protótipo em desenvolvimento, não uma plataforma oficial da SETRAN.

## Documentação

As escolhas de arquitetura, alternativas consideradas e limitações conhecidas estão registradas em [Decisões técnicas](docs/decisoes_tecnicas.md).