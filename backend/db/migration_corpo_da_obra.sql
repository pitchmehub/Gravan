-- ════════════════════════════════════════════════════════════════
-- Pitch.me — Atualização dos contratos: "LETRA" → "CORPO DA OBRA"
--
-- Atualiza os templates já existentes em public.landing_content
-- substituindo os marcadores antigos da letra pelos novos.
--
-- AFETA AS CHAVES:
--   • contrato_edicao_template            (Contrato de Edição padrão)
--   • contrato_edicao_publisher_template  (Contrato de Edição via editora)
--
-- COMO RODAR:
--   1. Acesse https://app.supabase.com/project/SEU_PROJETO/sql/new
--   2. Cole TODO este arquivo
--   3. Clique em RUN
--   4. Confira a saída do último SELECT — todos devem aparecer como "OK"
-- ════════════════════════════════════════════════════════════════

begin;

-- ─── 1) PRÉVIA: mostra quais linhas serão tocadas ───────────────
select
  id,
  length(valor)                 as tamanho_atual,
  updated_at                    as ultima_atualizacao,
  position('INÍCIO DA LETRA' in valor) as posicao_marcador_antigo
from public.landing_content
where id in (
  'contrato_edicao_template',
  'contrato_edicao_publisher_template'
)
  and valor ~ 'INÍCIO DA LETRA|FIM DA LETRA';


-- ─── 2) UPDATE: troca os marcadores antigos pelos novos ─────────
-- A ordem dos replaces é importante: a versão mais longa
-- ("…DA LETRA DA OBRA") tem que ser trocada ANTES da curta
-- ("…DA LETRA"), senão o resultado fica duplicado ("DA OBRA DA OBRA").
update public.landing_content
set
  valor = replace(
            replace(
              replace(
                replace(
                  valor,
                  'INÍCIO DA LETRA DA OBRA', 'CORPO DA OBRA'
                ),
                'FIM DA LETRA DA OBRA',     'FIM DO CORPO DA OBRA'
              ),
              'INÍCIO DA LETRA',            'CORPO DA OBRA'
            ),
            'FIM DA LETRA',                 'FIM DO CORPO DA OBRA'
          ),
  updated_at = now()
where id in (
  'contrato_edicao_template',
  'contrato_edicao_publisher_template'
)
  and valor ~ 'INÍCIO DA LETRA|FIM DA LETRA';


-- ─── 3) VERIFICAÇÃO FINAL ───────────────────────────────────────
select
  id,
  case
    when valor ~ 'INÍCIO DA LETRA|FIM DA LETRA'
      then '❌ AINDA TEM MARCADOR ANTIGO'
    when valor like '%CORPO DA OBRA%'
      then '✓ OK — marcador novo presente'
    else
      '⚠ chave não tem nenhum dos marcadores'
  end as status,
  updated_at
from public.landing_content
where id in (
  'contrato_edicao_template',
  'contrato_edicao_publisher_template'
);

commit;

-- ════════════════════════════════════════════════════════════════
-- Caso queira REVERTER (rollback manual após o commit):
--
-- update public.landing_content
-- set valor = replace(
--               replace(valor, 'CORPO DA OBRA',          'INÍCIO DA LETRA'),
--                              'FIM DO CORPO DA OBRA',   'FIM DA LETRA'
--             )
-- where id in (
--   'contrato_edicao_template',
--   'contrato_edicao_publisher_template'
-- );
-- ════════════════════════════════════════════════════════════════
