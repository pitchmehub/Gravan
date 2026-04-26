"""
Gravan — Watchdog de saúde do backend.

Monitora /api/health a cada 30 segundos.
Após 3 falhas consecutivas:
  1. Envia alerta ao Sentry
  2. Mata qualquer processo preso na porta 8000
  3. Reinicia o gunicorn como processo independente
  4. Confirma que voltou a responder
"""
import logging
import os
import signal
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [watchdog] %(levelname)s: %(message)s",
)
logger = logging.getLogger("watchdog")

HEALTH_URL        = os.getenv("WATCHDOG_URL", "http://127.0.0.1:8000/api/health")
CHECK_INTERVAL    = int(os.getenv("WATCHDOG_INTERVAL", "30"))   # segundos entre checks
MAX_FAILURES      = int(os.getenv("WATCHDOG_MAX_FAILURES", "3"))# falhas antes de reiniciar
STARTUP_WAIT      = int(os.getenv("WATCHDOG_STARTUP_WAIT", "20"))# segundos para o gunicorn subir
BACKEND_PORT      = int(os.getenv("WATCHDOG_PORT", "8000"))
DUNNING_INTERVAL  = int(os.getenv("WATCHDOG_DUNNING_INTERVAL", "3600"))  # segundos entre rodadas de dunning
BACKEND_DIR       = os.path.dirname(os.path.abspath(__file__))
GUNICORN_CMD      = [
    sys.executable, "-m", "gunicorn",
    "--bind", f"0.0.0.0:{BACKEND_PORT}",
    "--workers", "2",
    "--reuse-port",
    "--capture-output",
    "--log-level", "info",
    "app:create_app()",
]


def _sentry_alert(title: str, message: str, level: str = "warning") -> None:
    try:
        import sentry_sdk
        dsn = os.getenv("SENTRY_DSN_BACKEND")
        if not dsn:
            return
        if not sentry_sdk.is_initialized():
            sentry_sdk.init(dsn=dsn, environment=os.getenv("FLASK_ENV", "development"))
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "watchdog")
            scope.set_extra("health_url", HEALTH_URL)
            scope.set_extra("timestamp", datetime.utcnow().isoformat())
            sentry_sdk.capture_message(f"[Watchdog] {title}: {message}", level=level)
        logger.info("Alerta enviado ao Sentry: %s", title)
    except Exception as e:
        logger.warning("Falha ao enviar alerta Sentry: %s", e)


def _ping() -> bool:
    try:
        req = Request(HEALTH_URL, headers={"User-Agent": "gravan-watchdog/1.0"})
        with urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception:
        return False


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def _kill_port(port: int) -> None:
    logger.info("Matando processos na porta %s...", port)
    try:
        result = subprocess.run(
            ["fuser", "-k", f"{port}/tcp"],
            capture_output=True, timeout=10,
        )
        time.sleep(2)
        logger.info("fuser retornou %s", result.returncode)
    except Exception as e:
        logger.warning("fuser falhou: %s — tentando via lsof", e)
        try:
            out = subprocess.check_output(
                ["lsof", "-ti", f":{port}"], text=True
            ).strip()
            for pid in out.splitlines():
                try:
                    os.kill(int(pid), signal.SIGTERM)
                except Exception:
                    pass
            time.sleep(2)
        except Exception as e2:
            logger.warning("lsof também falhou: %s", e2)


def _start_gunicorn() -> None:
    logger.info("Iniciando gunicorn: %s", " ".join(GUNICORN_CMD))
    subprocess.Popen(
        GUNICORN_CMD,
        cwd=BACKEND_DIR,
        preexec_fn=os.setsid,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _run_dunning() -> None:
    """
    Dispara em subprocesso a rotina de dunning (cancela PRO em past_due > 7d).
    Isolado para não derrubar o watchdog se algo falhar.
    """
    logger.info("Rodando dunning de assinaturas em atraso...")
    try:
        result = subprocess.run(
            [
                sys.executable, "-c",
                "from services.subscription import expirar_assinaturas_em_atraso;"
                "import json, sys;"
                "sys.stdout.write(json.dumps(expirar_assinaturas_em_atraso()))",
            ],
            cwd=BACKEND_DIR,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            logger.info("Dunning OK: %s", (result.stdout or "").strip())
        else:
            logger.warning(
                "Dunning falhou (rc=%s): %s",
                result.returncode, (result.stderr or "").strip()[:500],
            )
    except subprocess.TimeoutExpired:
        logger.warning("Dunning excedeu timeout de 120s — abortado.")
    except Exception as e:
        logger.warning("Dunning erro inesperado: %s", e)


def _restart_backend(reason: str) -> None:
    logger.error("REINICIANDO backend. Motivo: %s", reason)
    _sentry_alert(
        "Backend reiniciado automaticamente",
        reason,
        level="error",
    )
    _kill_port(BACKEND_PORT)
    _start_gunicorn()

    logger.info("Aguardando %ss para o backend subir...", STARTUP_WAIT)
    deadline = time.time() + STARTUP_WAIT
    while time.time() < deadline:
        time.sleep(3)
        if _ping():
            elapsed = round(STARTUP_WAIT - (deadline - time.time()), 1)
            logger.info("Backend voltou em ~%ss", elapsed)
            _sentry_alert(
                "Backend recuperado",
                f"Reiniciado com sucesso após: {reason}",
                level="info",
            )
            return
    logger.error("Backend NÃO respondeu após %ss — próxima tentativa em breve.", STARTUP_WAIT)


def main() -> None:
    logger.info(
        "Watchdog iniciado | url=%s intervalo=%ss max_falhas=%s dunning=%ss",
        HEALTH_URL, CHECK_INTERVAL, MAX_FAILURES, DUNNING_INTERVAL,
    )
    consecutive_failures = 0
    last_dunning_run = 0.0  # epoch da última rodada de dunning

    # Aguarda o backend subir pela primeira vez
    logger.info("Aguardando backend ficar disponível...")
    for _ in range(20):
        if _ping():
            logger.info("Backend disponível. Monitoramento ativo.")
            break
        time.sleep(3)
    else:
        logger.warning("Backend não respondeu na inicialização — monitoramento continua.")

    while True:
        time.sleep(CHECK_INTERVAL)

        if _ping():
            if consecutive_failures > 0:
                logger.info("Backend OK (estava com %s falha(s))", consecutive_failures)
            consecutive_failures = 0
            logger.debug("Health check OK")

            # Tick de dunning — só roda quando backend está saudável
            now = time.time()
            if DUNNING_INTERVAL > 0 and (now - last_dunning_run) >= DUNNING_INTERVAL:
                last_dunning_run = now
                _run_dunning()
            continue

        consecutive_failures += 1
        logger.warning(
            "Health check FALHOU (%s/%s consecutivas)", consecutive_failures, MAX_FAILURES
        )

        if consecutive_failures >= MAX_FAILURES:
            _restart_backend(
                f"{consecutive_failures} health checks consecutivos falharam em {HEALTH_URL}"
            )
            consecutive_failures = 0


if __name__ == "__main__":
    main()
