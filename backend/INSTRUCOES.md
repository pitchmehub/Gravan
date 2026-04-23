# Pitch.me — Atualização do módulo de DOSSIÊ (v2)

Esta versão **muda o fluxo** do dossiê: a geração agora é feita
exclusivamente pelo administrador, na nova aba **Obras** do painel
admin. O botão "Gerar dossiê" do cadastro de obra foi removido em
todos os perfis.

---

## 📦 Arquivos para sobrescrever

```
pitchme-dossie-fix/
├── INSTRUCOES.md                                ← este arquivo
├── backend/
│   ├── routes/dossie.py                         ← SUBSTITUIR
│   ├── services/dossie.py                       ← SUBSTITUIR
│   └── db/migration_dossie.sql                  ← SUBSTITUIR e rodar
└── frontend/
    └── src/pages/
        ├── Admin.jsx                            ← SUBSTITUIR  (nova aba "Obras")
        ├── Descoberta.jsx                       ← SUBSTITUIR  (1 clique = play, 2 cliques = ficha)
        ├── NovaObra.jsx                         ← SUBSTITUIR  (sem botão de dossiê)
        └── Dossies.jsx                          ← SUBSTITUIR  (busca + ID único)
```

---

## 🚨 COMO SABER SE OS ARQUIVOS FORAM REALMENTE TROCADOS

Depois de copiar tudo e **reiniciar backend + frontend**, abre `/admin` →
aba **Obras**. Você deve ver no topo do painel uma **tarja amarela**
escrita **"✓ Painel Obras carregado — versão atualizada (abril/2026)"**.

- ✅ Tarja amarela apareceu → o `Admin.jsx` foi trocado certo
- ❌ Não apareceu → o `Admin.jsx` antigo continua no lugar. Confere o
  caminho exato: `pitchme/frontend/src/pages/Admin.jsx`

E se a aba **Obras** nem aparece na barra do admin, é porque o
`Admin.jsx` definitivamente não foi trocado.

### Backend não esquece
Flask **não recarrega sozinho** — depois de trocar `routes/dossie.py`
você PRECISA parar (Ctrl+C) e iniciar de novo o backend, senão o
endpoint `/api/dossies/admin/obras` continua o antigo (sem o
`audio_path` que o player precisa).

---

## ✨ O que mudou nesta versão

### 1. Botão "Gerar dossiê" removido do cadastro de obra
Em **todos os perfis** (compositor, intérprete, editora). O fluxo
antigo mostrava um passo extra após cadastrar uma obra perguntando
"deseja gerar o dossiê?". Esse passo sumiu — após cadastrar, vai
direto para "Minhas Obras".

> Arquivo: `frontend/src/pages/NovaObra.jsx`

### 2. Nova aba "Obras" no painel administrador
Adicionada entre "Receita" e "Gêneros". Lista **todas** as obras
cadastradas na plataforma com:

- **Botão ▶ tocar prévia** (usa o mesmo GlobalPlayer da home/catálogo)
- **Nome da obra** + **gênero** + selo "✓ dossiê pronto" (se já gerado)
- **ID único** da obra com botão de copiar
- Titular (nome + email) + data de cadastro + valor da licença
- Barra de busca (por nome, ID, titular ou email)
- Botão **GERAR DOSSIÊ** (vermelho, ou contorno se já existe → vira
  "REGENERAR DOSSIÊ")
- Botão **BAIXAR DOSSIÊ** (verde, desabilitado se ainda não foi gerado)

> Arquivo: `frontend/src/pages/Admin.jsx`

### 3. Novo endpoint backend
```
GET /api/dossies/admin/obras   (admin only)
```
Retorna a lista completa de obras já com a info do dossiê
correspondente (id, hash, data) embutida. Uma única chamada — sem
N+1.

> Arquivo: `backend/routes/dossie.py` (endpoint `admin_listar_obras`)

### 4. Comportamento dos botões
- **GERAR DOSSIÊ**: chama `POST /api/dossies/obras/<obra_id>` — a
  plataforma reúne todos os dados do contrato assinado (áudio,
  letra, metadados, contrato em PDF, hash SHA-256) num arquivo
  ZIP e o salva no Storage privado do Supabase.
- Se já existir um dossiê para aquela obra, o botão muda para
  "**REGENERAR DOSSIÊ**" e pede confirmação antes de sobrescrever.
- **BAIXAR DOSSIÊ**: chama `GET /api/dossies/<dossie_id>/download`
  — entrega o ZIP ao navegador para download direto.
- Feedback inline (verde/vermelho) abaixo de cada linha após cada
  ação.

---

## 🛠️ Como instalar

### Backend
```
cp pitchme-dossie-fix/backend/routes/dossie.py     pitchme/backend/routes/dossie.py
cp pitchme-dossie-fix/backend/services/dossie.py   pitchme/backend/services/dossie.py
```
Não precisa mexer em `app.py` — o blueprint já está registrado em
`/api/dossies`. Reinicie o backend.

### Banco (Supabase)
Rode no SQL Editor o arquivo (idempotente — pode rodar de novo):
```
pitchme-dossie-fix/backend/db/migration_dossie.sql
```

### Frontend
```
cp pitchme-dossie-fix/frontend/src/pages/Admin.jsx     pitchme/frontend/src/pages/Admin.jsx
cp pitchme-dossie-fix/frontend/src/pages/NovaObra.jsx  pitchme/frontend/src/pages/NovaObra.jsx
cp pitchme-dossie-fix/frontend/src/pages/Dossies.jsx   pitchme/frontend/src/pages/Dossies.jsx
```
Sem mudanças no `App.jsx`, `SideMenu.jsx` ou `lib/api.js`.

```bash
cd pitchme/frontend
npm run dev    # ou yarn dev
```

---

## ✅ Roteiro de teste

1. Logar como **compositor**, criar uma obra nova → ao salvar, vai
   direto para "Minhas Obras". (Nenhuma tela perguntando sobre dossiê.)
2. Logar como **administrador**, abrir o painel → clicar na aba
   **Obras**.
3. A obra recém-criada aparece na lista, com o ID único em destaque
   e o botão **GERAR DOSSIÊ** vermelho.
4. Clicar em **GERAR DOSSIÊ** → após alguns segundos, aparece o
   selo "✓ dossiê pronto" e o botão muda para **REGENERAR DOSSIÊ**.
5. Clicar em **BAIXAR DOSSIÊ** → o navegador baixa o ZIP
   `dossie-<nome-da-obra>.zip`.
6. Abrir o ZIP → deve conter áudio, letra, `metadata.json`,
   contrato PDF, `hash.txt`.
7. Buscar pela barra de pesquisa: pelo nome, pelo ID único e pelo
   email do titular — todos devem filtrar.
