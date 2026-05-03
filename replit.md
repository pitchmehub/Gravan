# Gravan — Marketplace de Obras Musicais

### Auditoria de Segurança Financeira — Saques & Wallets (mai/2026)
Auditoria completa de todos os fluxos financeiros. **8 vulnerabilidades corrigidas:**

1. **CRÍTICA — `executar_saque_stripe` legada bloqueada** (`services/repasses.py`):
   Função tinha fluxo completamente inseguro (sem OTP, sem janela, debit não-atômico na
   ordem errada). Agora lança `RuntimeError` imediatamente se chamada, com código original
   preservado como comentário histórico.

2. **CRÍTICA — `_reconstitui_wallet` com duplo fallback** (`services/saque_security.py`):
   Antes silenciava falha de re-crédito. Agora tenta RPC `creditar_wallet` → se falhar,
   faz UPDATE direto → se ambos falharem, lança `RuntimeError` com log "CRÍTICO IRREVERSÍVEL"
   para forçar reconciliação manual imediata.

3. **CRÍTICA — `confirmar_otp` com UPDATE atômico condicional** (`services/saque_security.py`):
   Race condition: dois requests simultâneos podiam ambos passar o check de `pendente_otp`.
   Fix: `.eq("status", "pendente_otp")` no UPDATE e verificação de `upd.data` — se vazio,
   outro request já confirmou.

4. **ALTA — `reenviar-otp` sem rate limit** (`routes/saques.py`):
   Rota não tinha `@limiter.limit()`. Agora limitada a 5/hour.

5. **ALTA — `liberar_pendentes` fallback inseguro** (`services/saque_security.py`):
   Quando RPC `saques_a_liberar` falha, o fallback fazia SELECT + UPDATE separados sem lock.
   Fix: UPDATE condicional com `.eq("status", "aguardando_liberacao")` — só processa saques
   que este worker realmente travou (sem processamento duplo).

6. **ALTA — Admin `aprovar_saque` reescrito sem RPC perigosa** (`routes/admin.py`):
   Antes chamava RPC `aprovar_saque` cegamente (comportamento desconhecido). Agora:
   - Aceita apenas `pago` ou `rejeitado` (removido `processando` que não fazia sentido).
   - `pago` só permitido para saques em `processando` (cron já debitou e enviou Transfer).
   - `rejeitado` de saque em `processando`: reconstitui wallet ANTES de atualizar status.
   - UPDATE condicional com WHERE status=<status_atual> previne race com cron.

7. **MÉDIA — `VALOR_MIN_CENTS` elevado de 1 para 1.000** (`services/saque_security.py`):
   Mínimo era R$ 0,01. Agora R$ 10,00 (evita spam de OTP e Transfers para valores irrisórios).

8. **BAIXA — Frontend corrigido** (`frontend/src/pages/Saques.jsx`):
   Todos os textos "24h" e badge "Em janela de 24h" corrigidos para "12h" (consistente
   com `JANELA_LIBERACAO_HORAS = 12`).

**Arquivos modificados:** `backend/services/saque_security.py`, `backend/services/repasses.py`,
`backend/routes/saques.py`, `backend/routes/admin.py`, `frontend/src/pages/Saques.jsx`.

**SQL pendente (usuário deve rodar no Supabase):** `backend/db/migration_debitar_wallet_atomico.sql`
(cria RPCs atômicas `debitar_wallet` / `creditar_wallet` e constraint `CHECK (saldo_cents >= 0)`).



### Recibo Fiscal Mensal + Bulk Upload da Editora (abr/2026)
- **Recibo fiscal mensal** para compositores e editoras: novo serviço
  `backend/services/recibo_fiscal.py` agrega `pagamentos_compositores`
  por mês (mesma fonte canônica usada pelo dashboard) e gera tanto JSON
  quanto PDF (ReportLab, mesmo padrão de `contrato_pdf.py`). Os
  totais incluem bruto creditado no mês, fees informativos (25%
  plataforma + 5% exploração comercial) e o acumulado YTD. O documento
  é informativo — a apuração tributária e a emissão de NFS-e ficam
  com o beneficiário.
- **Rotas**: `backend/routes/financeiro.py` registrado em `app.py`:
  `GET /api/financeiro/recibos-mensais` lista meses com renda > 0;
  `GET /api/financeiro/recibo-mensal?ano&mes` retorna JSON;
  `GET /api/financeiro/recibo-mensal/pdf?ano&mes` faz download do PDF.
- **Frontend**: nova página `frontend/src/pages/Financeiro.jsx` em
  `/financeiro` (compositor, publisher, administrador) com lista de
  meses + visualização do recibo + botão "Baixar PDF". Link adicionado
  no `SideMenu` (compositor e publisher) e no `PublisherDashboard`.
- **Bulk upload de obras pela editora**: novo serviço
  `backend/services/bulk_obras.py` que aceita um `.zip` contendo um
  CSV (UTF-8 com BOM) + arquivos `.mp3`. Para cada linha do CSV,
  reusa `services.obras.ObraService.criar_obra` em nome do titular
  (que precisa ser agregado da editora — match por CPF/email),
  vincula `publisher_id` e dispara `services.contrato_publisher.
  gerar_contrato_edicao` (autor↔editora). Limites: 200 MB / 200 obras
  por upload. Erros são reportados linha-a-linha e não derrubam o
  processamento das demais.
- **Rotas**: adicionadas em `backend/routes/publishers.py`:
  `GET /api/publishers/bulk-upload/template` baixa CSV exemplo;
  `POST /api/publishers/bulk-upload` recebe ZIP (multipart `arquivo`)
  e devolve `{criadas[], erros[], total_csv}`.
- **Frontend**: nova página `frontend/src/pages/BulkUploadObras.jsx`
  em `/editora/bulk-upload` (publisher, administrador) com instruções,
  download do template, drag&drop do .zip e tabela de resultados.
  Link em `SideMenu` (publisher) e botão no `PublisherDashboard`.
- **Testes**: `backend/tests/test_bulk_obras_parsers.py` (16 testes)
  cobre os parsers puros (preço, coautores, CPF, resolução de
  titular) e validações de ZIP. Os 10 testes anti-regressão de
  contrato continuam verdes.

### Escrow Real — Assinatura Manual + Bug do Split da Editora (abr/2026)
- **Modelo de assinatura mudou para MANUAL REAL**: autores, coautores e editora-mãe
  agora são inseridos em `contract_signers` com `signed=False, signed_at=None`. Cada
  parte humana DEVE acessar `/contratos/licenciamento/<id>` e clicar "Concordo" para
  assinar. Apenas o COMPRADOR (intérprete) e a Gravan (editora_detentora bilateral)
  continuam auto-assinando — o primeiro porque o pagamento é o aceite, a segunda
  porque é a operadora institucional.
- **Trava extra no `_escrow_guard`** (defesa em profundidade): além de checar
  `contracts.status='concluído'`, valida que cada signer humano (autor, coautor,
  editora_detentora não-Gravan) tem `signed=True E ip_hash NOT NULL`. O `ip_hash`
  é setado apenas via rota HTTP `/aceitar` (`hash_ip(remote_addr)`), garantindo
  que houve clique humano via interface. Se algum humano não assinou via HTTP,
  o crédito é bloqueado e registrado como `escrow_blocked_human_check` em
  `contract_events` mesmo que o status diga "concluído".
- **Notificações ao criar contrato**: bilateral e trilateral agora notificam
  todos os autores e a editora-mãe sobre a pendência de assinatura, com link
  direto para `/contratos/licenciamento/<id>`.
- **Bug do split da editora corrigido (silent fail)**: a query
  `transacoes.select("..., obras(...)")` em `creditar_wallets_por_transacao`
  estava ambígua porque a tabela `transacoes` tem duas FKs para `obras`
  (`transacoes_obra_fk` e `transacoes_obra_id_fkey`). PostgREST devolvia
  `PGRST201`, a função abortava antes de chegar no crédito da editora,
  e os autores eram pagos por uma execução anterior que rodou antes da
  ambiguidade aparecer. **Fix**: embed explícito
  `obras!transacoes_obra_id_fkey(...)`.
- **Idempotência granular**: `creditar_wallets_por_transacao` agora skipa
  apenas perfis_id já pagos (não bail-out na primeira ocorrência), permitindo
  retry da editora quando autores foram pagos antes. Falhas em pagamento de
  qualquer perfil agora são registradas como `credito_falhou` em
  `contract_events` (era `logger.warning` silencioso antes).
- **Backfill aplicado** na transação `3e889470-29e0-4ceb-8326-72756b1f8ed6`
  (content_hash `bb5df127...`): editora `32657744` recebeu 28799 cents (10%
  do net após taxas Stripe), wallet atualizada de 419061 → 447860.

### Escrow — Correção de Violação + E-mail com PDF (abr/2026)
- **Bug corrigido**: o INSERT do signer Gravan usava fallback frágil baseado em string de
  erro (`"signers_role_check" in str(e)`). Se a string não aparecia exatamente assim,
  a Gravan ficava ausente da tabela → `todos_assinaram` retornava `True` com apenas
  [Autor, Comprador] → wallets creditadas antes do autor assinar.
- **Correção camada 1 (`gerar_contrato_licenciamento`)**: novo helper `_inserir_gravan_signer`
  tenta cada role de `_GRAVAN_ROLES_FALLBACK = ["editora_detentora", "editora_agregadora"]`
  sem depender da mensagem de erro. Idempotente (verifica existência antes de inserir).
  Loga `gravan_signer_error` em `contract_events` se todos os roles falharem.
- **Correção camada 2 (`aceitar_contrato`)**: guarda de escrow antes de `todos_assinaram`:
  (a) verifica se Gravan está em `contract_signers`; se não estiver, chama
  `_inserir_gravan_signer` na hora; (b) após o check, confirma explicitamente que Gravan
  está `signed=True` — se não estiver, bloqueia a liberação e loga `ESCROW BLOQUEADO`.
- **E-mail com PDF**: quando `todos_assinaram=True`, `aceitar_contrato` envia e-mail
  a todas as partes humanas (autores, coautores, intérprete/comprador) com o PDF do
  contrato assinado em anexo. Usa `services.email_service.send_email(attachments=...)` +
  `render_licenciamento_concluido_email` (novo template). Falhas são silenciosas
  (wrapped em try/except) para não bloquear a resposta HTTP de assinatura.
- **`send_email`** agora aceita `attachments: list[dict]` (data, filename, maintype, subtype).

### Contratos — Prazo, Rescisão e Exclusividade (abr/2026)
- Bilateral (CLÁUSULA 3) e trilateral / intermediação (CLÁUSULA 5) agora preveem:
  validade de 5 anos, rescisão por comunicação formal via e-mail com 30 dias de
  antecedência, e — quando a licença for de exclusividade — 5 anos de
  exclusividade. As cláusulas estão em `backend/services/contrato_licenciamento.py`
  (`TEMPLATE_LICENCIAMENTO`, `TEMPLATE_TRILATERAL`).
- Cláusula 8 do bilateral foi suavizada para "IRRETRATABILIDADE DA EXPLORAÇÃO",
  ressalvando o direito de rescisão da Cláusula 3.
- Quando uma exclusividade é vendida, `services.ofertas.aplicar_exclusividade_em_obra`
  marca `is_exclusive=true` (catálogo automaticamente bloqueia novos
  licenciamentos) e dispara, via `services.email_service.render_rescisao_exclusividade_email`,
  comunicação formal de rescisão por e-mail ao compositor, coautores e à
  editora envolvida (agregada — `perfis.publisher_id` — ou terceira —
  `obras.editora_terceira_email`), apontando como motivo a venda de
  exclusividade. Idempotente (não reenvia em retry de webhook).

### Assinatura PRO — Dunning automático (abr/2026)
- Renovação mensal recorrente no Stripe (Subscriptions).
- Em falha de cobrança (`invoice.payment_failed`), o perfil entra em
  `status_assinatura='past_due'` e recebe carimbo `past_due_desde` (timestamptz).
  Se a cobrança subsequente for bem sucedida, o carimbo é zerado.
- Após `DUNNING_GRACE_DAYS=7` dias em past_due, a rotina
  `services.subscription.expirar_assinaturas_em_atraso()` cancela a Subscription
  no Stripe; o webhook `customer.subscription.deleted` rebaixa o perfil para
  STARTER (handler já existente). Idempotente.
- Agendamento: `backend/watchdog.py` chama a rotina a cada
  `WATCHDOG_DUNNING_INTERVAL` segundos (default 3600), em subprocesso isolado,
  só quando o backend está saudável. Migração obrigatória:
  `backend/db/migration_assinatura.sql` (coluna `past_due_desde`).

## Visão Geral
Plataforma premium que conecta compositores e compradores de obras musicais com pagamentos via Stripe (PayPal removido em abr/2026), autenticação via Supabase, e transcrição de áudio com faster-whisper.

### Saques (Stripe Connect Brasil — atualizado abr/2026)
- A Stripe Brasil **exige** `source_transaction=ch_xxx` em toda Transfer
  Connect. Por isso, cada saque agora consome 1+ registros da tabela
  `pagamentos_compositores` em FIFO e cria **uma Transfer por charge**,
  cada uma vinculada à charge de origem.
- Migração obrigatória antes de usar: `backend/db/migration_saques_source_transaction.sql`
  (adiciona `saque_id`, `stripe_charge_id`, `liberado_em` em
  `pagamentos_compositores` + 2 índices). É idempotente.
- Implementação: `backend/services/saque_security.py::_processar_um_saque`.
  Em caso de erro Stripe no meio, todos os Transfers já criados são
  revertidos automaticamente (`Transfer.create_reversal`).
- O último pagamento pode ser parcialmente sacado (split): o registro
  original é encolhido (continua pendente) e um filho com `status='pago'`
  é criado pra rastrear o que foi pro saque.
- Rate-limit Stripe: idempotency_key por par saque/pagamento
  (`saque_{id}_pag_{pag_id}`).

### Modelo Comercial (atualizado abr/2026)
- **Planos de compositor:** apenas duas categorias — **Free (STARTER)** e **PRO**.
  O sistema antigo de "níveis" (prata / ouro / diamante) foi removido.
- **Taxa da plataforma sobre cada licenciamento:**
  - Titular Free → 20% Gravan, 80% para os autores
  - Titular PRO  → 15% Gravan, 85% para os autores
- **Editora vinculada (publisher):** quando o titular da obra está agregado a uma
  editora cadastrada na Gravan (`perfis.publisher_id` preenchido), a editora
  recebe automaticamente **10% do valor da venda** em cada licenciamento. O
  saldo remanescente, depois da taxa Gravan e dos 10% da editora, é distribuído
  entre os coautores conforme o split declarado. Implementado em
  `backend/services/finance.py::calcular_split` e
  `backend/services/repasses.py` (cobre tanto o crédito em wallet quanto os
  Transfers via Stripe Connect). A cláusula correspondente é injetada no
  contrato trilateral agregado em `backend/services/contrato_licenciamento.py`.
- **Royalties autorais (ECAD) — execução pública (atualizado abr/2026):**
  todos os contratos (bilateral e trilateral) preveem o seguinte rateio dos
  rendimentos do ECAD:
  - **85%** para os autores/coautores
  - **10%** para o intérprete
  - **5%** para a EDITORA GRAVAN
  A antiga cláusula 5.3 (royalties de fonograma) foi removida dos contratos.
- **Histórico de licenciamentos da editora:** endpoint
  `GET /api/publishers/historico-licenciamentos` lista todas as transações em
  que a editora logada recebeu sua comissão de 10%, com obra, titular agregado,
  comprador e valor. Renderizado no `PublisherDashboard.jsx`.
- **Fluxo de ofertas/contrapropostas (atualizado abr/2026):**
  - Ao criar uma oferta, o sistema notifica **compositor titular**, **editoras
    envolvidas** (publisher_id do titular + editora_terceira_id da obra) **e o
    próprio intérprete** (confirmação de envio). Implementado em
    `backend/services/ofertas.py::notificar_compositor_nova_oferta`.
  - Quando o intérprete responde a uma contraproposta do compositor, o backend
    notifica compositor + editoras (`notificar_resposta_contraproposta`). Se
    aceita, o `expires_at` é movido para 72h (janela de pagamento) e a resposta
    inclui `checkout_redirect=/comprar/<obra>?oferta_id=<id>`. O frontend
    (`Ofertas.jsx`) navega automaticamente para o checkout com o valor
    negociado.

## Arquitetura

### Backend (`backend/`)
- **Flask** (Python 3.11) rodando na porta **8000** via `python -m gunicorn`
- Logo da marca em `backend/assets/gravan-logo.png` (usada nos PDFs premium)
- Dossiê de Licença (cortesia ao comprador): `backend/services/dossie_licenca.py` →
  ZIP com letra em PDF (logo + tipografia premium), MP3 da composição (bucket `obras-audio`)
  e cópia do contrato. Rotas: `GET /api/contratos/licenciamento/<id>/dossie-licenca` (apenas
  o `buyer_id`) e `GET /api/contratos/licenciamento/by-transacao/<id>` (lookup pós-pagamento).
- Workflow: `cd backend && python -m gunicorn --bind=0.0.0.0:8000 --workers 2 --reuse-port 'app:create_app()'`
- Entrada: `backend/app.py` → `create_app()`
- Autenticação: Supabase Auth (JWT verificado no middleware `backend/middleware/auth.py`)
- Banco de dados: Supabase (PostgreSQL)
- Pagamentos: Stripe (PayPal removido — abr/2026)
- Rate limiting: Flask-Limiter (Redis ou memória)
- Segurança: Flask-WTF CSRF, CORS configurado, headers de segurança

### Frontend (`frontend/`)
- **React + Vite** rodando na porta **5000**
- Workflow: `cd frontend && npm run dev`
- Proxy `/api/*` → `http://localhost:8000` (configurado no vite.config.js)
- Autenticação: `@supabase/supabase-js` via `VITE_SUPABASE_URL` e `VITE_SUPABASE_ANON_KEY`

## Variáveis de Ambiente Necessárias

### Secrets (configurados no Replit)
- `SUPABASE_URL` — URL do projeto Supabase
- `SUPABASE_SERVICE_KEY` — Chave de serviço do Supabase (backend)
- `SUPABASE_ANON_KEY` — Chave anônima do Supabase (backend)
- `VITE_SUPABASE_URL` — Mesmo valor de SUPABASE_URL (exposto ao frontend via Vite)
- `VITE_SUPABASE_ANON_KEY` — Mesmo valor de SUPABASE_ANON_KEY (exposto ao frontend via Vite)
- `STRIPE_SECRET_KEY` — Chave secreta do Stripe
- `STRIPE_WEBHOOK_SECRET` — Secret do webhook Stripe
- `STRIPE_CONNECT_WEBHOOK_SECRET` — Secret do webhook Stripe Connect

### Env Vars (configuradas no Replit userenv.shared)
- `FLASK_SECRET_KEY` — Chave secreta Flask para sessões
- `PII_ENCRYPTION_KEY` — Chave de criptografia de dados pessoais
- `FLASK_ENV` — `development` ou `production`
- `ALLOWED_ORIGINS` — Origens permitidas pelo CORS
- `FRONTEND_URL` — URL base do frontend
- `SAQUE_CRON_SECRET` — Secret para o cron de saques
- `VITE_API_URL` — `/api`
- `VITE_API_BASE_URL` — `/api`

## Portas
- `5000` → Frontend (webview, porta externa 80)
- `8000` → Backend (console, porta externa 8000)

## Rotas Principais do Backend
Todos os blueprints registrados com prefixo `/api/*`:
- `/api/obras` — Obras musicais
- `/api/perfis` — Perfis de usuários
- `/api/catalogo` — Catálogo público
- `/api/transacoes` — Transações
- `/api/stripe` — Webhooks e pagamentos Stripe
- `/api/admin` — Painel administrativo
- `/api/analytics` — Métricas
- `/api/assinatura` — Assinaturas
- `/api/favoritos` — Favoritos
- `/api/ai` — Transcrição (Whisper) e geração de capas (Pollinations.ai)
- `/api/financeiro` — Recibo fiscal mensal (JSON e PDF) p/ compositor e editora
- `/api/publishers/bulk-upload` — Upload em massa de obras pela editora (ZIP)
- `/api/health` — Health check
