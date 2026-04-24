"""
Backend smoke + stats tests for Gravan
Run: pytest /app/backend/tests/test_backend.py -v --junitxml=/app/test_reports/pytest/pytest_results.xml
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://3207e26c-d880-4300-b9d3-87ec9502829f.preview.emergentagent.com").rstrip("/")


@pytest.fixture
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ─── Health ───────────────────────────────────────
class TestHealth:
    def test_health(self, client):
        r = client.get(f"{BASE_URL}/api/health", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "healthy"


# ─── Public stats (Landing) ───────────────────────
class TestPublicStats:
    def test_stats_status_and_shape(self, client):
        r = client.get(f"{BASE_URL}/api/catalogo/stats/public", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert set(data.keys()) >= {"obras", "compositores", "total_pago"}
        assert isinstance(data["obras"], int)
        assert isinstance(data["compositores"], int)
        assert isinstance(data["total_pago"], (int, float))

    def test_stats_no_auth_required(self, client):
        # no Authorization header
        r = requests.get(f"{BASE_URL}/api/catalogo/stats/public", timeout=15)
        assert r.status_code == 200

    def test_stats_matches_list_count(self, client):
        """Bug check: /stats/public must reflect real DB numbers, not 0."""
        stats = client.get(f"{BASE_URL}/api/catalogo/stats/public", timeout=15).json()
        listing = client.get(f"{BASE_URL}/api/catalogo/?per_page=50", timeout=15).json()
        assert isinstance(listing, list)
        # If there are obras in the listing, stats.obras must not be 0
        if len(listing) > 0:
            assert stats["obras"] >= len(listing), (
                f"Stats says {stats['obras']} obras but listing has {len(listing)}"
            )


# ─── Catalogo list ────────────────────────────────
class TestCatalogo:
    def test_listar(self, client):
        r = client.get(f"{BASE_URL}/api/catalogo/?per_page=5", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_detalhe_404(self, client):
        r = client.get(f"{BASE_URL}/api/catalogo/00000000-0000-0000-0000-000000000000", timeout=15)
        assert r.status_code in (404, 406)  # supabase .single() can 406 when not found


# ─── Protected routes ─────────────────────────────
class TestAuthProtection:
    def test_ofertas_recebidas_requires_auth(self, client):
        r = client.get(f"{BASE_URL}/api/catalogo/ofertas/recebidas", timeout=15)
        assert r.status_code == 401

    def test_ofertas_enviadas_requires_auth(self, client):
        r = client.get(f"{BASE_URL}/api/catalogo/ofertas/enviadas", timeout=15)
        assert r.status_code == 401


# ─── Static asset ─────────────────────────────────
class TestStatic:
    def test_zip_available(self, client):
        r = client.head(f"{BASE_URL}/gravan_completo.zip", timeout=15, allow_redirects=True)
        assert r.status_code == 200


# ─── CORS ─────────────────────────────────────────
class TestCORS:
    def test_cors_allowed_origin(self, client):
        r = client.options(
            f"{BASE_URL}/api/health",
            headers={
                "Origin": "https://3207e26c-d880-4300-b9d3-87ec9502829f.preview.emergentagent.com",
                "Access-Control-Request-Method": "GET",
            },
            timeout=15,
        )
        assert r.status_code in (200, 204)
