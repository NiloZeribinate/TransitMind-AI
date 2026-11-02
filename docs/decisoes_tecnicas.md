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

---

## Decisões em aberto

- Política de validação e descarte dos arquivos brutos.
- Tamanho ideal dos arquivos Parquet.
- Identificação e tratamento de registros duplicados.
- Semântica operacional dos campos `Sentido` e `Qtde Integrações`.
- Estratégia de segurança e privacidade para as ferramentas do agente de IA.