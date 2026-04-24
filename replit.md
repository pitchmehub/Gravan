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
