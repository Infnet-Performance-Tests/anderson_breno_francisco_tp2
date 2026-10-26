# Auditoria final de segurança com OWASP ZAP — TP3

## Resumo

| Item | Valor |
| --- | --- |
| Ferramenta | OWASP ZAP 2.17.0 (`ghcr.io/zaproxy/zaproxy:stable`, via Docker) |
| Data | 26/10/2026 |
| Alvo | API FastAPI rodando localmente (`uvicorn main:app --host 0.0.0.0 --port 8000`), acessada pelo container como `http://host.docker.internal:8000` |
| Banco usado no scan | cópia de `fastapi/database.db` (variável `DATABASE_PATH`), para que as predictions criadas pelo ZAP não entrassem no banco versionado |
| Findings Medium/High encontrados | **2 Medium**, ambos em `/docs` |
| Findings Medium/High após a correção | **0** (e também 0 Low) |

### Scans executados

| # | Script ZAP | Ponto de partida | Objetivo | Relatórios |
| --- | --- | --- | --- | --- |
| 1 | `zap-baseline.py` (scan **passivo** + spider) | `/docs` | Auditar a documentação interativa, que é HTML e carrega JavaScript | antes: [`zap_tp3_docs_antes.html`](zap_tp3_docs_antes.html) · depois: [`zap_tp3_docs_depois.html`](zap_tp3_docs_depois.html), [`.md`](zap_tp3_docs_depois.md), [`.json`](zap_tp3_docs_depois.json), [`.log`](zap_tp3_docs_depois.log) |
| 2 | `zap-api-scan.py` (regras passivas + ativas) **autenticado** | `/openapi.json` | Auditar todas as rotas da API, inclusive as protegidas | [`zap_tp3_api.html`](zap_tp3_api.html), [`.md`](zap_tp3_api.md), [`.json`](zap_tp3_api.json), [`.log`](zap_tp3_api.log) |

No scan 2 o token JWT de um usuário de teste (`alice`) foi injetado em todas as requisições com
o *replacer* do ZAP, para que as rotas protegidas (`/predict`, `/predictions`,
`/predictions/{id}`) respondessem `200` e fossem realmente analisadas, e não apenas recusadas
com `401`. A especificação OpenAPI importada está em [`openapi_tp3.json`](openapi_tp3.json).

Comandos (a partir da raiz do repositório, com a API no ar):

```bash
# 1. scan passivo da documentação interativa
docker run --rm -v "$PWD/zap:/zap/wrk:rw" -t ghcr.io/zaproxy/zaproxy:stable \
  zap-baseline.py -t http://host.docker.internal:8000/docs -I -j \
  -r zap_tp3_docs_depois.html -J zap_tp3_docs_depois.json -w zap_tp3_docs_depois.md

# 2. scan da API a partir do OpenAPI, autenticado
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/token \
  -d "username=alice&password=alice123" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
docker run --rm -v "$PWD/zap:/zap/wrk:rw" -t ghcr.io/zaproxy/zaproxy:stable \
  zap-api-scan.py -t http://host.docker.internal:8000/openapi.json -f openapi -I \
  -r zap_tp3_api.html -J zap_tp3_api.json -w zap_tp3_api.md \
  -z "-config replacer.full_list(0).description=auth \
      -config replacer.full_list(0).enabled=true \
      -config replacer.full_list(0).matchtype=REQ_HEADER \
      -config replacer.full_list(0).matchstr=Authorization \
      -config replacer.full_list(0).regex=false \
      -config replacer.full_list(0).replacement=Bearer\ $TOKEN"
```

### Por que o TP2 não pegou esses findings

O scan do TP2 (preservado em [`tp2/`](tp2/)) partiu só do OpenAPI. Como `/docs` não faz parte
da especificação, o ZAP nunca abriu a página HTML do Swagger. No TP3 o `/docs` virou
entregável ("documentação interativa funcional"), então ele entrou no escopo da auditoria. O
scan 2, que cobre as mesmas rotas do TP2 e as novas rotas de ownership, não encontrou nenhum
finding Medium ou High já na primeira execução.

---

## Resultado consolidado

| Scan | High | Medium | Low | Informational |
| --- | ---: | ---: | ---: | ---: |
| 1. `/docs` — antes da correção | 0 | **2** | 4 | 2 |
| 1. `/docs` — depois da correção | 0 | **0** | 0 | 2 |
| 2. API autenticada (final) | 0 | **0** | 0 | 3 |

---

## Finding 1 — Content Security Policy (CSP) Header Not Set

| Campo | Valor |
| --- | --- |
| Plugin ZAP | 10038 |
| Severidade | **Medium** |
| Confiança | High |
| CWE / WASC | CWE-693 (Protection Mechanism Failure) / WASC-15 |
| URL afetada | `GET http://host.docker.internal:8000/docs` |
| O que foi detectado | A resposta HTML do `/docs` não tinha o header `Content-Security-Policy`. |

**Por que é um risco.** O `/docs` é a única resposta HTML da API e é onde o usuário digita
usuário e senha (botão *Authorize*) e onde o token JWT fica guardado na memória da página.
Sem CSP, qualquer script que chegue à página — por um XSS, por uma dependência comprometida
ou por uma extensão maliciosa — roda sem restrição e pode ler o token e enviá-lo a outro
domínio. A CSP é a segunda linha de defesa que limita de onde vêm scripts e para onde a
página pode mandar dados. A origem do problema estava no próprio código: no TP2 o middleware
pulava a CSP do `/docs` de propósito, porque o Swagger UI padrão do FastAPI usa um `<script>`
inline que uma CSP estrita bloquearia.

**Correção.**

1. O script de inicialização do Swagger deixou de ser inline e passou a ser servido pela
   própria API em `/docs/swagger-init.js` — `fastapi/routes/docs.py`.
2. O `/docs` passou a receber uma CSP própria, sem `'unsafe-inline'` nem `'unsafe-eval'`, que
   libera apenas os dois arquivos exatos do Swagger no CDN, scripts da própria origem, imagens
   `data:` e `fetch` para a própria API — `fastapi/security/headers.py`, constante `DOCS_CSP`
   (comentário `ZAP TP3 — finding 10038`):

   ```text
   default-src 'none';
   script-src 'self' https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.32.15/swagger-ui-bundle.js;
   style-src 'self' https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.32.15/swagger-ui.css;
   img-src 'self' data:; connect-src 'self';
   base-uri 'none'; form-action 'none'; frame-ancestors 'none'
   ```

3. De carona, o `/docs` também passou a enviar `Cross-Origin-Opener-Policy`,
   `Cross-Origin-Resource-Policy` e `Cross-Origin-Embedder-Policy: require-corp`, o que eliminou
   os três findings **Low** do plugin 90004 (Spectre / isolamento cross-origin).

**Evidência de que o problema não permanece.**

- Scan 1 depois da correção ([`zap_tp3_docs_depois.log`](zap_tp3_docs_depois.log)):
  `PASS: Content Security Policy (CSP) Header Not Set [10038]` e
  `FAIL-NEW: 0  WARN-NEW: 2` (as duas restantes são Informational).
- Header devolvido pela API corrigida:

  ```text
  $ curl -s -D - -o /dev/null http://127.0.0.1:8000/docs
  content-security-policy: default-src 'none'; script-src 'self' https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.32.15/swagger-ui-bundle.js; style-src 'self' https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.32.15/swagger-ui.css; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'
  cross-origin-embedder-policy: require-corp
  cross-origin-opener-policy: same-origin
  cross-origin-resource-policy: same-origin
  ```

- Funcionamento: o `/docs` foi aberto no Chrome com a CSP ativa, a página renderizou, o login
  pelo botão *Authorize* funcionou e o console ficou sem nenhuma violação de CSP.
- Teste de regressão: `tests/test_health_docs.py::test_docs_tem_csp_restritiva`.

---

## Finding 2 — Sub Resource Integrity Attribute Missing

| Campo | Valor |
| --- | --- |
| Plugin ZAP | 90003 |
| Severidade | **Medium** |
| Confiança | High |
| CWE / WASC | CWE-345 (Insufficient Verification of Data Authenticity) / WASC-15 |
| URL afetada | `GET http://host.docker.internal:8000/docs` (2 instâncias) |
| O que foi detectado | `<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js">` e `<link href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">` sem atributo `integrity`. |

**Por que é um risco.** A página carregava JavaScript de um servidor de terceiros (CDN) sem
verificar o conteúdo, e ainda por uma versão flutuante (`@5`, que vira qualquer `5.x` nova).
Se o CDN, o pacote npm ou o caminho de rede fossem comprometidos, o script alterado rodaria
**na origem da API**, com acesso ao token JWT e às credenciais digitadas no Swagger — um ataque
de cadeia de suprimentos sem nenhuma falha no nosso código. O atributo `integrity` (SRI) faz o
navegador recusar qualquer arquivo cujo hash não seja o esperado.

**Correção.** `fastapi/routes/docs.py` (comentário `ZAP TP3 — finding 90003`):

1. Versão do Swagger UI fixada em `5.32.15` (`SWAGGER_UI_VERSION`), em vez de `@5`.
2. Hash SHA-384 de cada arquivo declarado no atributo `integrity`, com
   `crossorigin="anonymous"` (necessário para o navegador validar o SRI de outra origem):

   ```html
   <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.32.15/swagger-ui.css"
         integrity="sha384-fgyWYkUAamzuI8mJFu/xpRP0JWCJRwkwUwsYDoOYVHUJ8NQE5cENn8ib3ppwFFSX" crossorigin="anonymous">
   <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.32.15/swagger-ui-bundle.js"
           integrity="sha384-m7zaGj7MPzU+G4lz2eyy73GxK9bbRDr9bB2CSdj8wodg2wu/Wnt6wsoLP3JD+RS9" crossorigin="anonymous"></script>
   ```

   Os hashes foram gerados com `openssl dgst -sha384 -binary <arquivo> | openssl base64 -A`
   sobre os arquivos publicados no CDN. Para atualizar o Swagger, troca-se a versão e
   recalculam-se os dois hashes.

3. O `/docs` padrão do FastAPI foi desligado (`docs_url=None` em `fastapi/main.py`) e o
   `/redoc` também (`redoc_url=None`), porque carregava outro script de CDN sem SRI e só
   duplicava a documentação.

**Evidência de que o problema não permanece.**

- Scan 1 depois da correção ([`zap_tp3_docs_depois.log`](zap_tp3_docs_depois.log)):
  `PASS: Sub Resource Integrity Attribute Missing [90003]`. O finding Low
  *Cross-Domain JavaScript Source File Inclusion* (10017) também deixou de aparecer.
- O HTML servido em `/docs` contém os atributos `integrity` e `crossorigin` mostrados acima, e
  nenhum `<script>` inline.
- Testes de regressão: `tests/test_health_docs.py::test_docs_carrega_scripts_externos_com_sri`
  e `::test_redoc_foi_desligado`.

---

## Findings restantes (Informational, sem correção necessária)

| Finding | Onde | Por que não é corrigido |
| --- | --- | --- |
| A Client Error response code was returned by the server (100000) | várias rotas | É o comportamento esperado: o ZAP envia payloads inválidos e a API responde `401`, `404` ou `422`. Não há stack trace nem detalhe interno no corpo. |
| Authentication Request Identified (10111) | `/auth/token` | Apenas identifica a rota de login. |
| Non-Storable Content (10049) | todas | Consequência direta do `Cache-Control: no-store`, aplicado de propósito para que tokens e predictions nunca fiquem em cache. |
| Modern Web Application (10109) | `/docs` | Apenas informa que a página é uma SPA (o Swagger UI). |

## Conclusão

A auditoria final não tem nenhum finding High, Medium ou Low em aberto. Os dois findings
Medium encontrados foram corrigidos no código, com comentários nos pontos da correção,
validados por um novo scan do ZAP e protegidos por testes de regressão que rodam no CI.
