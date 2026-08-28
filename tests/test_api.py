from fastapi.testclient import TestClient

from api.index import app
from weather_api import CITIES, normalize_city

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_cities():
    response = client.get("/api/cities")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == len(CITIES)
    assert data["count"] >= 150
    assert {"label": "Cape Town, South Africa"} in data["cities"]
    assert {"label": "Tokyo, Japan"} in data["cities"]


def test_weather_requires_city():
    response = client.get("/api/weather")
    assert response.status_code == 422


def test_normalize_city():
    assert normalize_city("  Cape   Town  ") == "Cape Town"
