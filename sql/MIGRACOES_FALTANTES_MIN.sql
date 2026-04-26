ALTER TYPE public.oferta_status ADD VALUE IF NOT EXISTS 'contra_proposta';
ALTER TYPE public.oferta_status ADD VALUE IF NOT EXISTS 'cancelada';
ALTER TYPE public.oferta_status ADD VALUE IF NOT EXISTS 'paga';
ALTER TYPE public.oferta_status ADD VALUE IF NOT EXISTS 'expirada';
BEGIN;
ALTER TABLE public.ofertas
  ADD COLUMN IF NOT EXISTS tipo TEXT NOT NULL DEFAULT 'padrao';
ALTER TABLE public.ofertas
  ADD COLUMN IF NOT EXISTS contraproposta_de_id UUID
    REFERENCES public.ofertas(id) ON DELETE SET NULL;
ALTER TABLE public.ofertas
  ADD COLUMN IF NOT EXISTS aguardando_resposta_de TEXT NOT NULL DEFAULT 'compositor';
ALTER TABLE public.ofertas
  ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ
    DEFAULT (now() + INTERVAL '48 hours');
ALTER TABLE public.ofertas
  ADD COLUMN IF NOT EXISTS mensagem TEXT;
ALTER TABLE public.ofertas
  ADD COLUMN IF NOT EXISTS responded_at TIMESTAMPTZ;
UPDATE public.ofertas
   SET expires_at = created_at + INTERVAL '48 hours'
 WHERE expires_at IS NULL;
ALTER TABLE public.ofertas DROP CONSTRAINT IF EXISTS ofertas_tipo_check;
ALTER TABLE public.ofertas
  ADD CONSTRAINT ofertas_tipo_check
  CHECK (tipo IN ('padrao','exclusividade'));
ALTER TABLE public.ofertas DROP CONSTRAINT IF EXISTS ofertas_aguardando_check;
ALTER TABLE public.ofertas
  ADD CONSTRAINT ofertas_aguardando_check
  CHECK (aguardando_resposta_de IN ('compositor','interprete'));
ALTER TABLE public.obras
  ADD COLUMN IF NOT EXISTS is_exclusive BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE public.obras
  ADD COLUMN IF NOT EXISTS exclusive_until TIMESTAMPTZ;
ALTER TABLE public.obras
  ADD COLUMN IF NOT EXISTS exclusive_to_id UUID
    REFERENCES public.perfis(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_ofertas_obra_status
  ON public.ofertas (obra_id, status);
CREATE INDEX IF NOT EXISTS idx_ofertas_interprete_status
  ON public.ofertas (interprete_id, status);
CREATE INDEX IF NOT EXISTS idx_ofertas_pendentes_expirando
  ON public.ofertas (expires_at)
  WHERE status = 'pendente';
CREATE INDEX IF NOT EXISTS idx_ofertas_contraproposta_pai
  ON public.ofertas (contraproposta_de_id)
  WHERE contraproposta_de_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_obras_exclusivas
  ON public.obras (is_exclusive)
  WHERE is_exclusive = true;
CREATE INDEX IF NOT EXISTS idx_obras_exclusive_to
  ON public.obras (exclusive_to_id)
  WHERE exclusive_to_id IS NOT NULL;
COMMIT;
  ALTER TABLE public.perfis
    ALTER COLUMN role DROP DEFAULT;
  ALTER TABLE public.perfis
    ALTER COLUMN role DROP NOT NULL;
  DO $$
  BEGIN
    IF NOT EXISTS (
      SELECT 1 FROM pg_enum e
      JOIN pg_type t ON t.oid = e.enumtypid
      WHERE t.typname = 'user_role' AND e.enumlabel = 'publisher'
    ) THEN
      ALTER TYPE public.user_role ADD VALUE IF NOT EXISTS 'publisher';
    END IF;
  END $$;
  CREATE OR REPLACE FUNCTION public.handle_new_user()
  RETURNS trigger
  LANGUAGE plpgsql
  SECURITY DEFINER SET search_path = public
  AS $$
  BEGIN
    INSERT INTO public.perfis (id, email, nome, role)
    VALUES (
      NEW.id,
      NEW.email,
      COALESCE(
        NEW.raw_user_meta_data->>'full_name',
        NEW.raw_user_meta_data->>'name',
        split_part(NEW.email, '@', 1)
      ),
      NULL   -- role sempre NULL: o usuário escolhe em EscolherTipoPerfil
    )
    ON CONFLICT (id) DO NOTHING;

    -- Cria wallet zerada
    INSERT INTO public.wallets (perfil_id, saldo_cents)
    VALUES (NEW.id, 0)
    ON CONFLICT (perfil_id) DO NOTHING;

    RETURN NEW;
  END;
  $$;
  DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
  CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();
alter table public.perfis
  add column if not exists capa_url text;
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'avatares', 'avatares', true,
  2 * 1024 * 1024,
  array['image/jpeg','image/png','image/webp']
)
on conflict (id) do update
  set public             = excluded.public,
      file_size_limit    = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'capas', 'capas', true,
  5 * 1024 * 1024,
  array['image/jpeg','image/png','image/webp']
)
on conflict (id) do update
  set public             = excluded.public,
      file_size_limit    = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;
drop policy if exists "avatares insert auth"   on storage.objects;
drop policy if exists "avatares select public" on storage.objects;
drop policy if exists "avatares update owner"  on storage.objects;
drop policy if exists "avatares delete owner"  on storage.objects;
create policy "avatares insert auth"
on storage.objects for insert to authenticated
with check (
  bucket_id = 'avatares'
  and (storage.foldername(name))[1] = auth.uid()::text
);
create policy "avatares select public"
on storage.objects for select to public
using (bucket_id = 'avatares');
create policy "avatares update owner"
on storage.objects for update to authenticated
using (
  bucket_id = 'avatares'
  and (storage.foldername(name))[1] = auth.uid()::text
)
with check (
  bucket_id = 'avatares'
  and (storage.foldername(name))[1] = auth.uid()::text
);
create policy "avatares delete owner"
on storage.objects for delete to authenticated
using (
  bucket_id = 'avatares'
  and (storage.foldername(name))[1] = auth.uid()::text
);
drop policy if exists "capas insert auth"   on storage.objects;
drop policy if exists "capas select public" on storage.objects;
drop policy if exists "capas update owner"  on storage.objects;
drop policy if exists "capas delete owner"  on storage.objects;
create policy "capas insert auth"
on storage.objects for insert to authenticated
with check (
  bucket_id = 'capas'
  and (storage.foldername(name))[1] = auth.uid()::text
);
create policy "capas select public"
on storage.objects for select to public
using (bucket_id = 'capas');
create policy "capas update owner"
on storage.objects for update to authenticated
using (
  bucket_id = 'capas'
  and (storage.foldername(name))[1] = auth.uid()::text
)
with check (
  bucket_id = 'capas'
  and (storage.foldername(name))[1] = auth.uid()::text
);
create policy "capas delete owner"
on storage.objects for delete to authenticated
using (
  bucket_id = 'capas'
  and (storage.foldername(name))[1] = auth.uid()::text
);
alter table public.saques add column if not exists otp_hash          text;
alter table public.saques add column if not exists otp_expires_at    timestamptz;
alter table public.saques add column if not exists otp_attempts      int  not null default 0;
alter table public.saques add column if not exists confirmado_em     timestamptz;
alter table public.saques add column if not exists liberar_em        timestamptz;
alter table public.saques add column if not exists cancel_token_hash text;
alter table public.saques add column if not exists cancelado_em      timestamptz;
alter table public.saques add column if not exists cancelado_motivo  text;
alter table public.saques add column if not exists ip_hash           text;
alter table public.saques add column if not exists user_agent        text;
create index if not exists idx_saques_liberar_em on public.saques(liberar_em)
  where status = 'aguardando_liberacao';
create index if not exists idx_saques_perfil_status on public.saques(perfil_id, status);
create index if not exists idx_saques_cancel_token on public.saques(cancel_token_hash)
  where cancel_token_hash is not null;
create or replace function public.saques_a_liberar(p_limit int default 50)
returns setof public.saques
language sql
security definer
as $$
  update public.saques
     set status = 'processando'
   where id in (
     select id from public.saques
      where status = 'aguardando_liberacao'
        and liberar_em <= now()
      order by liberar_em
      limit p_limit
      for update skip locked
   )
  returning *;
$$;
create or replace function public.saques_expirar_otps()
returns int
language sql
security definer
as $$
  with x as (
    update public.saques
       set status = 'expirado'
     where status = 'pendente_otp'
       and otp_expires_at < now()
    returning 1
  )
  select count(*)::int from x;
$$;
create or replace view public.saques_pendentes_admin as
select
  id, perfil_id, valor_cents, status,
  created_at, confirmado_em, liberar_em, cancelado_em,
  cancelado_motivo
from public.saques
where status in ('pendente_otp','aguardando_liberacao','processando');
grant select on public.saques_pendentes_admin to authenticated;
alter table public.obras
  add column if not exists obra_editada_terceiros  boolean       not null default false,
  add column if not exists editora_terceira_nome     text,
  add column if not exists editora_terceira_email    text,
  add column if not exists editora_terceira_telefone text,
  add column if not exists editora_terceira_id       uuid references public.perfis(id) on delete set null;
create index if not exists idx_obras_editora_terceira
  on public.obras (editora_terceira_id)
  where editora_terceira_id is not null;
create index if not exists idx_obras_editora_terceira_email
  on public.obras (lower(editora_terceira_email))
  where editora_terceira_email is not null;
create table if not exists public.ofertas_licenciamento (
  id                            uuid primary key default gen_random_uuid(),
  obra_id                       uuid not null references public.obras(id)   on delete restrict,
  comprador_id                  uuid not null references public.perfis(id)  on delete restrict,
  valor_cents                   integer not null check (valor_cents >= 100),
  editora_terceira_nome         text not null,
  editora_terceira_email        text not null,
  editora_terceira_telefone     text,
  editora_terceira_id           uuid references public.perfis(id) on delete set null,
  registration_token            text not null unique,
  stripe_checkout_session_id    text,
  stripe_payment_intent_id      text,
  status                        text not null default 'aguardando_editora',
  deadline_at                   timestamptz not null,
  reminder_48h_sent_at          timestamptz,
  reminder_24h_sent_at          timestamptz,
  pago_em                       timestamptz,
  editora_cadastrada_em         timestamptz,
  contrato_id                   uuid references public.contracts(id) on delete set null,
  concluida_em                  timestamptz,
  expirada_em                   timestamptz,
  reembolsada_em                timestamptz,
  cancelada_em                  timestamptz,
  created_at                    timestamptz not null default now(),
  updated_at                    timestamptz not null default now(),
  constraint ofertas_status_check check (status in (
    'aguardando_pagamento',
    'aguardando_editora',
    'editora_cadastrada',
    'em_assinatura',
    'concluida',
    'expirada',
    'reembolsada',
    'cancelada'
  ))
);
create index if not exists idx_ofertas_obra        on public.ofertas_licenciamento (obra_id);
create index if not exists idx_ofertas_comprador   on public.ofertas_licenciamento (comprador_id);
create index if not exists idx_ofertas_editora     on public.ofertas_licenciamento (editora_terceira_id);
create index if not exists idx_ofertas_status      on public.ofertas_licenciamento (status);
create index if not exists idx_ofertas_deadline    on public.ofertas_licenciamento (deadline_at) where status in ('aguardando_editora','editora_cadastrada','em_assinatura');
create unique index if not exists uq_ofertas_pi    on public.ofertas_licenciamento (stripe_payment_intent_id) where stripe_payment_intent_id is not null;
create unique index if not exists uq_ofertas_sess  on public.ofertas_licenciamento (stripe_checkout_session_id) where stripe_checkout_session_id is not null;
create or replace function public._touch_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at := now(); return new; end $$;
drop trigger if exists trg_ofertas_touch on public.ofertas_licenciamento;
create trigger trg_ofertas_touch before update on public.ofertas_licenciamento
  for each row execute function public._touch_updated_at();
alter table public.contracts
  add column if not exists trilateral boolean not null default false,
  add column if not exists oferta_id  uuid references public.ofertas_licenciamento(id) on delete set null;
do $$
begin
  alter table public.contract_signers drop constraint if exists signers_role_check;
  alter table public.contract_signers add constraint signers_role_check
    check (role in ('autor','coautor','intérprete','interprete','editora','editora_terceira','gravan'));
exception when others then null;
end $$;
alter table public.ofertas_licenciamento enable row level security;
drop policy if exists "ofertas_sel" on public.ofertas_licenciamento;
create policy "ofertas_sel" on public.ofertas_licenciamento for select using (
  auth.uid() = comprador_id
  or auth.uid() = editora_terceira_id
  or exists (
    select 1 from public.obras o
    where o.id = ofertas_licenciamento.obra_id and o.titular_id = auth.uid()
  )
  or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
);
revoke insert, update, delete on public.ofertas_licenciamento from anon, authenticated;
select
  'obras.obra_editada_terceiros'   as item,
  exists(select 1 from information_schema.columns where table_schema='public' and table_name='obras'
         and column_name='obra_editada_terceiros') as ok
union all select 'obras.editora_terceira_email',
  exists(select 1 from information_schema.columns where table_schema='public' and table_name='obras'
         and column_name='editora_terceira_email')
union all select 'table ofertas_licenciamento',
  exists(select 1 from information_schema.tables where table_schema='public' and table_name='ofertas_licenciamento')
union all select 'contracts.trilateral',
  exists(select 1 from information_schema.columns where table_schema='public' and table_name='contracts'
         and column_name='trilateral');
CREATE TABLE IF NOT EXISTS dossies (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    obra_id       UUID        NOT NULL REFERENCES obras(id)            ON DELETE CASCADE,
    contrato_id   UUID        REFERENCES contratos_edicao(id)          ON DELETE SET NULL,
    gerado_por    UUID        REFERENCES perfis(id)                    ON DELETE SET NULL,
    storage_path  TEXT        NOT NULL,
    hash_sha256   TEXT        NOT NULL,
    titulo_obra   TEXT        NOT NULL DEFAULT '',
    metadata      JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name      = 'dossies'
          AND constraint_name = 'dossies_contrato_id_fkey'
    ) THEN
        ALTER TABLE dossies DROP CONSTRAINT dossies_contrato_id_fkey;
        ALTER TABLE dossies ADD CONSTRAINT dossies_contrato_id_fkey
            FOREIGN KEY (contrato_id)
            REFERENCES contratos_edicao(id)
            ON DELETE SET NULL;
    END IF;
END $$;
CREATE INDEX IF NOT EXISTS dossies_obra_id_idx     ON dossies(obra_id);
CREATE INDEX IF NOT EXISTS dossies_gerado_por_idx  ON dossies(gerado_por);
CREATE INDEX IF NOT EXISTS dossies_created_at_idx  ON dossies(created_at DESC);
DO $$
BEGIN
    BEGIN
        CREATE EXTENSION IF NOT EXISTS pg_trgm;
    EXCEPTION WHEN OTHERS THEN
        NULL;
    END;

    IF EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'
    ) THEN
        EXECUTE
            'CREATE INDEX IF NOT EXISTS dossies_titulo_obra_idx '
            'ON dossies USING gin (titulo_obra gin_trgm_ops)';
    END IF;
END $$;
ALTER TABLE dossies ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "admin_all_dossies"     ON dossies;
DROP POLICY IF EXISTS "titular_select_dossie" ON dossies;
DROP POLICY IF EXISTS "editora_select_dossie" ON dossies;
CREATE POLICY "admin_all_dossies"
    ON dossies FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM perfis
            WHERE perfis.id = auth.uid()
              AND perfis.role = 'administrador'
        )
    );
CREATE POLICY "titular_select_dossie"
    ON dossies FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM obras
            WHERE obras.id         = dossies.obra_id
              AND obras.titular_id = auth.uid()
        )
    );
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name   = 'contracts_edicao'
    ) THEN
        EXECUTE $POL$
            CREATE POLICY "editora_select_dossie"
                ON dossies FOR SELECT
                USING (
                    EXISTS (
                        SELECT 1 FROM contracts_edicao
                        WHERE contracts_edicao.obra_id      = dossies.obra_id
                          AND contracts_edicao.publisher_id = auth.uid()
                    )
                )
        $POL$;
    END IF;
END $$;
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'dossies',
    'dossies',
    false,
    104857600,                                       -- 100 MB
    ARRAY['application/zip', 'application/octet-stream']
)
ON CONFLICT (id) DO UPDATE
    SET public          = EXCLUDED.public,
        file_size_limit = EXCLUDED.file_size_limit,
        allowed_mime_types = EXCLUDED.allowed_mime_types;
DROP POLICY IF EXISTS "dossies storage insert" ON storage.objects;
DROP POLICY IF EXISTS "dossies storage select" ON storage.objects;
DROP POLICY IF EXISTS "dossies storage update" ON storage.objects;
DROP POLICY IF EXISTS "dossies storage delete" ON storage.objects;
CREATE POLICY "dossies storage insert"
    ON storage.objects FOR INSERT TO authenticated
    WITH CHECK (bucket_id = 'dossies');
CREATE POLICY "dossies storage select"
    ON storage.objects FOR SELECT TO authenticated
    USING (bucket_id = 'dossies');
CREATE POLICY "dossies storage update"
    ON storage.objects FOR UPDATE TO authenticated
    USING (bucket_id = 'dossies')
    WITH CHECK (bucket_id = 'dossies');
CREATE POLICY "dossies storage delete"
    ON storage.objects FOR DELETE TO authenticated
    USING (bucket_id = 'dossies');
create table if not exists public.notificacoes (
  id           uuid primary key default gen_random_uuid(),
  perfil_id    uuid not null references public.perfis(id) on delete cascade,
  tipo         text not null,
  titulo       text not null,
  mensagem     text,
  link         text,
  payload      jsonb default '{}'::jsonb,
  lida         boolean not null default false,
  criada_em    timestamptz not null default now(),
  lida_em      timestamptz
);
create index if not exists idx_notif_perfil_lida_data
  on public.notificacoes (perfil_id, lida, criada_em desc);
alter table public.notificacoes enable row level security;
drop policy if exists "ler_proprias" on public.notificacoes;
create policy "ler_proprias" on public.notificacoes
  for select using (auth.uid() = perfil_id);
drop policy if exists "marcar_proprias" on public.notificacoes;
create policy "marcar_proprias" on public.notificacoes
  for update using (auth.uid() = perfil_id) with check (auth.uid() = perfil_id);
grant select, update on public.notificacoes to authenticated;
do $$
begin
  if not exists (
    select 1
    from   pg_publication_tables
    where  pubname = 'supabase_realtime'
      and  schemaname = 'public'
      and  tablename  = 'notificacoes'
  ) then
    execute 'alter publication supabase_realtime add table public.notificacoes';
  end if;
end$$;
alter table public.notificacoes replica identity full;
alter table public.notificacoes enable row level security;
drop policy if exists "notif_owner_select" on public.notificacoes;
create policy "notif_owner_select" on public.notificacoes
  for select using (perfil_id = auth.uid());
drop policy if exists "notif_owner_update" on public.notificacoes;
create policy "notif_owner_update" on public.notificacoes
  for update using (perfil_id = auth.uid())
  with check (perfil_id = auth.uid());
drop policy if exists "notif_owner_delete" on public.notificacoes;
create policy "notif_owner_delete" on public.notificacoes
  for delete using (perfil_id = auth.uid());
create table if not exists public.push_subscriptions (
  id            uuid primary key default gen_random_uuid(),
  perfil_id     uuid not null references public.perfis(id) on delete cascade,
  endpoint      text not null unique,
  p256dh        text not null,
  auth_key      text not null,
  user_agent    text,
  created_at    timestamptz not null default now(),
  last_used_at  timestamptz not null default now()
);
create index if not exists idx_push_subs_perfil on public.push_subscriptions(perfil_id);
comment on table public.push_subscriptions is
  'Assinaturas de Web Push (VAPID) por perfil. Cada navegador/dispositivo registra uma entrada única (endpoint).';
alter table public.push_subscriptions enable row level security;
drop policy if exists "push_subs_owner_select" on public.push_subscriptions;
create policy "push_subs_owner_select" on public.push_subscriptions
  for select using (perfil_id = auth.uid());
drop policy if exists "push_subs_owner_insert" on public.push_subscriptions;
create policy "push_subs_owner_insert" on public.push_subscriptions
  for insert with check (perfil_id = auth.uid());
drop policy if exists "push_subs_owner_delete" on public.push_subscriptions;
create policy "push_subs_owner_delete" on public.push_subscriptions
  for delete using (perfil_id = auth.uid());
create table if not exists public.agregado_convites (
  id            uuid primary key default gen_random_uuid(),
  editora_id    uuid not null references public.perfis(id) on delete cascade,
  artista_id    uuid          references public.perfis(id) on delete cascade,
  email_artista text not null,
  modo          text not null check (modo in ('cadastrar','adicionar')),
  status        text not null default 'pendente'
                check (status in ('pendente','aceito','recusado','cancelado','expirado')),
  token         text not null unique default encode(gen_random_bytes(24),'hex'),
  termo_html                  text not null,
  termo_versao                text not null default 'v1',
  responsavel_editora_nome    text,
  responsavel_editora_cpf_mask text,    -- ex.: "***.***.***-12" (último bloco)
  editora_aceito_em           timestamptz not null default now(),
  editora_aceito_ip           text,
  termo_aceito_pelo_artista_em timestamptz,
  termo_aceito_ip             text,
  assinatura_artista_nome     text,
  decided_at  timestamptz,
  expires_at  timestamptz not null default (now() + interval '30 days'),
  created_at  timestamptz not null default now()
);
create index if not exists idx_agconvites_editora  on public.agregado_convites(editora_id);
create index if not exists idx_agconvites_artista  on public.agregado_convites(artista_id);
create index if not exists idx_agconvites_email    on public.agregado_convites(lower(email_artista));
create index if not exists idx_agconvites_status   on public.agregado_convites(status);
create unique index if not exists uq_agconvites_pendente_por_email
  on public.agregado_convites(editora_id, lower(email_artista))
  where status = 'pendente';
comment on table public.agregado_convites is
  'Convites de agregação editora→artista. Cada convite carrega um termo jurídico imutável que ambas partes assinam digitalmente.';
alter table public.agregado_convites enable row level security;
drop policy if exists "ag_convites_editora_select" on public.agregado_convites;
create policy "ag_convites_editora_select" on public.agregado_convites
  for select using (editora_id = auth.uid());
drop policy if exists "ag_convites_editora_insert" on public.agregado_convites;
create policy "ag_convites_editora_insert" on public.agregado_convites
  for insert with check (editora_id = auth.uid());
drop policy if exists "ag_convites_editora_cancelar" on public.agregado_convites;
create policy "ag_convites_editora_cancelar" on public.agregado_convites
  for update using (editora_id = auth.uid())
  with check (editora_id = auth.uid());
drop policy if exists "ag_convites_artista_select" on public.agregado_convites;
create policy "ag_convites_artista_select" on public.agregado_convites
  for select using (
    artista_id = auth.uid()
    or lower(email_artista) = (select lower(email) from public.perfis where id = auth.uid())
  );
drop policy if exists "ag_convites_artista_decidir" on public.agregado_convites;
create policy "ag_convites_artista_decidir" on public.agregado_convites
  for update using (
    artista_id = auth.uid()
    or lower(email_artista) = (select lower(email) from public.perfis where id = auth.uid())
  )
  with check (
    artista_id = auth.uid()
    or lower(email_artista) = (select lower(email) from public.perfis where id = auth.uid())
  );
drop policy if exists "ag_convites_admin_all" on public.agregado_convites;
create policy "ag_convites_admin_all" on public.agregado_convites
  for all using (
    exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
  );
ALTER TABLE obras
  ADD COLUMN IF NOT EXISTS cover_url   text,
  ADD COLUMN IF NOT EXISTS letra_status text NOT NULL DEFAULT 'pendente'
    CHECK (letra_status IN ('pendente', 'transcrevendo', 'pronta', 'erro'));
CREATE INDEX IF NOT EXISTS idx_obras_letra_status ON obras (letra_status);
  begin;
  select id, length(valor) as tamanho_atual, updated_at as antes
  from public.landing_content
  where id in (
    'contrato_edicao_template',
    'contrato_edicao_publisher_template',
    'contrato_edicao_versao'
  )
  order by id;
  insert into public.landing_content (id, valor)
  values ('contrato_edicao_template', $CT$CONTRATO DE EDIÇÃO DE OBRAS MUSICAIS E OUTRAS AVENÇAS
Pelo presente instrumento particular, de um lado:
AUTOR: {{nome_completo}}, portador do RG nº {{rg}}, inscrito no CPF/MF sob o nº {{cpf}}, residente e domiciliado em {{endereco_completo}}, e-mail {{email}}, doravante denominado "AUTOR";
e, de outro lado:
EDITORA: {{plataforma_razao_social}}, inscrita no CNPJ/MF sob o nº {{plataforma_cnpj}}, com sede em {{plataforma_endereco}}, doravante denominada "EDITORA";
AUTOR e EDITORA, doravante denominadas, em conjunto, "PARTES" e, individualmente, "PARTE", firmam entre si o presente Contrato de Edição de Obras Musicais e Outras Avenças, doravante denominado "Contrato", mediante as cláusulas e condições a seguir.
CONSIDERANDO QUE:
(i) o AUTOR é titular de {{share_autor_pct}}% (por cento) dos direitos autorais sobre a obra lítero-musical intitulada "{{obra_nome}}", doravante denominada "OBRA";
(ii) sendo os demais titulares/coautores: {{coautores_lista}};
(iii) a EDITORA, por meio da assinatura deste Contrato, tornar-se-á a editora musical e detentora dos direitos autorais patrimoniais sobre a parte do AUTOR na OBRA, observados os termos aqui previstos, nos moldes da Lei nº 9.610/1998 (Lei de Direitos Autorais).
CLÁUSULA PRIMEIRA — OBJETO
1.1 Por meio deste Contrato, o AUTOR (i) contrata com a EDITORA a edição musical de sua parte sobre a OBRA, com indicação do respectivo percentual de edição, em regime de absoluta exclusividade e sem qualquer limitação territorial; e (ii) outorga, desde logo, à EDITORA o direito único e exclusivo sobre o recebimento de qualquer valor decorrente das explorações comerciais havidas com a edição da OBRA pela EDITORA, na forma, extensão e aplicação em que os possui por força das Leis Brasileiras e Tratados Internacionais em vigor, e dos que vierem a vigorar no futuro, observadas as remunerações devidas ao AUTOR na forma da Cláusula Sexta.
1.2 O AUTOR desde já concorda e reconhece que a EDITORA poderá contratar com quaisquer outras editoras a administração das obras musicais e/ou lítero-musicais que integram ou venham a integrar o catálogo da EDITORA, incluindo a OBRA objeto deste Contrato, em relação ao que o AUTOR não se opõe.
1.3 Para todos os efeitos legais, integra o presente Contrato a LETRA COMPLETA da OBRA, conforme cadastrada pelo AUTOR na plataforma Gravan, transcrita a seguir:
— CORPO DA OBRA "{{obra_nome}}" —
{{obra_letra}}
— FIM DO CORPO DA OBRA —
CLÁUSULA SEGUNDA — DIREITOS
2.1 Pelo presente Contrato, ficam sob a égide da EDITORA, sem quaisquer limitações e durante todo o tempo de proteção legal dos direitos autorais e em todos os países do mundo, a totalidade dos direitos e faculdades que no seu conjunto constituem o direito autoral do AUTOR sobre a OBRA, em todos os seus aspectos, manifestações e aplicações diretas ou indiretas, processos de reprodução e divulgação ou extensões e ampliações, tais como, mas não limitados a: edição gráfica e fonomecânica em todas as suas formas, aplicações, sistemas e processos, quer atuais, quer os que venham a ser inventados ou aperfeiçoados no futuro; transcrição; adaptação; versões; variação; redução; execução; irradiação; distribuição física ou eletrônica, incluindo, mas não se limitando a download, streaming, ringtone, truetone, qualquer tipo de sincronização em suporte físico ou digital, existente ou que venha a existir, tais como televisão, VOD, adaptação e/ou inclusão cinematográfica, ou, ainda, em peças publicitárias, com a adaptação da letra e/ou melodia, em publicidade gráfica, sonora ou audiovisual, bem como qualquer forma de exploração, reprodução e divulgação da OBRA, incluindo sua execução pública, sem nenhuma exceção, mesmo que no futuro outras venham a ser as denominações da técnica ou da praxe, com todas as faculdades de exploração comercial e industrial necessárias para o exercício dos respectivos direitos, a exclusivo arbítrio da EDITORA. Serve o presente Contrato como título para que a EDITORA possa efetuar, onde lhe for útil ou conveniente, os registros e depósitos necessários para o irrestrito reconhecimento de seu direito, em todos os países do mundo, com faculdade de transferir os direitos ora adquiridos a terceiros, no todo ou em parte, a qualquer título.
2.2 Fica reservada ao AUTOR, na forma da lei, a integralidade dos direitos morais sobre sua parte na OBRA, nos termos do art. 24 da Lei nº 9.610/1998.
CLÁUSULA TERCEIRA — PROCURAÇÃO
3.1 Fica a EDITORA desde já constituída como bastante procuradora do AUTOR, com amplos e irrevogáveis poderes para que, em seu nome, possa defender e receber os direitos concernentes à OBRA.
CLÁUSULA QUARTA — ORIGINALIDADE
4.1 O AUTOR é exclusiva e pessoalmente responsável pela originalidade de sua parte sobre a OBRA, exonerando a EDITORA de toda e qualquer responsabilidade nesse sentido e obrigando-se a indenizá-la pelas perdas e danos que esta vier a sofrer em caso de contestação.
4.2 O AUTOR declara, sob as penas da lei, que a OBRA é de sua autoria (ou coautoria, conforme o caso), não constituindo plágio ou violação de direito autoral de terceiros, e que se encontra LIVRE e DESEMBARAÇADA de qualquer contrato de edição prévio com terceiros.
CLÁUSULA QUINTA — EDIÇÃO
5.1 A EDITORA, por este Contrato, obriga-se a editar, divulgar e expor à venda a OBRA, sendo certo que a tiragem de cada edição, o número de edições, a fixação da época, a determinação da forma e os detalhes de confecção artística, bem como o preço de venda ao público das edições, ficarão a exclusivo critério da EDITORA, que deverá envidar seus melhores esforços para consultar o AUTOR sobre valores das licenças, em especial na eventualidade de licenças sem ônus.
5.2 A EDITORA compromete-se a envidar seus melhores esforços para consultar o AUTOR sobre oportunidades de comercialização e uso da OBRA.
CLÁUSULA SEXTA — REMUNERAÇÃO
6.1 Pelo presente Contrato, a EDITORA obriga-se a pagar ao AUTOR os percentuais abaixo especificados, relativos às receitas líquidas efetivamente recebidas pela EDITORA pela exploração da OBRA, sempre incidentes sobre o percentual de direitos autorais do AUTOR sobre a OBRA, da seguinte forma:
  (a) Direitos de Sincronização e adaptação em produções audiovisuais, publicitárias ou não: 70% (setenta por cento) ao AUTOR e 30% (trinta por cento) à EDITORA;
  (b) Direitos de reprodução gráfica (edição); distribuição de direitos fonomecânicos; venda e locação de gravações sonoras; distribuição mediante meios óticos, cabo, satélites, redes de informação e rede local e/ou mundial de computadores que permitam ao usuário a seleção da obra ou que importe em pagamento pelo usuário; inclusão em base de dados ou qualquer forma de armazenamento; e demais modalidades previstas na Cláusula Segunda: 75% (setenta e cinco por cento) ao AUTOR e 25% (vinte e cinco por cento) à EDITORA;
  (c) Direitos de Execução Pública, observado o disposto na Cláusula 6.2: 75% (setenta e cinco por cento) ao AUTOR e 25% (vinte e cinco por cento) à EDITORA.
6.2 Os direitos de execução pública serão pagos ao AUTOR diretamente pela Sociedade de Autores a que este for filiado, sob sua exclusiva responsabilidade.
6.3 O AUTOR declara-se ciente e concorda expressamente que a EDITORA procederá à retenção proporcional do valor correspondente ao Imposto de Renda pago pela EDITORA sobre a remuneração recebida por esta pela exploração da OBRA, repassando ao AUTOR o montante líquido devido após a retenção.
CLÁUSULA SÉTIMA — DISPOSIÇÕES GERAIS
7.1 Este Contrato cancela e substitui qualquer acordo anterior firmado entre as PARTES, verbal ou escrito, referente ao mesmo objeto, obrigando as PARTES por si, seus herdeiros e sucessores.
7.2 Este Contrato poderá ser rescindido a qualquer tempo, por qualquer das PARTES, mediante notificação prévia e expressa com até 6 (seis) meses da efetiva rescisão. Toda e qualquer licença concedida durante a vigência, inclusive nos 6 (seis) meses seguintes à notificação, reputar-se-ão válidas e definitivas.
7.3 A EDITORA procederá trimestralmente, na conta bancária em nome do AUTOR indicada no cadastro da plataforma, à liquidação dos direitos eventualmente devidos ao AUTOR, mediante a transferência das receitas que lhe pertencem, acompanhada dos respectivos demonstrativos, mencionando a fonte pagadora, o período a que se refere o crédito, o título da OBRA e o valor de cada crédito, devendo efetuá-la dentro dos 60 (sessenta) dias posteriores ao fim de cada trimestre.
7.4 O AUTOR poderá, anualmente e em adição às prestações de contas descritas na Cláusula 7.3, requerer uma prestação de contas adicional, completa e consolidada referente ao exercício fiscal em curso.
7.5 O AUTOR assegura à EDITORA absoluta preferência, em igualdade de condições com propostas de terceiros, para a contratação de modalidades de exploração econômica da OBRA que, eventualmente, não tenham sido previstas neste Contrato, e para aquelas modalidades que venham a existir no futuro.
7.6 Este Contrato poderá ser cedido pela EDITORA a qualquer de suas associadas, coligadas ou filiadas, já existentes ou que venham a ser constituídas.
7.7 As PARTES elegem o foro da Comarca da Capital da Cidade do Rio de Janeiro, Estado do Rio de Janeiro, como único competente para dirimir eventuais controvérsias oriundas deste Contrato, com expressa renúncia a qualquer outro, por mais privilegiado que seja.
7.8 As PARTES declaram aceitar e reconhecer como válida, autêntica e verdadeira a comprovação da autoria e integridade deste documento realizada por meio eletrônico, nos termos da MP nº 2.200-2/2001, Lei nº 14.063/2020 e legislação correlata. A aceitação eletrônica do presente Contrato no ato do cadastro da OBRA na plataforma Gravan, com registro de data, hora, IP e hash SHA-256 do conteúdo, é considerada ASSINATURA VÁLIDA E VINCULANTE para todos os efeitos legais.
E, por estarem justas e acordadas, as PARTES firmam este instrumento eletronicamente na data abaixo:
Rio de Janeiro, {{data_assinatura}}.
___________________________________________
{{nome_completo}}
CPF: {{cpf}}
(AUTOR)
___________________________________________
{{plataforma_razao_social}}
CNPJ: {{plataforma_cnpj}}
(EDITORA)
$CT$)
  on conflict (id) do update
    set valor = excluded.valor,
        updated_at = now();
  insert into public.landing_content (id, valor)
  values ('contrato_edicao_publisher_template', $CP$CONTRATO DE EDIÇÃO DE OBRAS MUSICAIS — EDITORA
Pelo presente instrumento particular, de um lado:
AUTOR: {{autor_nome}}, portador do RG nº {{autor_rg}}, inscrito no CPF/MF sob o nº {{autor_cpf}}, residente e domiciliado em {{autor_endereco}}, e-mail {{autor_email}}, doravante denominado "AUTOR";
e, de outro lado:
EDITORA: {{publisher_razao_social}} (nome fantasia: {{publisher_nome_fantasia}}), inscrita no CNPJ/MF sob o nº {{publisher_cnpj}}, com sede em {{publisher_endereco}}, neste ato representada por seu responsável legal {{publisher_responsavel_nome}}, CPF {{publisher_responsavel_cpf}}, doravante denominada "EDITORA";
AUTOR e EDITORA, em conjunto "PARTES", firmam o presente Contrato de Edição de Obras Musicais, mediante as cláusulas a seguir.
CONSIDERANDO QUE:
(i) o AUTOR é titular de {{share_autor_pct}}% dos direitos autorais sobre a obra "{{obra_nome}}", doravante "OBRA";
(ii) os demais coautores são: {{coautores_lista}};
(iii) a OBRA será gerida pela EDITORA por meio da plataforma GRAVAN.
CLÁUSULA PRIMEIRA — OBJETO
1.1 O AUTOR contrata com a EDITORA a edição musical de sua parte sobre a OBRA, em regime de exclusividade, sem limitação territorial, nos termos da Lei 9.610/1998.
1.2 Para todos os efeitos legais, integra o presente Contrato o CORPO DA OBRA, conforme cadastrado pelo AUTOR na plataforma GRAVAN, transcrito a seguir:
— CORPO DA OBRA "{{obra_nome}}" —
{{obra_letra}}
— FIM DO CORPO DA OBRA —
CLÁUSULA SEGUNDA — DIREITOS
2.1 Ficam sob a égide da EDITORA todos os direitos patrimoniais sobre a OBRA durante o prazo de proteção legal, em todos os países.
2.2 Ficam reservados ao AUTOR os direitos morais (art. 24 da Lei 9.610/1998).
CLÁUSULA TERCEIRA — ORIGINALIDADE
3.1 O AUTOR declara que a OBRA é de sua autoria/coautoria, livre de plágio e de contratos prévios.
CLÁUSULA QUARTA — REMUNERAÇÃO DO AUTOR
4.1 A EDITORA pagará ao AUTOR sobre as receitas líquidas relativas à parte do AUTOR na OBRA:
  (a) Sincronização: 70% AUTOR / 30% EDITORA;
  (b) Reprodução, distribuição digital, fonomecânicos: 75% AUTOR / 25% EDITORA;
  (c) Execução pública: 75% AUTOR / 25% EDITORA, paga diretamente ao AUTOR pela sociedade de autores.
CLÁUSULA QUINTA — REMUNERAÇÃO DA PLATAFORMA (FEE DE INTERMEDIAÇÃO EDITORIAL)
5.1 Em razão da utilização da plataforma GRAVAN e dos serviços de intermediação, gestão e disponibilização de obras musicais, a EDITORA concorda em pagar à GRAVAN o equivalente a 5% (cinco por cento) sobre todos os valores brutos recebidos pela EDITORA decorrentes da exploração econômica das obras cadastradas na plataforma.
Parágrafo Primeiro: O percentual incidirá sobre todas as receitas, incluindo, mas não se limitando a licenciamento, cessão de direitos, sincronização, distribuição digital e execução pública.
Parágrafo Segundo: O pagamento deverá ser realizado no prazo máximo de 30 (trinta) dias corridos contados do recebimento dos valores pela EDITORA.
Parágrafo Terceiro: O pagamento será feito diretamente à conta bancária da GRAVAN:
  Banco: {{gravan_banco}}
  Agência: {{gravan_agencia}}
  Conta: {{gravan_conta}}
  Titular: {{gravan_titular}}
  CNPJ: {{gravan_cnpj}}
Parágrafo Quarto: A EDITORA se compromete a manter registros financeiros e fornecer relatórios sempre que solicitado pela GRAVAN.
Parágrafo Quinto: O não pagamento dentro do prazo estipulado poderá resultar na suspensão da conta da EDITORA na plataforma e nas medidas legais cabíveis.
CLÁUSULA SEXTA — RESCISÃO
6.1 Este Contrato pode ser rescindido por qualquer das PARTES mediante notificação prévia de 90 (noventa) dias.
CLÁUSULA SÉTIMA — FORO
7.1 Fica eleito o foro da comarca da cidade do Rio de Janeiro/RJ.
ASSINATURAS ELETRÔNICAS
Este instrumento é firmado eletronicamente, com registro de data, hora, IP anonimizado (SHA-256) e hash de integridade. A aceitação eletrônica por cada parte configura assinatura válida e vinculante (MP 2.200-2/2001; Lei 14.063/2020).
Data de emissão: {{data_emissao}}
Hash SHA-256: {{conteudo_hash}}
$CP$)
  on conflict (id) do update
    set valor = excluded.valor,
        updated_at = now();
  insert into public.landing_content (id, valor)
  values ('contrato_edicao_versao', 'v2.1 - Abr/2026')
  on conflict (id) do update
    set valor = excluded.valor,
        updated_at = now();
  select
    id,
    length(valor) as tamanho_novo,
    case
      when valor like '%CORPO DA OBRA%' then '✓ OK — bloco CORPO DA OBRA presente'
      when id = 'contrato_edicao_versao' and valor = 'v2.1 - Abr/2026' then '✓ OK — versão atualizada'
      else '❌ não atualizado'
    end as status,
    updated_at
  from public.landing_content
  where id in (
    'contrato_edicao_template',
    'contrato_edicao_publisher_template',
    'contrato_edicao_versao'
  )
  order by id;
  commit;
DROP VIEW IF EXISTS public.catalogo_publico CASCADE;
CREATE VIEW public.catalogo_publico AS
SELECT
  o.id,
  o.nome,
  o.genero,
  o.bpm,
  o.preco_cents,
  o.capa_url,
  o.cover_url,
  o.audio_path,
  o.letra,
  o.letra_status,
  o.status,
  o.compositor_id,
  o.compositor_id            AS titular_id,
  p.nome_artistico           AS compositor_nome,
  COALESCE(p.nome_artistico, p.nome) AS titular_nome,
  p.nivel                    AS titular_nivel,
  p.avatar_url               AS titular_avatar_url,
  o.created_at
FROM public.obras o
LEFT JOIN public.perfis p ON p.id = o.compositor_id
WHERE o.status::text = 'publicada';
GRANT SELECT ON public.catalogo_publico TO anon, authenticated;
  CREATE INDEX IF NOT EXISTS idx_transacoes_vendedor
    ON public.transacoes (vendedor_id);
  CREATE INDEX IF NOT EXISTS idx_transacoes_created_at
    ON public.transacoes (created_at DESC);
  CREATE INDEX IF NOT EXISTS idx_saques_perfil
    ON public.saques (perfil_id);
  CREATE INDEX IF NOT EXISTS idx_saques_status
    ON public.saques (status);
  CREATE INDEX IF NOT EXISTS idx_play_events_perfil
    ON public.play_events (perfil_id)
    WHERE perfil_id IS NOT NULL;
  CREATE INDEX IF NOT EXISTS idx_contracts_status
    ON public.contracts (status);
  CREATE INDEX IF NOT EXISTS idx_contracts_edicao_completed
    ON public.contracts_edicao (completed_at DESC)
    WHERE completed_at IS NOT NULL;
  CREATE INDEX IF NOT EXISTS idx_obras_created_at
    ON public.obras (created_at DESC);
  CREATE INDEX IF NOT EXISTS idx_perfis_plano
    ON public.perfis (plano);
  CREATE INDEX IF NOT EXISTS idx_perfis_status_assinatura
    ON public.perfis (status_assinatura)
    WHERE status_assinatura = 'ativa';
  CREATE INDEX IF NOT EXISTS idx_obra_analytics_plays
    ON public.obra_analytics (plays_count DESC);
  CREATE INDEX IF NOT EXISTS idx_obra_analytics_favorites
    ON public.obra_analytics (favorites_count DESC);
  CREATE INDEX IF NOT EXISTS idx_obras_compositor_status
    ON public.obras (compositor_id, status);
  CREATE INDEX IF NOT EXISTS idx_obras_status_genero
    ON public.obras (status, genero)
    WHERE status = 'publicada';
  CREATE INDEX IF NOT EXISTS idx_transacoes_vendedor_status
    ON public.transacoes (vendedor_id, status);
  CREATE INDEX IF NOT EXISTS idx_transacoes_comprador_status
    ON public.transacoes (comprador_id, status);
  CREATE INDEX IF NOT EXISTS idx_perfis_publisher_role
    ON public.perfis (publisher_id, role)
    WHERE publisher_id IS NOT NULL;
  CREATE INDEX IF NOT EXISTS idx_obras_publisher_status
    ON public.obras (publisher_id, status)
    WHERE publisher_id IS NOT NULL;
  ALTER TABLE public.obras
    ADD COLUMN IF NOT EXISTS fts tsvector
    GENERATED ALWAYS AS (
      to_tsvector('portuguese',
        COALESCE(nome, '') || ' ' ||
        COALESCE(genero, '')
      )
    ) STORED;
  CREATE INDEX IF NOT EXISTS idx_obras_fts
    ON public.obras USING GIN (fts);
  CREATE INDEX IF NOT EXISTS idx_obras_catalogo_publico
    ON public.obras (genero, created_at DESC)
    WHERE status = 'publicada';
  CREATE MATERIALIZED VIEW IF NOT EXISTS public.mv_catalogo AS
  SELECT
    o.id,
    o.nome,
    o.genero,
    o.bpm,
    o.capa_url,
    o.preco_cents,
    o.created_at,
    o.compositor_id,
    o.publisher_id,
    p.nome           AS compositor_nome,
    p.nome_artistico AS compositor_artistico,
    COALESCE(a.plays_count, 0)     AS plays_count,
    COALESCE(a.favorites_count, 0) AS favorites_count,
    a.last_played_at
  FROM public.obras o
  LEFT JOIN public.perfis        p ON p.id = o.compositor_id
  LEFT JOIN public.obra_analytics a ON a.obra_id = o.id
  WHERE o.status = 'publicada';
  CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_catalogo_id
    ON public.mv_catalogo (id);
  CREATE INDEX IF NOT EXISTS idx_mv_catalogo_genero
    ON public.mv_catalogo (genero);
  CREATE INDEX IF NOT EXISTS idx_mv_catalogo_plays
    ON public.mv_catalogo (plays_count DESC);
  CREATE INDEX IF NOT EXISTS idx_mv_catalogo_favorites
    ON public.mv_catalogo (favorites_count DESC);
  CREATE OR REPLACE FUNCTION public.refresh_mv_catalogo()
  RETURNS void
  LANGUAGE sql
  SECURITY DEFINER
  AS $$
    REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_catalogo;
  $$;
  CREATE OR REPLACE FUNCTION public.fn_obra_status_changed()
  RETURNS trigger
  LANGUAGE plpgsql
  AS $$
  BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status OR
       OLD.nome   IS DISTINCT FROM NEW.nome   OR
       OLD.genero IS DISTINCT FROM NEW.genero THEN
      PERFORM public.refresh_mv_catalogo();
    END IF;
    RETURN NEW;
  END;
  $$;
  DROP TRIGGER IF EXISTS trg_obra_refresh_catalogo ON public.obras;
  CREATE TRIGGER trg_obra_refresh_catalogo
    AFTER UPDATE ON public.obras
    FOR EACH ROW EXECUTE FUNCTION public.fn_obra_status_changed();
  SELECT
    schemaname,
    relname      AS tabela,
    indexrelname AS indice,
    pg_size_pretty(pg_relation_size(indexrelid)) AS tamanho
  FROM pg_stat_user_indexes
  WHERE schemaname = 'public'
  ORDER BY relname, indexrelname;
alter table public.obras add column if not exists isrc text;
alter table public.obras add column if not exists iswc text;
create table if not exists public.contracts (
  id               uuid primary key default gen_random_uuid(),
  transacao_id     uuid unique references public.transacoes(id) on delete cascade,
  obra_id          uuid not null references public.obras(id)      on delete cascade,
  seller_id        uuid not null references public.perfis(id)     on delete set null,
  buyer_id         uuid not null references public.perfis(id)     on delete set null,
  valor_cents      integer not null,
  contract_html    text not null,
  contract_text    text not null,
  status           text not null default 'pendente',
  versao           text not null default 'v1.0',
  completed_at     timestamptz,
  created_at       timestamptz not null default now(),
  constraint contracts_status_check check (status in ('pendente','assinado','concluído','cancelado'))
);
create index if not exists idx_contracts_obra     on public.contracts (obra_id);
create index if not exists idx_contracts_seller   on public.contracts (seller_id);
create index if not exists idx_contracts_buyer    on public.contracts (buyer_id);
create table if not exists public.contract_signers (
  id            uuid primary key default gen_random_uuid(),
  contract_id   uuid not null references public.contracts(id) on delete cascade,
  user_id       uuid not null references public.perfis(id)    on delete set null,
  role          text not null,
  share_pct     numeric(6,3),
  signed        boolean not null default false,
  signed_at     timestamptz,
  ip_hash       text,
  created_at    timestamptz not null default now(),
  unique (contract_id, user_id),
  constraint signers_role_check check (role in ('autor','coautor','intérprete','interprete'))
);
create index if not exists idx_signers_contract on public.contract_signers (contract_id);
create index if not exists idx_signers_user     on public.contract_signers (user_id);
create table if not exists public.contract_events (
  id          uuid primary key default gen_random_uuid(),
  contract_id uuid not null references public.contracts(id) on delete cascade,
  user_id     uuid references public.perfis(id) on delete set null,
  event_type  text not null,
  payload     jsonb,
  created_at  timestamptz not null default now()
);
create index if not exists idx_events_contract on public.contract_events (contract_id, created_at desc);
alter table public.contracts        enable row level security;
alter table public.contract_signers enable row level security;
alter table public.contract_events  enable row level security;
drop policy if exists "contracts_sel" on public.contracts;
create policy "contracts_sel" on public.contracts for select using (
  auth.uid() = seller_id
  or auth.uid() = buyer_id
  or exists (select 1 from public.contract_signers s where s.contract_id = contracts.id and s.user_id = auth.uid())
  or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
);
drop policy if exists "signers_sel" on public.contract_signers;
create policy "signers_sel" on public.contract_signers for select using (
  auth.uid() = user_id
  or exists (select 1 from public.contracts c where c.id = contract_signers.contract_id and (c.seller_id = auth.uid() or c.buyer_id = auth.uid()))
  or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
);
drop policy if exists "events_sel" on public.contract_events;
create policy "events_sel" on public.contract_events for select using (
  exists (select 1 from public.contracts c where c.id = contract_events.contract_id and (c.seller_id = auth.uid() or c.buyer_id = auth.uid()))
  or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
);
revoke insert, update, delete on public.contracts        from anon, authenticated;
revoke insert, update, delete on public.contract_signers from anon, authenticated;
revoke insert, update, delete on public.contract_events  from anon, authenticated;
select
  'table contracts'         as item, exists(select 1 from information_schema.tables where table_schema='public' and table_name='contracts') as ok
union all select 'table contract_signers',  exists(select 1 from information_schema.tables where table_schema='public' and table_name='contract_signers')
union all select 'table contract_events',   exists(select 1 from information_schema.tables where table_schema='public' and table_name='contract_events')
union all select 'obras.isrc',              exists(select 1 from information_schema.columns where table_schema='public' and table_name='obras' and column_name='isrc')
union all select 'obras.iswc',              exists(select 1 from information_schema.columns where table_schema='public' and table_name='obras' and column_name='iswc');
do $$
declare
  pol record;
  obj record;
begin
  -- Dropa TODAS as policies cujo definition menciona "Admin" (case-sensitive)
  for pol in
    select schemaname, tablename, policyname
      from pg_policies
     where qual like '%public.Admin%'
        or qual like '%"Admin"%'
        or with_check like '%public.Admin%'
        or with_check like '%"Admin"%'
  loop
    execute format('drop policy if exists %I on %I.%I',
                   pol.policyname, pol.schemaname, pol.tablename);
  end loop;

  -- Dropa views que mencionam Admin
  for obj in
    select schemaname, viewname
      from pg_views
     where definition like '%public.Admin%' or definition like '%"Admin"%'
  loop
    execute format('drop view if exists %I.%I cascade', obj.schemaname, obj.viewname);
  end loop;

  -- Dropa funções que mencionam Admin
  for obj in
    select n.nspname as schemaname, p.proname as funcname,
           pg_get_function_identity_arguments(p.oid) as args
      from pg_proc p join pg_namespace n on n.oid = p.pronamespace
     where n.nspname = 'public'
       and p.prokind = 'f'                -- só funções normais, não aggregates/windows
       and (pg_get_functiondef(p.oid) like '%public.Admin%'
            or pg_get_functiondef(p.oid) like '%"Admin"%')
  loop
    execute format('drop function if exists %I.%I(%s) cascade',
                   obj.schemaname, obj.funcname, obj.args);
  end loop;
end $$;
alter table public.perfis add column if not exists plano                  text    not null default 'STARTER';
alter table public.perfis add column if not exists status_assinatura      text    not null default 'inativa';
alter table public.perfis add column if not exists assinatura_inicio      timestamptz;
alter table public.perfis add column if not exists assinatura_fim         timestamptz;
alter table public.perfis add column if not exists stripe_customer_id     text;
alter table public.perfis add column if not exists stripe_subscription_id text;
do $$ begin
  alter table public.perfis drop constraint if exists perfis_plano_check;
  alter table public.perfis add  constraint perfis_plano_check             check (plano in ('STARTER','PRO'));
  alter table public.perfis drop constraint if exists perfis_status_assinatura_check;
  alter table public.perfis add  constraint perfis_status_assinatura_check check (status_assinatura in ('ativa','inativa','cancelada','past_due'));
end $$;
create index if not exists idx_perfis_stripe_customer     on public.perfis (stripe_customer_id);
create index if not exists idx_perfis_stripe_subscription on public.perfis (stripe_subscription_id);
create table if not exists public.favoritos (
  id          uuid primary key default gen_random_uuid(),
  perfil_id   uuid not null references public.perfis(id) on delete cascade,
  obra_id     uuid not null references public.obras(id)  on delete cascade,
  created_at  timestamptz not null default now(),
  unique (perfil_id, obra_id)
);
create index if not exists idx_favoritos_perfil on public.favoritos (perfil_id);
create index if not exists idx_favoritos_obra   on public.favoritos (obra_id);
create table if not exists public.obra_analytics (
  obra_id          uuid primary key references public.obras(id) on delete cascade,
  plays_count      int not null default 0,
  favorites_count  int not null default 0,
  last_played_at   timestamptz
);
create table if not exists public.play_events (
  id          uuid primary key default gen_random_uuid(),
  obra_id     uuid not null references public.obras(id) on delete cascade,
  perfil_id   uuid references public.perfis(id) on delete set null,
  ip_hash     text,
  created_at  timestamptz not null default now()
);
create index if not exists idx_play_events_obra on public.play_events (obra_id, created_at desc);
create or replace function public.fn_favoritos_inc()
returns trigger language plpgsql as $$
begin
  insert into public.obra_analytics (obra_id, favorites_count)
       values (new.obra_id, 1)
  on conflict (obra_id) do update set favorites_count = obra_analytics.favorites_count + 1;
  return new;
end $$;
create or replace function public.fn_favoritos_dec()
returns trigger language plpgsql as $$
begin
  update public.obra_analytics
     set favorites_count = greatest(favorites_count - 1, 0)
   where obra_id = old.obra_id;
  return old;
end $$;
drop trigger if exists trg_favoritos_inc on public.favoritos;
create trigger trg_favoritos_inc after insert on public.favoritos
  for each row execute function public.fn_favoritos_inc();
drop trigger if exists trg_favoritos_dec on public.favoritos;
create trigger trg_favoritos_dec after delete on public.favoritos
  for each row execute function public.fn_favoritos_dec();
create or replace function public.fn_play_events_inc()
returns trigger language plpgsql as $$
begin
  insert into public.obra_analytics (obra_id, plays_count, last_played_at)
       values (new.obra_id, 1, new.created_at)
  on conflict (obra_id) do update
     set plays_count    = obra_analytics.plays_count + 1,
         last_played_at = excluded.last_played_at;
  return new;
end $$;
drop trigger if exists trg_play_events_inc on public.play_events;
create trigger trg_play_events_inc after insert on public.play_events
  for each row execute function public.fn_play_events_inc();
alter table public.favoritos      enable row level security;
alter table public.obra_analytics enable row level security;
alter table public.play_events    enable row level security;
drop policy if exists "favoritos_sel" on public.favoritos;
drop policy if exists "favoritos_ins" on public.favoritos;
drop policy if exists "favoritos_del" on public.favoritos;
create policy "favoritos_sel" on public.favoritos for select
  using (auth.uid() = perfil_id or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador'));
create policy "favoritos_ins" on public.favoritos for insert with check (auth.uid() = perfil_id);
create policy "favoritos_del" on public.favoritos for delete using (auth.uid() = perfil_id);
drop policy if exists "analytics_sel_owner" on public.obra_analytics;
create policy "analytics_sel_owner" on public.obra_analytics for select
  using (
    exists (select 1 from public.obras o where o.id = obra_analytics.obra_id and o.titular_id = auth.uid())
    or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
  );
drop policy if exists "play_events_ins" on public.play_events;
create policy "play_events_ins" on public.play_events for insert with check (true);
revoke all on public.play_events from anon, authenticated;
grant insert on public.play_events to anon, authenticated;
select
  'perfis.plano'             as item, exists (select 1 from information_schema.columns where table_schema='public' and table_name='perfis' and column_name='plano')             as ok
union all select 'table favoritos',       exists (select 1 from information_schema.tables  where table_schema='public' and table_name='favoritos')
union all select 'table obra_analytics',  exists (select 1 from information_schema.tables  where table_schema='public' and table_name='obra_analytics')
union all select 'table play_events',     exists (select 1 from information_schema.tables  where table_schema='public' and table_name='play_events');
alter table public.perfis
  add column if not exists stripe_account_id text,
  add column if not exists stripe_charges_enabled boolean default false,
  add column if not exists stripe_payouts_enabled boolean default false,
  add column if not exists stripe_onboarding_completo boolean default false,
  add column if not exists stripe_account_atualizado_em timestamptz;
create index if not exists idx_perfis_stripe_account on public.perfis(stripe_account_id);
create table if not exists public.repasses (
  id              uuid primary key default gen_random_uuid(),
  transacao_id    uuid not null references public.transacoes(id) on delete cascade,
  perfil_id       uuid not null references public.perfis(id),
  valor_cents     int  not null check (valor_cents > 0),
  share_pct       numeric(6,3) not null,
  stripe_transfer_id  text unique,
  stripe_account_id   text,
  status          text not null default 'pendente',
  erro_msg        text,
  metadata        jsonb default '{}'::jsonb,
  created_at      timestamptz default now(),
  enviado_at      timestamptz,
  liberado_at     timestamptz,
  constraint repasses_status_check check (status in
    ('pendente', 'retido', 'enviado', 'falhou', 'revertido'))
);
create index if not exists idx_repasses_transacao on public.repasses(transacao_id);
create index if not exists idx_repasses_perfil    on public.repasses(perfil_id);
create index if not exists idx_repasses_status    on public.repasses(status);
alter table public.repasses enable row level security;
drop policy if exists repasses_select_own on public.repasses;
drop policy if exists repasses_admin_all  on public.repasses;
create policy repasses_select_own on public.repasses
  for select using (perfil_id = auth.uid());
create policy repasses_admin_all on public.repasses
  for all using (
    exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
  );
create or replace view public.v_saldo_retido as
select
  perfil_id,
  count(*)::int                     as qtd_repasses_retidos,
  coalesce(sum(valor_cents),0)::int as valor_retido_cents
from public.repasses
where status = 'retido'
group by perfil_id;
alter table public.saques
  add column if not exists stripe_transfer_id text unique,
  add column if not exists stripe_account_id  text,
  add column if not exists metodo             text default 'paypal';
do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema='public' and table_name='saques'
      and column_name='paypal_email' and is_nullable='NO'
  ) then
    execute 'alter table public.saques alter column paypal_email drop not null';
  end if;
end $$;
create index if not exists idx_saques_stripe_transfer on public.saques(stripe_transfer_id);
  do $$
  begin
    if exists (select 1 from information_schema.tables
                where table_schema='public' and table_name='obras_autores') then
      execute 'drop view if exists public.bi_auditoria_splits cascade';
      execute $v$
        create view public.bi_auditoria_splits as
        select oa.obra_id, o.nome as obra_nome,
               count(*) as qtd_autores, sum(oa.share_pct) as soma_splits
          from public.obras_autores oa
          join public.obras o on o.id = oa.obra_id
         group by oa.obra_id, o.nome
      $v$;
    end if;
  end $$;
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'obras-audio', 'obras-audio', false,
  10 * 1024 * 1024,
  array['audio/mpeg','audio/mp3']
)
on conflict (id) do update
  set public             = excluded.public,
      file_size_limit    = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;
drop policy if exists "obras-audio insert auth"  on storage.objects;
drop policy if exists "obras-audio select auth"  on storage.objects;
drop policy if exists "obras-audio delete owner" on storage.objects;
drop policy if exists "obras-audio update owner" on storage.objects;
create policy "obras-audio insert auth"
on storage.objects for insert to authenticated
with check (
  bucket_id = 'obras-audio'
  and (storage.foldername(name))[1] = auth.uid()::text
);
create policy "obras-audio select auth"
on storage.objects for select to authenticated
using (bucket_id = 'obras-audio');
create policy "obras-audio update owner"
on storage.objects for update to authenticated
using (
  bucket_id = 'obras-audio'
  and (storage.foldername(name))[1] = auth.uid()::text
);
create policy "obras-audio delete owner"
on storage.objects for delete to authenticated
using (
  bucket_id = 'obras-audio'
  and (storage.foldername(name))[1] = auth.uid()::text
);
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'obras-audio', 'obras-audio', false,
  10 * 1024 * 1024,
  array['audio/mpeg','audio/mp3']
)
on conflict (id) do update
  set public             = excluded.public,
      file_size_limit    = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;
drop policy if exists "obras-audio insert auth"  on storage.objects;
drop policy if exists "obras-audio select auth"  on storage.objects;
drop policy if exists "obras-audio delete owner" on storage.objects;
drop policy if exists "obras-audio update owner" on storage.objects;
create policy "obras-audio insert auth"
on storage.objects for insert to authenticated
with check (
  bucket_id = 'obras-audio'
  and (storage.foldername(name))[1] = auth.uid()::text
);
create policy "obras-audio select auth"
on storage.objects for select to authenticated
using (bucket_id = 'obras-audio');
create policy "obras-audio update owner"
on storage.objects for update to authenticated
using (
  bucket_id = 'obras-audio'
  and (storage.foldername(name))[1] = auth.uid()::text
);
create policy "obras-audio delete owner"
on storage.objects for delete to authenticated
using (
  bucket_id = 'obras-audio'
  and (storage.foldername(name))[1] = auth.uid()::text
);