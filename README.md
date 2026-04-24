# 🎵 Pitch.me — Marketplace de Composições Musicais

Marketplace premium para compositores venderem obras musicais. **Design 1** (minimalista, branco + preto + red REC).

**Stack:**
- **Frontend:** React 18 + Vite
- **Backend:** Python 3.11 + Flask + Gunicorn
- **Banco de dados:** Supabase (PostgreSQL + RLS + Auth)  
- **Pagamentos:** Stripe + PayPal
- **PWA:** Service Worker com network-first cache 

---

## 📂 Estrutura do projeto

```
pitchme/
├── frontend/          # App React (vai para Vercel)
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── vite.config.js
│   ├── vercel.json    # Config de deploy Vercel
│   └── .env.example
├── backend/           # API Flask (vai para Render/Railway)
│   ├── routes/
│   ├── services/
│   ├── utils/
│   ├── middleware/
│   ├── db/
│   ├── app.py
│   ├── server.py
│   ├── wsgi.py
│   ├── requirements.txt
│   ├── Procfile       # Config Render/Railway/Heroku
│   ├── render.yaml    # Config Render 1-click deploy
│   └── .env.example
├── README.md          # Este arquivo
├── DEPLOY_VERCEL.md   # Guia completo de deploy
└── LICENSE
```

---

## 🚀 Rodando localmente

### Pré-requisitos
- Node.js 18+ e Yarn
- Python 3.11+
- Conta no [Supabase](https://supabase.com) (grátis) — para DB e Auth
- `libmagic` (sistema): `brew install libmagic` (Mac) / `apt install libmagic1` (Linux)

### 1. Clone e configure o banco de dados

```bash
git clone https://github.com/seu-usuario/pitchme.git
cd pitchme
```

No Supabase:
1. Crie um novo projeto em https://app.supabase.com
2. Pegue `Project URL`, `anon key` e `service_role key` em Settings → API
3. Execute o SQL de criação de tabelas (ver `/backend/db/schema.sql` se incluído)

### 2. Backend (API Flask)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Preencha com suas credenciais Supabase/Stripe/PayPal
gunicorn wsgi:app --bind 0.0.0.0:8001
```

API sobe em `http://localhost:8001`. Teste: `curl http://localhost:8001/api/health`.

### 3. Frontend (Vite)

```bash
cd frontend
yarn install
cp .env.example .env             # Preencha com URL do backend local e chaves Supabase
yarn dev
```

App sobe em `http://localhost:3000`.

---

## 🌐 Deploy em produção

👉 **Siga o guia completo em [`DEPLOY_VERCEL.md`](./DEPLOY_VERCEL.md)**

Resumo:
- **Frontend → Vercel** (grátis, 1 clique)
- **Backend → Render** ou **Railway** (Flask não roda no Vercel)
- **DB + Auth → Supabase** (grátis até 50k usuários)

---

## 🧪 Credenciais de teste

Um usuário de teste já cadastrado:
- Email: `teste.design@pitchme.local`
- Senha: `Teste@2026Design`
- Role: compositor

---

## 🎨 Design System

- **Cores:** `#FFFFFF` / `#09090B` / `#E11D48` (Red REC)
- **Fontes:** Space Grotesk (headings) + IBM Plex Sans (body)
- **Cantos:** 100% retos (Swiss/Design 1)
- **Tokens:** `frontend/src/styles/global.css` (variáveis CSS)

---

## 📜 Licença

Proprietário — todos os direitos reservados © 2025 Pitch.me.
