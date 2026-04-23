# 🚀 Pitch.me — Guia de Deploy em Produção

**Stack:** Vercel (frontend React/Vite) + Render (backend Flask) + Supabase (Postgres/Auth/Storage)

---

## ⚠️ ANTES DE COMEÇAR — ROTAÇÃO DE CREDENCIAIS

Os arquivos `.env` que vinham no projeto **continham segredos reais já expostos**.
Eles foram removidos. Você **precisa rotacionar** (gerar novas) as seguintes chaves antes de subir nada para produção:

| Serviço      | O que rotacionar                                | Onde                                                                                  |
| ------------ | ----------------------------------------------- | ------------------------------------------------------------------------------------- |
| **Supabase** | `service_role key` (NUNCA pode vazar de novo)   | Dashboard → Project Settings → API → "Reset service_role"                             |
| **Stripe**   | `Secret Key` e o `Webhook Signing Secret`       | Dashboard → Developers → API keys → Roll secret key + Webhooks → recriar endpoint     |
| **Flask**    | `FLASK_SECRET_KEY`                              | Gere localmente: `openssl rand -hex 32`                                               |
| **PayPal**   | `Client Secret` (se a app já existe)            | Developer Dashboard → My Apps → Show secret → recriar                                 |

> ❗ **Não pule esta etapa.** A `service_role` do Supabase dá acesso TOTAL ao banco contornando RLS.

---

## 1. Banco — Supabase

1. Crie um projeto em <https://app.supabase.com>.
2. Vá em **SQL Editor → New query** e rode na ordem:
   - `backend/db/schema.sql` (estrutura)
   - `backend/db/rls_security.sql` (políticas de Row-Level Security)
   - Demais arquivos de migration em `backend/db/migrations/` (em ordem cronológica)
3. Em **Storage → New bucket**, crie:
   - `obras-audio` (private)
   - `avatars` (public)
4. Anote em **Settings → API**:
   - `Project URL` → `SUPABASE_URL`
   - `anon public` → `SUPABASE_ANON_KEY` (frontend)
   - `service_role` → `SUPABASE_SERVICE_KEY` (backend — secreto)

---

## 2. Backend — Render

1. Faça push do projeto para o GitHub.
2. Em <https://dashboard.render.com> → **New → Blueprint** e aponte para o repositório.
   O arquivo `backend/render.yaml` é detectado automaticamente.
3. Em **Environment**, preencha (não use os valores antigos!):

   ```
   SUPABASE_URL              = https://SEU-PROJETO.supabase.co
   SUPABASE_SERVICE_KEY      = (a NOVA service_role)
   SUPABASE_ANON_KEY         = (a anon key — opcional, só para /security-check)
   FLASK_SECRET_KEY          = (auto-gerado pelo Render — ou cole o seu)
   FLASK_ENV                 = production
   STRIPE_SECRET_KEY         = sk_live_... (ou sk_test_ para testes)
   STRIPE_WEBHOOK_SECRET     = whsec_...
   PAYPAL_CLIENT_ID          = ...
   PAYPAL_CLIENT_SECRET      = ...
   PAYPAL_MODE               = live   (ou sandbox)
   FRONTEND_URL              = https://seu-app.vercel.app
   ALLOWED_ORIGINS           = https://seu-app.vercel.app
   ```
4. Após o deploy, anote a URL pública (ex.: `https://pitchme-api.onrender.com`).
5. Configure os webhooks:
   - **Stripe** → Developers → Webhooks → endpoint `https://pitchme-api.onrender.com/api/stripe/webhook` (eventos: `checkout.session.completed`, `invoice.paid`, `customer.subscription.deleted`).
   - **PayPal** → Webhooks → endpoint para `/api/paypal/webhook` (se vc adicionar; hoje o fluxo PayPal usa apenas execute-payment).

> 🟢 **Health check:** `GET /api/health` deve devolver `{"ok": true}`.

---

## 3. Frontend — Vercel

1. Em <https://vercel.com> → **Add New → Project**, escolha o repositório.
2. Em **Root Directory** selecione `frontend/`.
3. Framework: Vite. Build command: `yarn build`. Output: `dist`.
4. **Environment Variables** (Settings → Environment Variables):

   ```
   VITE_SUPABASE_URL       = https://SEU-PROJETO.supabase.co
   VITE_SUPABASE_ANON_KEY  = (anon key — pode ser pública, mas controlada por RLS)
   VITE_API_URL            = https://pitchme-api.onrender.com/api
   ```
5. Faça o deploy.

---

## 4. Verificação pós-deploy (Pentest rápido)

Rode estes comandos contra produção:

```bash
# 1. Health check (deve responder 200)
curl https://pitchme-api.onrender.com/api/health

# 2. Endpoint protegido sem JWT (deve responder 401)
curl -i https://pitchme-api.onrender.com/api/perfis/me

# 3. Endpoint inexistente (deve responder 404, não vazar stack trace)
curl -i https://pitchme-api.onrender.com/api/inexistente

# 4. CORS — origem não autorizada (deve NÃO retornar Access-Control-Allow-Origin)
curl -i -H "Origin: https://malicioso.com" https://pitchme-api.onrender.com/api/health

# 5. Rate limit — disparar várias chamadas para /api/contato (deve dar 429 após 3)
for i in 1 2 3 4; do curl -X POST -H "Content-Type: application/json" \
  -d '{"nome":"x","email":"a@b.c","mensagem":"teste 1234567890"}' \
  https://pitchme-api.onrender.com/api/contato/; done

# 6. Rota antiga de download de source (deve dar 404 — foi removida)
curl -i https://pitchme-api.onrender.com/api/download-projeto

# 7. RLS — anon key tentando ler perfis (deve dar 0 linhas)
#    Faça login como administrador e abra GET /api/security-check no painel admin
```

---

## 5. Correções de segurança aplicadas neste passo

| #  | Severidade | Falha                                                                | Correção                                                                                          |
| -- | ---------- | -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| 1  | 🔴 Crítica | `.env` commitados com `service_role`, Stripe e Flask secret reais   | Arquivos removidos; chaves precisam ser rotacionadas (ver topo)                                    |
| 2  | 🔴 Crítica | `app.py`: `SESSION_COOKIE_SECURE=request.is_secure if request else True` acessava `request` fora de contexto e era avaliado uma única vez | Substituído por flag fixa baseada em `FLASK_ENV=production` + validação de `FLASK_SECRET_KEY` ≥ 32 chars |
| 3  | 🔴 Crítica | `paypal_routes.execute_payment` chamava `calcular_split` com kwargs errados (crash em produção) e tratava `SplitResult` como list | Reescrita: usa assinatura correta `(valor, coautorias, plano_titular)`, itera sobre `.payouts`, tem fallback para wallets se RPC ausente, idempotente em retentativa |
| 4  | 🔴 Crítica | `/api/download-projeto` servia ZIP do source code SEM autenticação   | Rota removida; blueprint vazio mantido                                                             |
| 5  | 🟠 Alta    | PayPal aceitava compra de quem não tinha cadastro completo nem aceitou contrato | `create_payment` agora valida `cadastro_completo` + `concordo_contrato` igual ao Stripe          |
| 6  | 🟠 Alta    | `landing.py` salvava configuração em `config/landing.json` (disco efêmero do Render — perdia dados a cada deploy) | Migrado para tabela `landing_content` no Supabase (chave `__landing_full__`)                       |
| 7  | 🟠 Alta    | `contato.py` gravava IP em texto puro (LGPD)                         | Agora usa `hash_ip()` (mesma função já usada em analytics)                                         |
| 8  | 🟠 Alta    | `paypal_routes.get_payment_status` permitia consultar pagamento de outro usuário | Agora valida que o `comprador_id` da transação é o usuário autenticado                            |
| 9  | 🟠 Alta    | Configs de deploy duplicadas no root e em `backend/`                | Mantidos apenas em `backend/` (Procfile + render.yaml) e `frontend/` (vercel.json)                |
| 10 | 🟡 Média   | `paypal_routes.execute_payment` com `request.json.get(...)` crashava em request sem body JSON | Helper `_safe_json()` retorna `{}` quando body ausente/inválido                                   |

---

## 6. Hardening já existente no projeto (não foi alterado)

- ✅ Webhook Stripe valida HMAC (`stripe.Webhook.construct_event`)
- ✅ Sanitização de inputs (`utils/sanitizer.py` com bleach + path-traversal block)
- ✅ Encryption de PII — CPF e RG armazenados via Fernet (`utils/crypto.py`)
- ✅ Validação de magic-bytes para uploads MP3 (`utils/audio_validator.py`)
- ✅ Rate-limiting (Flask-Limiter) por rota crítica
- ✅ Audit logging (`utils/audit.py`) em compras, saques e logins
- ✅ RLS no Supabase (`db/rls_security.sql`)
- ✅ Permissions-Policy + CSP + HSTS no Flask
- ✅ Frontend usa apenas `VITE_*` (anon key) — service_role nunca chega ao browser

---

## 7. Próximos passos recomendados (não bloqueantes)

1. **Migrar PayPal v1 → v2 (Checkout Server SDK).** A lib `paypalrestsdk` está deprecada desde 2022.
2. **Adicionar webhook do PayPal** (`PAYMENT.SALE.COMPLETED`) para o caso de o usuário fechar o navegador antes do `execute-payment`.
3. **Substituir o salt fixo** em `utils/crypto.py` por uma variável de ambiente `PII_ENCRYPTION_SALT`.
4. **Configurar Sentry/Logtail** para receber os logs do Render.
5. **Backup automático do Supabase** (Plan Pro já inclui).

---

Pronto. Após rotacionar as chaves e seguir os passos 1–4, o app está em condições de ir para produção.
