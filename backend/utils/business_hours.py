"""
Cálculo de horas úteis em horário comercial brasileiro.

Regra (spec):
- Horário comercial: segunda a sexta, das 10h às 18h (BRT, UTC-3, sem DST).
- Excluem-se sábados, domingos e feriados nacionais brasileiros.
- "72 horas úteis" = 72 horas dentro dessa janela (9 dias úteis × 8h).

Uso:
    from utils.business_hours import add_business_hours, is_business_now
    deadline = add_business_hours(datetime.utcnow(), hours=72)
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone, date

# BRT = UTC-3, sem horário de verão desde 2019.
BRT = timezone(timedelta(hours=-3))

OPEN_HOUR  = 10
CLOSE_HOUR = 18
HOURS_PER_DAY = CLOSE_HOUR - OPEN_HOUR  # 8


def _easter(year: int) -> date:
    """Algoritmo de Anonymous Gregorian (Meeus/Jones/Butcher)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    L = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * L) // 451
    month = (h + L - 7 * m + 114) // 31
    day = ((h + L - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def br_holidays(year: int) -> set[date]:
    """Feriados nacionais brasileiros (fixos + móveis baseados na Páscoa)."""
    fixed = {
        date(year, 1, 1),    # Confraternização Universal
        date(year, 4, 21),   # Tiradentes
        date(year, 5, 1),    # Dia do Trabalho
        date(year, 9, 7),    # Independência
        date(year, 10, 12),  # N. Sra. Aparecida
        date(year, 11, 2),   # Finados
        date(year, 11, 15),  # Proclamação da República
        date(year, 11, 20),  # Consciência Negra (federal a partir de 2024)
        date(year, 12, 25),  # Natal
    }
    e = _easter(year)
    movable = {
        e - timedelta(days=48),  # Carnaval segunda
        e - timedelta(days=47),  # Carnaval terça
        e - timedelta(days=2),   # Sexta-feira Santa
        e + timedelta(days=60),  # Corpus Christi
    }
    return fixed | movable


def is_business_day(d: date) -> bool:
    return d.weekday() < 5 and d not in br_holidays(d.year)


def is_business_now(now_utc: datetime | None = None) -> bool:
    now = (now_utc or datetime.now(timezone.utc)).astimezone(BRT)
    if not is_business_day(now.date()):
        return False
    return OPEN_HOUR <= now.hour < CLOSE_HOUR


def _next_business_open(local: datetime) -> datetime:
    """Avança para o próximo instante de abertura comercial."""
    cur = local
    # Se ainda não abriu hoje, abre hoje (se for dia útil)
    if is_business_day(cur.date()) and cur.hour < OPEN_HOUR:
        return cur.replace(hour=OPEN_HOUR, minute=0, second=0, microsecond=0)
    # Senão, anda dia a dia
    cur = (cur + timedelta(days=1)).replace(hour=OPEN_HOUR, minute=0, second=0, microsecond=0)
    while not is_business_day(cur.date()):
        cur += timedelta(days=1)
    return cur


def add_business_hours(start_utc: datetime, hours: float) -> datetime:
    """
    Soma `hours` horas COMERCIAIS a `start_utc` e devolve o deadline em UTC.

    Considera segunda a sexta, 10h–18h BRT, excluindo feriados nacionais.
    """
    if start_utc.tzinfo is None:
        start_utc = start_utc.replace(tzinfo=timezone.utc)
    cur = start_utc.astimezone(BRT)

    # Normaliza: se está fora do expediente, pula para o próximo open
    if not (is_business_day(cur.date()) and OPEN_HOUR <= cur.hour < CLOSE_HOUR):
        cur = _next_business_open(cur)

    remaining = timedelta(hours=hours)
    while remaining.total_seconds() > 0:
        close_today = cur.replace(hour=CLOSE_HOUR, minute=0, second=0, microsecond=0)
        bloco = close_today - cur
        if bloco >= remaining:
            cur = cur + remaining
            remaining = timedelta(0)
        else:
            remaining -= bloco
            cur = _next_business_open(close_today)

    return cur.astimezone(timezone.utc)


def business_hours_remaining(deadline_utc: datetime, now_utc: datetime | None = None) -> float:
    """
    Quantas horas COMERCIAIS faltam até `deadline_utc`. Retorna 0 se já passou.
    """
    now = now_utc or datetime.now(timezone.utc)
    if now >= deadline_utc:
        return 0.0
    cur = now.astimezone(BRT)
    end = deadline_utc.astimezone(BRT)
    if not (is_business_day(cur.date()) and OPEN_HOUR <= cur.hour < CLOSE_HOUR):
        cur = _next_business_open(cur)
    total = timedelta(0)
    while cur < end:
        close_today = cur.replace(hour=CLOSE_HOUR, minute=0, second=0, microsecond=0)
        chunk_end = min(close_today, end)
        total += (chunk_end - cur)
        if chunk_end >= end:
            break
        cur = _next_business_open(close_today)
    return round(total.total_seconds() / 3600.0, 2)
