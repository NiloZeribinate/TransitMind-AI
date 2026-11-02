# Decisões técnicas

Este documento registra as principais decisões de engenharia tomadas durante o desenvolvimento do projeto, incluindo suas justificativas, alternativas consideradas e limitações.

As decisões podem ser revisadas conforme o projeto evoluir.

---

## DT-001 — Separação entre ingestão e processamento

**Status:** Adotada

**Contexto:** Os arquivos disponibilizados pela SETRAN precisam ser baixados, extraídos, tratados e preparados para análise.

**Decisão:** Separar a ingestão dos dados do pré-processamento e da análise.

**Motivação:**
- Facilitar testes e manutenção.
- Permitir executar cada etapa independentemente.
- Evitar misturar requisições HTTP, manipulação de arquivos e análise estatística.

**Consequência:** O projeto terá módulos com responsabilidades específicas, exigindo uma organização inicial um pouco maior.

## DT-002 — Compatibilidade com esquemas históricos

**Status:** Adotada

**Contexto:** Arquivos antigos das bases não possuem a coluna `Cartão Hash`, presente nos arquivos recentes.

**Decisão:** Permitir a ausência dessa coluna durante o processamento, preenchendo-a com valores nulos no esquema padronizado.

**Motivação:** Preservar a possibilidade de análises históricas sem inventar identificadores.

**Limitação:** Não será possível realizar determinadas análises de sequência de validações por cartão nos períodos sem identificadores confiáveis.

## DT-003 — Tratamento de inconsistências semânticas

**Status:** Em investigação

**Contexto:** O campo `Sentido` possui valores documentados para ida e volta, mas seu comportamento observado em determinados modais gera dúvidas sobre a interpretação.

**Decisão:** Preservar os valores originais e evitar conclusões sobre direção de viagem até validar o significado do campo para cada modalidade.

**Motivação:** Impedir que dados tecnicamente válidos produzam interpretações incorretas.

## DT-004 — Representação monetária

**Status:** Escolhida; implementação pendente

**Contexto:** As bases BU e BE possuem valores financeiros, incluindo tarifas, pagamentos e subsídios.

**Decisão:** Utilizar tipos decimais de precisão fixa, com duas casas decimais.

**Motivação:** Evitar aproximações de ponto flutuante em cálculos monetários.

**Ponto de atenção:** Campos vazios de subsídio na BE podem representar zero. Essa regra deverá ser validada e aplicada especificamente ao campo, sem substituir indiscriminadamente outros valores ausentes.

## DT-005 — Estratégia de armazenamento

**Status:** Planejada

**Contexto:** Os arquivos são volumosos e o espaço disponível em disco é limitado.

**Decisão:** Planejar a conversão para Parquet, organizado por base, ano e mês da transação, permitindo múltiplos arquivos por partição.

**Motivação:**
- Melhorar a eficiência das consultas analíticas.
- Facilitar atualizações incrementais.
- Evitar reescrever grandes arquivos mensais a cada atualização.

**Limitações e cuidados:**
- A data de publicação/processamento pode ser posterior à data da transação.
- Será necessário controlar quais arquivos de origem já foram incorporados.
- Os dados brutos só poderão ser descartados após validação e confirmação de que podem ser recuperados.

## DT-006 — Normalização do sentido por modal

**Status:** Em implementação

**Contexto:** O dicionário oficial define `Sentido` como 0 (não informado), 1 (ida) e 2 (volta). Entretanto, a exploração das bases BU e BE identificou valores potencialmente artificiais ou ausentes em registros de metrô, trem, BRT, barcas e vans.

**Decisão:** Normalizar o sentido desses modais para 0, conforme a interpretação operacional adotada para o protótipo, preservando o valor original para rastreabilidade.

**Motivação:** Evitar que o agente de IA apresente distribuições incorretas de ida e volta a partir de códigos não confiáveis.

**Limitações:**
- A classificação dos modais precisa ser validada.
- A regra se baseia em observações empíricas e pode precisar de revisão.
- O código 0 no conjunto processado representará também uma normalização realizada por falta de confiabilidade semântica.

**Validação:** Registrar o número de valores modificados por base e por modal, distinguindo valores originalmente ausentes de valores originalmente iguais a 2.

## DT-007 — Interpretação do índice de integração

**Status:** Adotada

**Contexto:** A base de Bilhete Único possui a coluna `Qtde Integrações`, descrita no dicionário oficial como a quantidade de integrações realizadas na mesma viagem.

Segundo a interpretação operacional adotada no projeto, o campo representa a sequência de validações, começando em zero na primeira validação e aumentando nas integrações seguintes.

**Decisão:** Renomear a coluna para `indice_integracao`, preservando seus valores originais, sem adicionar 1 ou criar colunas derivadas.

**Motivação:**
- Tornar o nome mais coerente com o significado operacional identificado.
- Evitar confundir o índice com a quantidade total de validações ou viagens.
- Preservar a informação original sem transformações desnecessárias.
- Manter a padronização centralizada no `schemas.py`.

**Consequências:**
- A primeira validação possui índice 0.
- A segunda validação possui índice 1, e assim sucessivamente.
- O campo será armazenado como inteiro anulável (`Int64`) no Pandas.
- Não será necessária uma etapa específica de transformação para esse campo.

**Limitações:** A interpretação se baseia na experiência prática com os dados e é mais específica do que a descrição apresentada no dicionário oficial. O índice, isoladamente, não permite reconstruir integralmente uma viagem nem determinar seu destino.

**Validação:** Conferir se os valores observados são inteiros não negativos e registrar eventuais inconsistências durante o processamento.

## DT-008 — Controle simplificado de lotes processados

**Status:** Adotada para o protótipo; implementação pendente

**Contexto:** Um arquivo CSV publicado pela SETRAN pode conter transações de diferentes meses, gerando múltiplos arquivos Parquet. O processamento pode ser interrompido antes da conclusão de todas as gravações.

Segundo as informações obtidas em reuniões com a SETRAN, os arquivos publicados não são alterados posteriormente. Mudanças estruturais serão disponibilizadas em novas versões das bases.

**Decisão:** Utilizar um marcador de conclusão (`.done`) por lote de origem, criado somente após a gravação e validação de todos os arquivos Parquet correspondentes.

**Motivação:**
- Evitar reprocessamentos desnecessários.
- Identificar lotes concluídos sem depender dos CSVs originais.
- Permitir a exclusão controlada dos arquivos brutos.
- Reduzir a complexidade de implementação do MVP.

**Limitações:**
- A presença do marcador não substitui uma verificação integral da integridade dos dados.
- Não haverá detecção automática de alterações nos arquivos de origem.
- O reprocessamento de lotes incompletos poderá sobrescrever arquivos já produzidos.
- A publicação de múltiplos Parquets não será atomicamente transacional.
- Mudanças futuras no esquema poderão exigir reprocessamento e versionamento dos dados.

**Evolução para produto:** Implementar controle transacional de lotes, versionamento dos esquemas, rastreabilidade completa das fontes, tratamento de concorrência e mecanismos de recuperação de falhas.

---

## Decisões em aberto

- Política de validação e descarte dos arquivos brutos.
- Tamanho ideal dos arquivos Parquet.
- Identificação e tratamento de registros duplicados.
- Semântica operacional dos campos `Sentido` e `Qtde Integrações`.
- Estratégia de segurança e privacidade para as ferramentas do agente de IA.