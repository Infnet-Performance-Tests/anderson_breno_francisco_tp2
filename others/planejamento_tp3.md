# Planejamento da próxima etapa (TP4/TP5)

**Grupo:** Anderson, Breno e Francisco · **Data:** 26/10/2026

Este documento registra as três definições que conduzem a fase preditiva e a fase adversarial
do projeto: o modelo candidato, a representação do texto e o alvo autorizado do pentest. A
base para as decisões está nas seções 2 e 3 do notebook [`eda/eda_tp3.ipynb`](../eda/eda_tp3.ipynb).

---

## Problema a resolver (resumo da formalização)

| Elemento | Definição |
| --- | --- |
| Pergunta | Dado o texto de uma mensagem de atendimento ao cliente, qual é a intenção do usuário? |
| Entrada (X) | `Ticket Description` (texto livre), o mesmo campo `text` de `POST /predict` |
| Alvo (y) | `Ticket Type`, com 5 classes: `billing_inquiry`, `cancellation_request`, `product_inquiry`, `refund_request`, `technical_issue` |
| Distribuição | Balanceada: 19,3% a 20,7% por classe, sem diferença significativa (χ² p = 0,115) |
| Métrica principal | **Macro-F1**, com acurácia, precisão/recall por classe e matriz de confusão como apoio |
| Piso de referência | Classificador aleatório estratificado: macro-F1 ≈ 0,20 |

---

## 1. Modelo candidato

### Escolha principal: Regressão Logística multinomial

`sklearn.linear_model.LogisticRegression` (solver `lbfgs`, multinomial, regularização L2).

Por que é adequada ao problema:

- **Feita para alvo categórico.** Modela diretamente P(intenção | texto) com uma *softmax* sobre as 5 classes. A saída é uma classe válida e a probabilidade de cada uma, o que preenche os campos `intent` e `confidence` da API sem pós-processamento. Essa é exatamente a limitação da regressão linear demonstrada no notebook (seção 3.4).
- **Funciona bem com texto vetorizado.** O CountVectorizer gera milhares de colunas esparsas, e modelos lineares regularizados são o *baseline* clássico e competitivo nesse cenário. A regularização L2 (`C`) controla o *overfitting* quando há mais palavras do que exemplos por classe.
- **Interpretável.** Cada classe tem um peso por palavra, então dá para listar os termos que mais empurram uma mensagem para "reembolso" ou para "problema técnico". Isso ajuda a explicar o modelo e a entender os ataques adversariais do TP4/TP5 (quais palavras um atacante precisa inserir para virar a predição).
- **Barata.** Treina em segundos nos 8.469 tickets e prevê em microssegundos, o que é compatível com uma rota síncrona e com rate limiting na API.
- **Classes balanceadas**, então não há necessidade de `class_weight` nem de reamostragem.

### Comparação: SVM linear

`sklearn.svm.LinearSVC` será treinado nos mesmos dados, como segundo candidato. Costuma ter
desempenho igual ou superior em texto esparso, mas não devolve probabilidades. Se vencer, entra
na API envolvido em `CalibratedClassifierCV` para gerar o `confidence`.

### Protocolo de treino e avaliação

1. Divisão 80/20 **estratificada** por `Ticket Type`, com `random_state=42`. O teste fica guardado até a avaliação final.
2. Ajuste de hiperparâmetros (`C`, `ngram_range`, `min_df`) por validação cruzada estratificada de 5 folds no treino, otimizando macro-F1.
3. Avaliação final no teste: macro-F1, acurácia, relatório por classe e matriz de confusão, sempre **comparados ao piso aleatório**.
4. O pipeline inteiro (`CountVectorizer` + modelo) será serializado num único artefato, de modo que a API aplique exatamente a mesma transformação usada no treino. A troca é feita em `fastapi/application/prediction_facade.py`, sem mudar o contrato HTTP.

---

## 2. Estratégia de representação do texto: CountVectorizer

`sklearn.feature_extraction.text.CountVectorizer` transforma cada mensagem em um vetor com a
**contagem de cada palavra** do vocabulário aprendido no treino (*bag-of-words*).

Configuração inicial:

| Parâmetro | Valor inicial | Motivo |
| --- | --- | --- |
| `lowercase` | `True` | "Refund" e "refund" são o mesmo termo |
| `ngram_range` | `(1, 1)`, testando `(1, 2)` | Bigramas capturam expressões como "cancel subscription" e "charged twice" |
| `min_df` | `2` | Descarta termos que aparecem em um único ticket (ruído, erros de digitação) |
| `max_df` | `0.95` | Descarta termos presentes em quase todos os tickets, como o boilerplate "Please assist" |
| `stop_words` | `None` no início | Palavras como "not" e "no" mudam a intenção. A remoção será testada, não assumida |
| `token_pattern` | padrão do sklearn | Ignora pontuação e o placeholder `{product_purchased}` vira o token `product_purchased` |

Por que o CountVectorizer:

- **Simples e transparente.** Cada coluna é uma palavra e cada valor é uma contagem. A matriz pode ser inspecionada e os pesos do modelo apontam termos legíveis, o que combina com a Regressão Logística e com a análise adversarial.
- **Adequado ao tamanho do dataset.** Com ~8,5 mil mensagens curtas (21 a 63 palavras), não há volume para treinar *embeddings* próprios, e a representação esparsa funciona bem com modelos lineares.
- **Sem vazamento.** O vocabulário é aprendido com `fit` só no treino (dentro do pipeline). Palavras novas no teste ou na API são simplesmente ignoradas.
- **Ponto de partida comparável.** É a base sobre a qual variações (TF-IDF, n-gramas, *embeddings*) podem ser medidas depois, mudando uma coisa de cada vez.

Limitações conhecidas: perde a ordem das palavras (exceto dentro dos n-gramas), não entende
sinônimos e é sensível a palavras injetadas, o que é justamente a superfície que o teste
adversarial vai explorar.

---

## 3. Risco principal: o texto do dataset não carrega sinal sobre a intenção

A verificação de viabilidade do notebook (seção 3.5) mostrou que **CountVectorizer + Regressão
Logística obtém macro-F1 de 0,194 ± 0,012**, contra **0,205 ± 0,016** do classificador
aleatório. As descrições são templates sintéticos (com o placeholder `{product_purchased}`
não substituído) e o `Ticket Type` é estatisticamente independente até do `Ticket Subject`
(χ² p = 0,98). **Com este dataset, nenhum modelo vai aprender a intenção a partir do texto.**

Alternativas para decisão da equipe no início do TP4:

| Opção | O que muda | Prós | Contras |
| --- | --- | --- | --- |
| A. Manter o dataset e documentar | Treinar como planejado e reportar o resultado contra o piso | Cumpre o roteiro sem mudar dados | O modelo da API será, na prática, aleatório |
| B. Rotular uma amostra pelo conteúdo | Reetiquetar manualmente ~500–1.000 descrições conforme o que o texto diz | Mantém o dataset do projeto | Trabalho manual, e os templates repetem frases genéricas |
| C. Complementar com um dataset de intenções com texto real | Usar um corpus público de atendimento rotulado por intenção para treinar, mantendo as 5 classes | Modelo realmente funcional na API | Exige mapear as classes e justificar a troca |

O pipeline, as métricas e a API não mudam em nenhuma das opções.

---

## 4. Alvo autorizado para o teste adversarial (TP4/TP5)

| Item | Valor |
| --- | --- |
| **URL do alvo** | **http://rest.vulnweb.com** |
| IP resolvido (26/10/2026) | `18.215.71.186` |
| O que é | *Invicti Vulnerable REST API*: API REST deliberadamente vulnerável, mantida pela Invicti (Acunetix) e publicada para que ferramentas e profissionais de segurança pratiquem testes |
| Por que este alvo | A equipe ainda não tem a API publicada em um endereço acessível pela internet, e a decisão foi usar uma API pública de testes cujo mantenedor disponibiliza o serviço para esse fim |
| API própria da equipe | Roda localmente em `http://127.0.0.1:8000` (`/docs` para a documentação). Se for publicada antes do TP4, o endereço público substitui ou complementa o alvo acima |

Regras de engajamento:

- Testar **somente** o host `rest.vulnweb.com`. Nenhum outro domínio ou IP, nem a infraestrutura do provedor de nuvem que o hospeda.
- **Sem negação de serviço:** nada de *flood*, *fuzzing* massivo sem limite de taxa ou ataques de exaustão de recursos. O serviço é compartilhado com outros usuários.
- Não usar dados obtidos no alvo fora do contexto acadêmico, e não publicar credenciais ou tokens encontrados.
- Registrar data/hora, ferramenta e comandos de cada atividade para o relatório.
- Antes de começar o TP4, confirmar que o endereço continua no ar e que o IP não mudou (é um serviço em nuvem).
