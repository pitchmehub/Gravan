# Gravan — Marketplace de Obras Musicais

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
- `/api/health` — Health check
