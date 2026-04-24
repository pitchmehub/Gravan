# Stripe Connect — Gravan

Guia completo de configuração de Stripe Connect (Express) para a plataforma.
Funciona em modo **TESTE** primeiro; depois você troca apenas as chaves para LIVE.

---

## 📦 O que foi implementado

### Backend
| Arquivo | O que faz |
|---|---|
| `backend/db/migration_stripe_connect.sql` | Adiciona `stripe_account_id`, `stripe_charges_enabled`, etc + tabela `repasses` + view `v_saldo_retido` + RLS |
| `backend/routes/stripe_connect.py` | Endpoints `/api/connect/onboarding`, `/status`, `/dashboard-link`, `/repasses` |
| `backend/services/repasses.py` | Cria transfers, retém quando autor não conectado, libera ao completar onboarding, reverte em refund |
| `backend/routes/stripe_routes.py` (atualizado) | Webhook agora trata: `payment_intent.succeeded`, `account.updated`, `account.application.deauthorized`, `transfer.failed`, `payout.failed`, `charge.refunded` |

### Frontend
| Arquivo | O que faz |
|---|---|
| `frontend/src/pages/ConnectOnboarding.jsx` | Tela "Receber pagamentos via Stripe" com status + botão de cadastro |
| `frontend/src/App.jsx` | Rotas `/connect`, `/connect/sucesso`, `/connect/refresh` |

### Regras de negócio implementadas
- ✅ Taxa STARTER **20%** / PRO **15%** (sobre o NET após taxas Stripe)
- ✅ Taxas Stripe rateadas proporcionalmente entre autores (item 9)
- ✅ **Wallet interna**: cada venda credita o saldo dos autores na plataforma
- ✅ **Saque manual**: autor solicita quando quiser em `/saques` → vira Transfer Stripe na hora
- ✅ Saque exige conta Stripe Connect ativa (banner direciona pra `/connect`)
- ✅ Reversal automático em caso de refund (transfers existentes)
- ✅ Idempotência em todos os transfers (não duplica)
- ✅ Assinatura PRO R$ 29,90/mês via Stripe Billing (já existia, sem Connect)
- ✅ PayPal mantido como legado/opcional na coluna `saques.metodo`

---

## 🚀 Setup passo a passo (modo TESTE)

### 1. Habilitar Stripe Connect no painel
1. Entre em https://dashboard.stripe.com/test/settings/connect
2. Clique em **Enable Connect**
3. Em **Platform settings** → defina nome "Gravan", logo, suporte
4. Em **Settings → Connect → Payout schedule**: deixe **Monthly** (item 10)
5. Em **Settings → Connect → Branding**: cor `#BE123C`, logo

### 2. Rodar a migration no Supabase
1. Abra https://supabase.com/dashboard → seu projeto → **SQL Editor**
2. Cole o conteúdo de `backend/db/migration_stripe_connect.sql`
3. Clique **Run**. Deve responder "Success".

### 3. Variáveis de ambiente
No `backend/.env` do seu PC:
```env
# Já tinha:
STRIPE_SECRET_KEY=sk_test_xxxxx
FRONTEND_URL=http://localhost:5173

# Novo (vai gerar no passo 4):
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
```

No `frontend/.env`:
```env
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_xxxxx
VITE_API_URL=http://localhost:5000
```

### 4. Webhook local com Stripe CLI (você sem URL pública)
A Stripe CLI cria um túnel que recebe os eventos da Stripe e encaminha pro seu localhost.

**Instalar (Windows):**
```powershell
scoop install stripe
# OU baixar de https://github.com/stripe/stripe-cli/releases (executável .exe)
```

**Linux/Mac:**
```bash
brew install stripe/stripe-cli/stripe
```

**Logar e iniciar o forwarding** (deixa rodando em paralelo ao backend):
```bash
stripe login
stripe listen --forward-to localhost:5000/api/stripe/webhook
```

Saída esperada:
```
> Ready! Your webhook signing secret is whsec_xxxxxxxxxxxx
```
**Copie esse `whsec_xxx` pro `STRIPE_WEBHOOK_SECRET` no `.env` e reinicie o Flask.**

### 5. Testar fluxo completo

#### a) Criar uma conta de teste como autor
1. Faça login no Gravan como compositor
2. Vá em `/connect` → clique **Conectar minha conta Stripe**
3. Você é redirecionado pra Stripe. Use:
   - País: **Brasil**
   - Tipo: **Indivíduo**
   - CPF qualquer válido (ex: `247.001.660-00`)
   - Banco de teste: `000` agência, `0000000000-0` conta
   - Documento de identidade: clique em "Pular para teste"
4. Volta pra `/connect/sucesso` → status deve ficar **ATIVA**

#### b) Simular uma compra
1. Logue como **outro usuário** (comprador)
2. Compre uma obra qualquer
3. Use cartão de teste: `4242 4242 4242 4242` · qualquer validade futura · CVC `123`
4. Após confirmar, no terminal da Stripe CLI você verá:
   ```
   2026-04-22 → checkout.session.completed   [evt_xxx]
   2026-04-22 → payment_intent.succeeded      [evt_xxx]
   ```
5. Verifique no banco:
   ```sql
   select status, valor_cents, stripe_transfer_id
   from repasses
   where transacao_id = '<id_da_transacao>';
   ```
   Deve aparecer `enviado` com `stripe_transfer_id = tr_xxx`.

#### c) Testar retenção (autor sem Stripe)
1. Crie um terceiro usuário sem fazer onboarding em `/connect`
2. Marque como coautor de uma obra (ex: 30%)
3. Faça uma compra. O repasse desse coautor entra como **`retido`**.
4. Logue como ele, vá em `/connect`, complete o onboarding.
5. O webhook `account.updated` dispara `liberar_repasses_retidos` → status vai pra `enviado`.

#### d) Testar refund
```bash
stripe refunds create --charge ch_xxxxx
```
O webhook `charge.refunded` cria reversals automáticos.

---

## 🌐 Indo para PRODUÇÃO (LIVE)

Quando estiver pronto pra publicar:

### 1. Stripe Dashboard
- Toggle **View test data** → desliga
- Repita os passos 1 (habilitar Connect) e 4 (criar webhook endpoint) em modo LIVE
- Em **Webhooks** → **Add endpoint**:
  - URL: `https://SEU-BACKEND.onrender.com/api/stripe/webhook`
  - Events:
    - `checkout.session.completed`
    - `payment_intent.succeeded`
    - `payment_intent.payment_failed`
    - `checkout.session.expired`
    - `customer.subscription.updated`
    - `customer.subscription.deleted`
    - `invoice.payment_failed`
    - `account.updated`
    - `account.application.deauthorized`
    - `transfer.failed`
    - `payout.failed`
    - `charge.refunded`
  - Copie o **Signing secret** (`whsec_xxx`) pro Render env var

### 2. Variáveis no Render
```
STRIPE_SECRET_KEY=sk_live_xxxxx       ← chave LIVE
STRIPE_WEBHOOK_SECRET=whsec_xxxxx     ← do endpoint LIVE
FRONTEND_URL=https://gravan.com.br
FLASK_ENV=production
```

### 3. Variáveis no Vercel
```
VITE_STRIPE_PUBLISHABLE_KEY=pk_live_xxxxx
VITE_API_URL=https://seu-backend.onrender.com
```

### 4. Verificar conta Stripe da plataforma
- Em **Settings → Account details**, certifique-se que o CNPJ **64.342.514/0001-08** está ativo e validado
- Em **Settings → Bank accounts and scheduling**, confirme a conta bancária da Gravan pra payouts

### 5. Smoke test em produção
Mesma sequência do passo 5 acima, mas com cartão real (pode usar R$ 1,00 e estornar depois).

---

## 📊 Eventos de webhook tratados

| Evento | Ação |
|---|---|
| `checkout.session.completed` (mode=payment) | Confirma transação + gera contrato + dispara repasses |
| `checkout.session.completed` (mode=subscription) | Ativa PRO |
| `payment_intent.succeeded` | Backup pra disparar repasses |
| `checkout.session.expired` / `payment_intent.payment_failed` | Cancela transação |
| `customer.subscription.updated` | Sincroniza status PRO |
| `customer.subscription.deleted` | Volta usuário pra STARTER |
| `invoice.payment_failed` | Marca PRO como `past_due` |
| `account.updated` | Atualiza status Connect + libera retidos |
| `account.application.deauthorized` | Limpa stripe_account_id do perfil |
| `transfer.failed` | Marca repasse como `falhou` |
| `payout.failed` | Log de erro (Stripe notifica o autor por email) |
| `charge.refunded` | Reverte transfers + marca transação `reembolsada` |

---

## 🔧 Troubleshooting

### "No such account: acct_xxx"
A conta foi criada em modo TESTE mas você está usando chave LIVE (ou vice-versa). Cada modo tem suas próprias contas.

### "Insufficient funds"
A plataforma precisa ter saldo suficiente no Stripe pra fazer transfers. Em modo teste, a Stripe creditará automaticamente. Em produção, garanta que os pagamentos liquidaram (~7 dias após o charge).

### Repasses ficando como "retido" mesmo após onboarding
Verifique se `account.updated` está chegando: `stripe events resend evt_xxx` ou consulte `/api/connect/status` que sincroniza manualmente.

### Webhook retorna 400
Provavelmente `STRIPE_WEBHOOK_SECRET` está errado ou faltando. Confira no terminal do `stripe listen` qual é o secret atual (ele muda toda vez que você reinicia o `listen`).

---

## 📞 Referências
- [Stripe Connect Express docs](https://stripe.com/docs/connect/express-accounts)
- [Separate Charges and Transfers](https://stripe.com/docs/connect/separate-charges-and-transfers)
- [Stripe CLI](https://stripe.com/docs/stripe-cli)
- [Webhooks signature verification](https://stripe.com/docs/webhooks/signatures)
