# Decisões técnicas — TransitMind AI

Este documento registra decisões de engenharia adotadas no desenvolvimento do **TransitMind AI**, com seus contextos, justificativas, consequências e limitações. Seu objetivo é explicar não apenas *o que* foi implementado, mas *por que* determinadas abordagens foram escolhidas.

**Escopo:** protótipo de exploração de dados públicos de transporte do Estado do Rio de Janeiro. As decisões refletem o código disponível para revisão e as atualizações realizadas durante a preparação do portfólio. A implementação de uma regra não significa que sua interpretação operacional esteja validada para todas as bases ou períodos.

> **Convenção de status:** **Implementada** indica uma decisão presente no código ou confirmada na revisão do protótipo; **Em investigação** indica uma questão semântica ou técnica ainda sujeita a validação; **Planejada** indica evolução que ainda não faz parte do sistema.

---

## DT-001 — Separação entre ingestão e processamento

**Status:** Implementada.

**Contexto:** Os arquivos publicados pela SETRAN-RJ precisam ser baixados, extraídos, tratados e preparados para análise.

**Decisão:** Manter responsabilidades distintas para ingestão, pré-processamento, armazenamento e consultas analíticas.

**Motivação:**
- Isolar requisições HTTP, regras de transformação e operações analíticas.
- Permitir testar e executar as etapas separadamente.
- Facilitar manutenção e reaproveitamento do pipeline.

**Implementação:** Os módulos `src/data/ingestion.py`, `preprocessing.py` e `storage.py` concentram etapas diferentes; `src/analytics/` contém as consultas.

**Consequência:** A estrutura tem mais componentes, mas evita acoplamento entre download de arquivos e perguntas ao agente. A ingestão ocorre em processo separado do chat, não automaticamente a cada pergunta.

## DT-002 — Compatibilidade com esquemas históricos

**Status:** Implementada.

**Contexto:** Arquivos antigos podem não possuir a coluna `Cartão Hash`, presente nos esquemas recentes.

**Decisão:** Tratar essa coluna como opcional no esquema, preenchendo-a com valores nulos quando ausente, sem criar identificadores artificiais.

**Motivação:** Preservar a possibilidade de processar históricos com diferenças estruturais.

**Implementação:** `src/data/schemas.py` define as colunas opcionais; `padronizar_colunas()` usa o esquema para padronizar a saída.

**Limitação:** A ausência de identificadores confiáveis impede determinadas análises de sequência de validações por cartão.

## DT-003 — Tratamento conservador de inconsistências semânticas

**Status:** Em investigação contínua.

**Contexto:** Alguns campos possuem definições formais que não são suficientes para interpretar todos os registros de maneira consistente. Um exemplo é o campo `Sentido`, cujo comportamento varia conforme o modal.

**Decisão:** Não inferir direções ou características operacionais sem evidência específica. Preservar, quando possível, a informação original e documentar as transformações aplicadas.

**Motivação:** Um valor tecnicamente válido pode produzir uma conclusão incorreta se seu significado operacional estiver errado.

**Consequência:** Algumas análises ficam indisponíveis ou mais restritas até a validação da semântica dos campos.

**Relação com a DT-006:** Esta decisão estabelece o princípio geral. A DT-006 documenta uma normalização concreta adotada no protótipo.

## DT-004 — Precisão e regras para valores monetários

**Status:** Implementada; testes por coluna em evolução.

**Contexto:** BU e BE contêm valores de tarifa, transação e subsídio. Usar números binários de ponto flutuante pode introduzir imprecisão em cálculos financeiros.

**Decisão:** Converter valores monetários para `Decimal`, exigir duas casas decimais e armazenar em Parquet com `decimal128(12, 2)`.

**Motivação:** Preservar a representação decimal exata dos valores financeiros.

**Implementação:** `converter_decimal()` e `converter_valores_monetarios()` em `src/data/preprocessing.py`, com tipos explícitos em `src/data/storage.py`.

**Regra específica:** Na base BE, a configuração admite interpretar `valor_subsidio` ausente como zero. Essa permissão deve ser aplicada **por coluna** (`coluna in REGRAS[tipo]["nulos_como_zero"]`), não a todos os campos monetários da base.

**Limitação:** A regra de preenchimento reflete uma interpretação operacional adotada para o protótipo. Não deve ser generalizada para outros campos sem validação. Os testes precisam cobrir a diferença entre colunas que aceitam ou rejeitam valores ausentes.

## DT-005 — Armazenamento em Parquet particionado

**Status:** Implementada.

**Contexto:** Os CSVs podem ser volumosos, e o agente precisa consultar períodos específicos com eficiência.

**Decisão:** Converter registros processados para Parquet, organizando arquivos por **base, ano e mês da transação**, permitindo que um mesmo lote de origem gere arquivos em mais de uma partição.

**Motivação:**
- Evitar reler e transformar os CSVs a cada pergunta.
- Consultar diretamente as partições mensais necessárias usando DuckDB.
- Acrescentar novos lotes sem regravar um grande arquivo mensal único.

**Implementação:** `salvar_particionado()` e `salvar_parquet()` em `src/data/storage.py`. Os Parquets usam esquema PyArrow explícito e compactação Snappy.

**Cuidados:**
- A data de publicação do arquivo pode diferir da data da transação.
- A gravação de cada arquivo é validada antes da substituição do destino, mas a gravação de todos os arquivos de um lote não é uma transação única.
- A quantidade e o tamanho ideais de arquivos por partição ainda podem ser refinados.

## DT-006 — Normalização do campo `Sentido` por modal

**Status:** Implementada como regra do protótipo; validação semântica em evolução.

**Contexto:** O dicionário oficial define `Sentido` como 0 (não informado), 1 (ida) e 2 (volta). Em determinados registros de transporte, os valores observados não permitem atribuir ida ou volta com confiança.

**Decisão:** Para sindicatos ou operadoras previamente configurados como não confiáveis nesse aspecto, normalizar `sentido` para 0 e preservar o valor recebido em `sentido_original`.

**Motivação:** Impedir que o agente apresente distribuições de ida/volta baseadas em códigos que não possuem interpretação operacional confirmada.

**Implementação:** `normalizar_sentido()` e conjuntos de configuração em `src/data/schemas.py`; a análise por veículo rejeita filtros de sentido 1 ou 2 quando aplicados a origens marcadas como não confiáveis.

**Limitações:**
- A classificação dos modais foi adotada com base na investigação dos dados e pode precisar de revisão.
- Um sentido 0 processado pode ser original ou resultado da normalização; `sentido_original` preserva essa distinção.
- Ainda é desejável registrar métricas de quantos valores foram alterados por base e modal.

## DT-007 — Interpretação do índice de integração

**Status:** Implementada; interpretação operacional sujeita a validação adicional.

**Contexto:** A base BU contém `Qtde Integrações`, descrita no dicionário oficial como a quantidade de integrações realizadas na mesma viagem.

**Decisão:** Renomear o campo para `indice_integracao`, preservando seus valores sem somar 1 ou criar uma contagem derivada.

**Motivação:** Segundo a interpretação utilizada no projeto, o campo se comporta como índice de validações na sequência, começando em zero; o nome reduz o risco de confundi-lo com a contagem total de passageiros, viagens ou validações.

**Implementação:** Renomeação centralizada em `src/data/schemas.py` e conversão para inteiro anulável (`Int64`) em `preprocessar()`.

**Limitação:** Essa interpretação é mais específica do que a descrição do dicionário oficial. O índice, isoladamente, **não** determina o destino de um passageiro nem reconstrói integralmente uma viagem. A verificação sistemática de valores negativos ou inconsistentes permanece como melhoria.

## DT-008 — Controle simplificado de lotes processados

**Status:** Implementada.

**Contexto:** Um CSV de origem pode conter transações de meses distintos, e seu processamento pode produzir múltiplos Parquets.

**Decisão:** Usar um marcador `.done` por lote de origem, contendo os caminhos dos arquivos produzidos. Criá-lo apenas após concluir as gravações e validações necessárias.

**Motivação:**
- Evitar reprocessar arquivos já incorporados.
- Relacionar um arquivo de origem às partições que ele gerou.
- Permitir a retomada de uma ingestão simples, adequada ao MVP.

**Implementação:** `lote_concluido()` e `registrar_lote()` em `src/data/storage.py`; o catálogo utiliza os marcadores para identificar os arquivos concluídos.

**Limitações:**
- A existência de um `.done` não equivale a uma verificação completa do conteúdo de todos os registros.
- Não há transação atômica envolvendo vários Parquets.
- O controle não detecta automaticamente republicações ou mudanças de esquema.
- Reprocessamentos e falhas concorrentes exigiriam mecanismos mais robustos em produção.

**Premissa operacional:** Segundo as informações recebidas durante o projeto, arquivos já publicados não são alterados; mudanças futuras seriam publicadas em novas versões. Se essa premissa mudar, a estratégia deverá ser revista.

## DT-009 — Ferramentas controladas em vez de SQL arbitrário gerado por IA

**Status:** Implementada.

**Contexto:** Um modelo de linguagem interpreta perguntas de modo flexível, mas pode escolher filtros incorretos, formular consultas inadequadas ou produzir conclusões sem suporte nos dados.

**Decisão:** Integrar o Gemini por *function calling* a funções Python previamente implementadas, que validam parâmetros e executam consultas analíticas via DuckDB. O agente não recebe uma ferramenta genérica de SQL livre.

**Motivação:** Manter os cálculos e as regras de negócio em código auditável e testável, reduzindo a superfície de consultas inesperadas.

**Implementação:** `src/agent/agent.py` disponibiliza as operações de pesquisa de linhas, análise de validações por veículo e ranking de linhas. As consultas estão em `src/analytics/` e suas interfaces em `src/agent/tools.py`.

**Trade-off:** A abordagem oferece maior controle, mas limita as perguntas que podem ser respondidas às funções disponíveis. Novas capacidades exigem implementação e validação de ferramentas adicionais.

**Limitação:** Restringir as ferramentas não garante que o Gemini sempre escolha a função correta ou interprete corretamente o retorno.

## DT-010 — Semântica de `numero_carro` e elegibilidade da análise por veículo

**Status:** Implementada para os modais configurados.

**Contexto:** Nos registros de BRT examinados no projeto, `numero_carro` identifica a **estação de validação**, não um veículo. Contar valores distintos desse campo como se fossem veículos produziria um indicador enganoso.

**Decisão:** Excluir BRT e outros modais configurados como não elegíveis dos cálculos de veículos distintos observados. Para os registros elegíveis, identificar veículos observados pela combinação de `operadora` e `numero_carro`.

**Motivação:** Não apresentar um número tecnicamente computável como se fosse uma medida confiável de frota.

**Implementação:** Conjuntos de exclusão em `src/data/config.py` e filtros em `validacoes_por_veiculo_hora()` (`src/analytics/queries.py`).

**Limitação:** Mesmo nos modais elegíveis, **veículos distintos observados não equivalem à frota total em operação**. O indicador também não mede ocupação nem passageiros únicos.

## DT-011 — Interpretação conservadora de períodos e ausência de registros

**Status:** Implementada em regras de consulta e instruções do agente; cobertura de dados ainda limitada.

**Contexto:** O protótipo pode ter apenas parte dos arquivos de um período carregada. Uma consulta com zero validações registradas não demonstra que o serviço não operou.

**Decisão:**
- Usar explicitamente os períodos solicitados; não inventar uma data padrão para completar perguntas ambíguas.
- Interpretar contagens como **validações registradas**, e não passageiros únicos.
- Tratar ausência de registros como limitação de evidência, não como prova de paralisação do serviço.

**Implementação:** Instruções em `src/agent/agent.py`; consultas temporais em `src/analytics/queries.py`, que usam início inclusivo e fim exclusivo.

**Limitação:** Instruções ao modelo reduzem interpretações indevidas, mas não as impedem completamente. A aplicação ainda não possui uma validação abrangente de cobertura temporal por linha e por arquivo de origem.

## DT-012 — Observabilidade das chamadas de ferramentas

**Status:** Implementada.

**Contexto:** Respostas textuais de um agente não mostram, por si só, quais operações foram executadas nem quanto tempo levaram.

**Decisão:** Registrar eventos de início, conclusão e erro das ferramentas, com detalhes da operação e duração; disponibilizá-los na interface Streamlit.

**Motivação:** Facilitar depuração, inspeção do fluxo e identificação de gargalos do protótipo.

**Implementação:** `src/agent/eventos.py`, callbacks em `src/agent/agent.py` e painel lateral em `app.py`.

**Limitações:**
- O tempo exibido para uma ferramenta não deve ser confundido com o tempo total de resposta do Gemini.
- A visualização dos eventos não constitui uma auditoria completa da precisão dos dados nem garante correção das interpretações do modelo.

## DT-013 — Preparação reproduzível de um recorte demonstrativo

**Status:** Implementada e testada localmente durante a preparação do portfólio (informação do autor).

**Contexto:** Clonar o código não basta para responder perguntas: são necessários dados já processados, dependências Python e configuração de acesso ao Gemini.

**Decisão:** Disponibilizar um script de preparação que utilize **BU, publicações de 01 a 05/03/2026**, reaproveitando o pipeline existente, e documentar a execução local com Python **3.13.5**.

**Motivação:** Permitir que outra pessoa reproduza uma demonstração com dados públicos, sem distribuir os arquivos brutos ou os Parquets diretamente pelo Git.

**Trade-off:** O procedimento depende da disponibilidade dos recursos externos, de tempo de download e de capacidade de memória/disk do ambiente. O recorte demonstrativo não deve ser confundido com a cobertura completa do sistema.

**Observação:** Esta atualização foi informada após o ZIP originalmente revisado. Conferir o arquivo `scripts/preparar_demo.py` e os comandos do README na versão publicada antes da revisão final do portfólio.

---

## Limitações e decisões em aberto

- **Cobertura dos dados:** verificar a completude dos períodos carregados e não atribuir ausência de registros à ausência de serviço.
- **Regras semânticas:** validar as convenções de `Sentido`, `indice_integracao` e identificação de veículos para cada modal.
- **Qualidade:** ampliar testes automatizados, especialmente para tratamento monetário por coluna, datas e consultas analíticas.
- **Segurança e privacidade:** manter credenciais fora do repositório e revisar o tratamento de identificadores, erros e parâmetros antes de qualquer publicação como serviço.
- **Pipeline:** definir política de descarte dos CSVs, verificações de integridade mais amplas, tratamento de concorrência e versionamento de esquemas.
- **Produto:** expandir o conjunto de ferramentas e validar utilidade, compreensão e correção com usuários reais; ainda não há métricas de impacto validadas.

## Referências internas

- `src/data/schemas.py` — esquemas, formatos e regras por base.
- `src/data/preprocessing.py` — conversões e normalização.
- `src/data/storage.py` — escrita de Parquet e controle de lotes.
- `src/data/catalog.py` — catálogo pesquisável.
- `src/data/config.py` — configurações e regras por modal.
- `src/analytics/queries.py` — cálculos e filtros analíticos.
- `src/agent/agent.py` e `src/agent/tools.py` — integração com o Gemini e exposição das ferramentas.
- `app.py` — interface Streamlit e eventos visíveis ao usuário.