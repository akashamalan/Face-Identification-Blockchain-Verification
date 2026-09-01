"""API endpoint tests using FastAPI TestClient."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("ok", "degraded")
        assert "services" in data

    def test_preflight_returns_200(self, client):
        resp = client.get("/api/preflight")
        assert resp.status_code == 200
        data = resp.json()
        assert "checks" in data
        assert "ready" in data


class TestFaceEndpoint:
    def test_no_file_returns_error(self, client):
        resp = client.post("/api/face/detect")
        assert resp.status_code == 422  # FastAPI validation error

    def test_empty_file_returns_error(self, client):
        resp = client.post(
            "/api/face/detect",
            files={"file": ("empty.jpg", b"", "image/jpeg")},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["success"] is False

    def test_invalid_extension_returns_error(self, client):
        resp = client.post(
            "/api/face/detect",
            files={"file": ("test.txt", b"not an image", "text/plain")},
        )
        assert resp.status_code == 400


class TestPipelineEndpoint:
    def test_no_file_returns_422(self, client):
        resp = client.post("/api/pipeline/run")
        assert resp.status_code == 422

    def test_empty_file_returns_400(self, client):
        resp = client.post(
            "/api/pipeline/run",
            files={"file": ("empty.jpg", b"", "image/jpeg")},
        )
        assert resp.status_code == 400
