# Projeto de Bloco — Classificação de intenções com API segura

**Grupo:** Anderson, Breno e Francisco

[![CI](https://github.com/Infnet-Performance-Tests/anderson_breno_francisco_tp2/actions/workflows/ci.yml/badge.svg?branch=tp3)](https://github.com/Infnet-Performance-Tests/anderson_breno_francisco_tp2/actions/workflows/ci.yml)

## Objetivo do projeto

Construir um sistema de atendimento ao cliente que responda à pergunta:

> **Dado o texto de uma mensagem de atendimento ao cliente, qual é a intenção do usuário?**

O projeto avança em duas frentes:

1. **Análise e modelagem** do *Customer Support Ticket Dataset*: EDA completa (TP1/TP2),
   regressão linear de diagnóstico e formalização do problema de classificação (TP3), e, a
   seguir, o treino do classificador (TP4).
2. **API FastAPI segura**, que vai servir o classificador: autenticação JWT, controle de
   acesso por ownership (anti-BOLA), validação estrita de entrada, headers de segurança, CORS
   com allowlist, rate limiting, testes automatizados no CI e auditoria com OWASP ZAP.

O TP3 é o pivô entre as duas fases: consolida o que foi construído, documenta as limitações e
planeja a fase preditiva e o teste adversarial ([`others/planejamento_tp3.md`](others/planejamento_tp3.md)).

---

## Estrutura de pastas

```text
.
├── README.md                     # este arquivo
├── requirements.txt              # dependências (API, EDA/ML e testes)
├── pyproject.toml                # configuração de pytest e ruff
├── Makefile                      # atalhos: install, db, run, test, lint, notebook
├── Dockerfile / docker-compose.yml
├── .env.example                  # modelo das variáveis JWT_SECRET_KEY e ALLOWED_ORIGINS
│
├── .github/workflows/ci.yml      # CI: lint + pytest tests/ -v a cada push
│
├── data/
│   └── customer_support_tickets.csv   # dataset original do Kaggle, sem alterações
│
├── eda/
│   └── eda_tp3.ipynb             # EDA completa (TP1, TP2 e TP3), já executada
│
├── fastapi/                      # código-fonte da aplicação
│   ├── main.py                   # ponto de entrada (uvicorn main:app)
│   ├── config.py                 # parâmetros do JWT, CORS e rate limit
│   ├── database.py               # engine SQLModel e dependência de sessão
│   ├── crud.py                   # todas as consultas (SQLModel, sem SQL raw)
│   ├── database.db               # banco SQLite com usuários e predictions de exemplo
│   ├── sqlite_database.py        # cria o schema e faz a população inicial (sqlite3)
│   ├── sqlite_populate.py        # popula usuários e predictions (sqlite3, idempotente)
│   ├── routes/                   # endpoints HTTP
│   │   ├── health.py             #   GET  /health
│   │   ├── auth.py               #   POST /auth/token        (rate limit 10/min)
│   │   ├── predict.py            #   POST /predict           (protegida)
│   │   ├── predictions.py        #   GET  /predictions[/{id}] (protegidas, ownership)
│   │   ├── docs.py               #   GET  /docs              (Swagger com SRI + CSP)
│   │   └── responses.py          #   respostas de erro documentadas no OpenAPI
│   ├── models/                   # contratos Pydantic e tabelas SQLModel
│   ├── security/                 # JWT, hash de senha, dependências, headers, rate limit
│   ├── application/              # casos de uso (fronteira entre rotas e domínio)
│   └── domain/                   # conceitos de negócio (enum das 5 intenções)
│
├── tests/                        # suíte pytest + TestClient (47 testes)
│
├── zap/
│   ├── scan_passivo_zap_TP3.md   # análise dos findings Medium/High do TP3
│   ├── zap_tp3_docs_*.html|json|md|log   # scan passivo do /docs (antes e depois)
│   ├── zap_tp3_api.html|json|md|log      # scan da API autenticada (final)
│   ├── openapi_tp3.json          # especificação usada no scan
│   └── tp2/                      # relatórios do TP2, preservados
│
├── others/
│   ├── planejamento_tp3.md       # modelo candidato, CountVectorizer e alvo do pentest
│   ├── hipoteses.md              # hipóteses sobre as intenções (TP1)
│   ├── dfd.png / dfd-and-cia.md  # DFD, trust boundaries e análise CIA (TP1)
│   └── generate_dfd.py
│
└── entregaveis/                  # PDFs entregues no Moodle
```

O fluxo da aplicação vai sempre na mesma direção:
`routes (HTTP) -> application (caso de uso) -> domain / security / crud`.

---

## Instalação

Requisito: **Python 3.12 ou superior**.

```bash
# 1. clonar e entrar no repositório
git clone https://github.com/Infnet-Performance-Tests/anderson_breno_francisco_tp2.git
cd anderson_breno_francisco_tp2

# 2. criar e ativar o ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. instalar as dependências
python -m pip install -r requirements.txt

# 4. configurar as variáveis de ambiente
cp .env.example .env             # troque JWT_SECRET_KEY por: openssl rand -hex 32
```

---

## Banco de dados

O `fastapi/database.db` já vem criado e populado. Para recriá-lo ou populá-lo:

```bash
cd fastapi
python sqlite_database.py --reset   # apaga e recria o schema + população inicial
python sqlite_database.py           # cria o schema e popula só se estiver vazio
python sqlite_populate.py           # (re)popula: insere o que faltar, sem duplicar
```

Tabelas: `users` (senha em hash PBKDF2-SHA256) e `predictions` (com `owner_id`). Os scripts
usam `sqlite3` puro; a API consulta o banco apenas via SQLModel.

| Usuário | Senha | Predictions de exemplo |
| --- | --- | --- |
| `alice` | `alice123` | 2 (`refund_request`, `billing_inquiry`) |
| `bob` | `bob123` | 2 (`technical_issue`, `cancellation_request`) |
| `admin` | `admin123` | 1 (`product_inquiry`) |

São credenciais acadêmicas, presentes apenas para demonstração e testes.

---

## Execução da API

De dentro do diretório `fastapi/`:

```bash
cd fastapi
uvicorn main:app --reload
```

- API: `http://127.0.0.1:8000`
- **Documentação interativa: `http://127.0.0.1:8000/docs`.** Use o botão **Authorize** com um
  dos usuários acima para testar as rotas protegidas.
- Especificação OpenAPI: `http://127.0.0.1:8000/openapi.json`

Com Docker: `docker compose up --build`.

### Endpoints

| Método | Rota | Autenticação | Descrição |
| --- | --- | --- | --- |
| `GET` | `/health` | Não | Verifica se a API está ativa. |
| `POST` | `/auth/token` | Não (rate limit) | Recebe `username`/`password` (form) e devolve um JWT válido por 30 min. |
| `POST` | `/predict` | **Bearer** | Classifica o texto e grava a prediction para o usuário autenticado. |
| `GET` | `/predictions` | **Bearer** | Lista apenas as predictions do usuário autenticado. |
| `GET` | `/predictions/{id}` | **Bearer** | Devolve a prediction se for do usuário; caso contrário, `404`. |
| `GET` | `/docs` | Não | Swagger UI. |

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/token \
  -d "username=alice&password=alice123" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -X POST http://127.0.0.1:8000/predict -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"text":"I was charged twice"}'
# {"id":6,"intent":"product_inquiry","confidence":1.0,"model_version":"stub-v0"}

curl http://127.0.0.1:8000/predictions/3 -H "Authorization: Bearer $TOKEN"
# {"detail":"Prediction not found"}   <- a prediction 3 é do bob
```

A rota `/predict` ainda devolve uma intenção fixa (`stub-v0`). O classificador entra no TP4,
sem mudar o contrato HTTP.

---

## Testes

```bash
pytest tests/ -v
```

São **47 testes**, todos usando o app real com `TestClient` e um banco SQLite temporário (o
`database.db` versionado não é alterado):

| Arquivo | Controle verificado |
| --- | --- |
| `test_autenticacao.py` | Credenciais válidas geram JWT do próprio usuário; senha errada e usuário inexistente recebem o mesmo `401` genérico; tokens forjados, expirados ou de usuário inexistente são recusados |
| `test_acesso_outro_usuario.py` | **BOLA**: um usuário não lê nem lista predictions de outro (`404`, com a mesma resposta de um ID inexistente) |
| `test_campo_extra.py` | **Validação de entrada**: campos extras (`extra="forbid"`), texto vazio ou longo demais, tipo errado, JSON malformado e IDs inválidos devolvem `422` |
| `test_rate_limit.py` | **Rate limiting**: a 11ª requisição em 1 minuto a `/auth/token` recebe `429`, mesmo com a senha certa; as outras rotas não são afetadas |
| `test_sem_token.py` | **Rota protegida**: `/predict`, `/predictions` e `/predictions/{id}` recusam requisição sem token, com token inválido ou com esquema diferente de Bearer |
| `test_headers_cors.py` | Headers HSTS, CSP, X-Frame-Options e X-Content-Type-Options; CORS só para origens da allowlist |
| `test_health_docs.py` | `/health`, `/docs` com CSP e SRI (regressão dos findings do ZAP) e OpenAPI documentando segurança e respostas |

Análise estática: `ruff check .`

### Integração contínua

O workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) roda **a cada push** (em
qualquer branch) e em pull requests: faz o checkout, configura o Python 3.12, instala o
`requirements.txt`, roda `ruff check .` e depois `pytest tests/ -v`. Se qualquer teste falhar,
o pytest sai com código diferente de zero e o workflow termina com erro. As execuções ficam
na aba **Actions** do repositório.

**Evidência de execução bem-sucedida:** run
[#40384632722](https://github.com/Infnet-Performance-Tests/anderson_breno_francisco_tp2/actions/runs/40384632722)
(push na branch `tp3`, 26/10/2026), com o job *Tests (pytest)* concluído em 56 s:
`ruff check .` → `All checks passed!` e `pytest tests/ -v` → `47 passed`.

---

## Notebook (EDA, regressão e formalização)

```bash
jupyter lab eda/eda_tp3.ipynb
```

O notebook já está executado, com todas as saídas salvas, e lê o CSV de `data/`:

- **1.1–1.8** — EDA completa (TP1/TP2): qualidade, limpeza, análises uni e multivariada,
  testes de hipótese (Mann-Whitney), outliers e conclusões.
- **2** — Regressão linear (TP3): alvo = quantidade de palavras da descrição; R², RMSE,
  Residual Plot, Q-Q Plot, limitações e por que ela não representa o problema.
- **3** — Formalização da classificação (TP3): X = `Ticket Description`, y = `Ticket Type`
  (5 classes balanceadas), justificativa de classificação vs. regressão e verificação de
  viabilidade.

> **Achado importante:** neste dataset sintético, o texto não carrega sinal sobre a intenção
> (CountVectorizer + Regressão Logística ≈ classificador aleatório, macro-F1 ≈ 0,19). As
> alternativas estão em [`others/planejamento_tp3.md`](others/planejamento_tp3.md).

---

## Segurança

### Controles implementados

| Controle | Onde |
| --- | --- |
| JWT HS256 com `sub`, `iat` e `exp` (30 min); só o algoritmo configurado é aceito | `security/jwt.py` |
| Usuários no banco com senha em hash PBKDF2-SHA256 (310 mil iterações) | `security/passwords.py`, `sqlite_populate.py` |
| Login sem enumeração de usuários (mesmo `401` e verificação de hash mesmo sem usuário) | `application/auth_facade.py` |
| Token só vale para usuário existente e ativo | `security/dependencies.py` |
| Ownership na própria consulta (anti-BOLA) | `crud.get_prediction_for_owner`, `routes/predictions.py` |
| `extra="forbid"` em todo body de entrada | `models/requests.py` |
| Rate limit de 10 req/min por IP no login (SlowAPI) | `routes/auth.py`, `security/rate_limit.py` |
| HSTS, CSP, X-Frame-Options, X-Content-Type-Options, COOP/CORP, `Cache-Control: no-store` | `security/headers.py` |
| CORS com allowlist explícita (`ALLOWED_ORIGINS`, sem `*`) | `main.py`, `config.py` |
| `/docs` com Swagger em versão fixa, SRI e CSP sem `unsafe-inline` | `routes/docs.py`, `security/headers.py` |

**Por que 10 requisições/minuto no login:** é uma tentativa a cada 6 segundos. Um usuário que
erra a senha não é afetado, mas um ataque de força bruta sobre 1 milhão de senhas levaria
cerca de 69 dias a partir de um mesmo IP.

### Alterações na API feitas no TP3

Para que os controles exigidos pudessem ser testados de ponta a ponta, a API foi alterada:

1. **Login passou a usar o banco.** Antes, `/auth/token` só aceitava o `admin` fixo em
   `config.py`, e os usuários do banco (TP2) não conseguiam autenticar. A senha em código foi
   removida.
2. **Rotas de ownership criadas:** `GET /predictions` e `GET /predictions/{id}`. No TP2 a
   consulta com ownership existia em `crud.py`, mas nenhuma rota a expunha, e os testes HTTP
   de BOLA eram pulados.
3. **`/predict` agora grava a prediction** com `owner_id` do usuário autenticado e devolve o
   `id` criado.
4. **Enum de intenções alinhado às 5 classes do dataset** (`domain/prediction.py`). O stub
   responde `product_inquiry`, e o seed do banco usa essas classes.
5. **Correções dos findings Medium do ZAP** em `/docs` (ver abaixo) e desligamento do
   `/redoc`.
6. **Testes reunidos em `tests/`** (antes divididos entre `tests/` e `fastapi/tests/`).

### Auditoria OWASP ZAP

A auditoria final está documentada em
**[`zap/scan_passivo_zap_TP3.md`](zap/scan_passivo_zap_TP3.md)**. Foram encontrados 2 findings
**Medium**, ambos em `/docs`: *CSP Header Not Set* e *Sub Resource Integrity Attribute
Missing*. Os dois foram corrigidos e validados por um novo scan. Resultado final: **0 High,
0 Medium e 0 Low**. Os relatórios exportados estão em `zap/`.

O DFD e a análise CIA do TP1 estão em [`others/dfd.png`](others/dfd.png) e
[`others/dfd-and-cia.md`](others/dfd-and-cia.md).

---

## Dataset

| Item | Valor |
| --- | --- |
| Nome | Customer Support Ticket Dataset |
| Publicador | `suraj520` (Kaggle) |
| URL | https://www.kaggle.com/datasets/suraj520/customer-support-ticket-dataset/data |
| Licença | CC0 — domínio público |
| Cópia local | `data/customer_support_tickets.csv`, sem alterações |
| Tamanho | 8.469 tickets × 17 colunas, um ticket por linha |

`Customer Name` e `Customer Email` são dados pessoais. Não aparecem em gráficos, logs,
respostas da API nem exemplos.

---

## Referências

- [Customer Support Ticket Dataset (Kaggle)](https://www.kaggle.com/datasets/suraj520/customer-support-ticket-dataset/data)
- [FastAPI — Security](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP API Security Top 10](https://owasp.org/API-Security/)
- [OWASP ZAP — Docker scans](https://www.zaproxy.org/docs/docker/)
- [scikit-learn — Working with text data](https://scikit-learn.org/stable/tutorial/text_analytics/working_with_text_data.html)
