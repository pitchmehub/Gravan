# Gravan

Marketplace for music rights/licensing built with React + Vite (frontend) and Flask (backend), backed by Supabase.

## Project Structure

- `frontend/` — React 18 + Vite SPA. Uses Supabase JS client and a custom API client (`src/lib/api.js`) for the Flask backend.
- `backend/` — Flask 3 API with CSRF, CORS, rate limiting, Supabase admin client, Stripe, PayPal, email, etc.
- `sql/` — SQL schema/migrations for Supabase.

## Replit Setup

Two workflows are configured:

1. **Frontend** — `cd frontend && npm run dev` — Vite dev server on port `5000`, host `0.0.0.0`, all hosts allowed (required for Replit's iframe proxy). HMR is disabled. Vite proxies `/api/*` to the backend.
2. **Backend** — `cd backend && python run.py` — Flask dev server bound to `127.0.0.1:8000`.

The frontend talks to the backend through the Vite proxy at the relative path `/api`, so `VITE_API_URL=/api` in `frontend/.env`.

## Environment

- `backend/.env` — Supabase service key, Flask secret, Stripe, SMTP, etc.
- `frontend/.env` — Supabase URL/anon key, `VITE_API_URL`.

## Deployment

Configured for Replit autoscale:

- Build: `cd frontend && npm install && npm run build`
- Run: gunicorn serves Flask on `127.0.0.1:8000`, Vite preview serves the built SPA on `0.0.0.0:5000` and proxies `/api` to gunicorn.

## Keep-alive (anti-sleep)

Three layers run together to keep the backend awake:

1. **Backend routes** (`backend/routes/keep_alive.py`) — `GET /api/ping` and `GET /api/keep-alive`. Both are CSRF- and rate-limit-exempt. Use `/api/keep-alive` from external uptime monitors (UptimeRobot, BetterStack, Cron-job.org).
2. **Internal heartbeat** (`backend/services/heartbeat.py`) — daemon thread started in `create_app()` that hits `http://127.0.0.1:8000/api/ping` every 240 s. Configurable via env vars `HEARTBEAT_ENABLED` (`1`/`0`), `HEARTBEAT_INTERVAL` (seconds), `HEARTBEAT_URL`.
3. **Frontend pinger** (`frontend/src/lib/keepAlive.js`) — fires from `main.jsx` and pings `/ping` every 4 minutes while the tab is visible (auto-pauses when hidden).

A standalone external pinger is also available at `scripts/external_pinger.py` for use in cron / GitHub Actions / a separate VM.

## AI features (free stack)

For MVP scale (~100 obras/month) the AI stack is fully free:

1. **Lyric transcription** — `faster-whisper` (model `base`, CPU `int8`) running in-process. Singleton model loaded lazily on first call. Service: `backend/services/ai_letra.py`. Endpoint: `POST /api/ai/transcrever` (sync, ~30s–2min per audio) and `POST /api/ai/obras/<id>/transcrever` (async, runs in background thread). Override model with env `WHISPER_MODEL` (default `base`).
2. **Cover art** — Pollinations.ai (no key, no signup). The URL itself returns the image. Service: `backend/services/ai_capa.py`. Endpoint: `POST /api/ai/obras/<id>/gerar-capa` (regenerate). Auto-triggered after `POST /api/obras/`. Genre → visual style mapping in `GENERO_STYLE` dict.

Database additions (see `sql/02_ai_capa_letra.sql`): `obras.cover_url` (text) and `obras.letra_status` (text, default `pendente`, check constraint).

Frontend:
- `NovaObra.jsx` — "✨ Transcrever com IA" button next to the lyric textarea (calls `/ai/transcrever` synchronously with the selected audio).
- `MinhasObras.jsx` — shows `cover_url` as the play-button thumbnail with overlay; "✨ Regerar capa" button when an obra is selected.

## Player

Global audio player lives in `frontend/src/contexts/PlayerContext.jsx` and `frontend/src/components/GlobalPlayer.jsx`. Audio URLs are signed by the backend (`/api/obras/<id>/preview-url`) for private bucket access.

Key behaviors:
- `playObra(listOrItem, idx, { shuffle })` — central shuffle (Fisher-Yates) keeps the clicked obra first when `shuffle: true`.
- `shuffle` (default `true`) and `repeat` (`'off' | 'all' | 'one'`) state, exposed via `toggleShuffle` / `cycleRepeat`. `nextTrack`/`onEnded` use refs to read latest values.
- Mobile: `.gp-mini` floats above the bottom nav (`bottom = calc(96px + env(safe-area-inset-bottom))`). Collapsing from the expanded view (chevron-down or swipe-down) returns to mini on mobile via `colapsarParaMini()`.
- Expanded view header: 3-dot button opens `FichaTecnica` modal (with Licenciar action). Liking uses `<BotaoCurtir />`.

Shared components:
- `frontend/src/components/FichaTecnica.jsx` — reusable ficha técnica modal (used by Descoberta, GlobalPlayer, PerfilPublico).
- `frontend/src/components/ArtistaHero.jsx` — exports `ObrasLista` with two modes:
  - Player mode (`onPlay` + `onShowFicha`): 1st click plays, 2nd click on the active row opens ficha técnica; right-side button becomes ▶/⏸.
  - Legacy (`onSelect` + `ctaLabel`): row/button click invokes `onSelect`.
- `Descoberta.jsx` and `PerfilPublico.jsx` both wire `ObrasLista` to the global player so artist pages behave identically to Descoberta.

## Notificações em tempo real + Web Push (PWA)

Três peças trabalham juntas para entregar notificações instantâneas:

1. **Supabase Realtime** — a tabela `notificacoes` está na publicação `supabase_realtime` (com `REPLICA IDENTITY FULL`). O hook `frontend/src/hooks/useRealtimeNotifications.js` assina `postgres_changes` filtrando por `perfil_id=eq.<uid>`. O `NotificationBell` e a página `/notificacoes` consomem esse hook para recarregar instantaneamente; o polling antigo virou fallback de 2 min. Migração: `backend/db/migration_realtime_notificacoes.sql`.

2. **Web Push (VAPID)** — backend usa `pywebpush`. Tabela: `push_subscriptions` (1 entrada por endpoint, com RLS por `perfil_id`). Migração: `backend/db/migration_push_subscriptions.sql`. Service: `backend/services/push_service.py` (`send_push(perfil_id, title, body, url, tag, data)` — degrada silenciosamente quando VAPID não está configurado). Rotas: `GET/POST /api/push/{public-key,subscribe,unsubscribe,test}` (`backend/routes/push.py`, csrf-exempt). O helper `notify()` em `backend/services/notificacoes.py` dispara push automaticamente para toda inserção. Frontend: `frontend/src/lib/push.js` (subscribe/unsubscribe/status/teste) + service worker `frontend/public/sw.js` (handlers `push` e `notificationclick`, versão `gravan-v5-design1-push-20260426`). UI de ativação fica na página `/notificacoes`.

   Secrets necessários: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` (mailto:contato@gravan.app).

3. **Histórico paginado `/notificacoes`** — `frontend/src/pages/Notificacoes.jsx`, rota em `App.jsx`, link "Notificações" na sidebar (todos os perfis) e "Ver todas" no rodapé do sino. Backend: `GET /api/notificacoes/?offset=&limit=&nao_lidas=` devolve `{items,total,offset,limit,has_more}` (compat: sem esses params, devolve apenas a lista, formato antigo). Filtros client-side por tipo + chip "Só não-lidas" + botão "Marcar todas como lidas".
