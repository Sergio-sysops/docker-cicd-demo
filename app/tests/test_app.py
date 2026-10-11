"""Integration tests: they need a running PostgreSQL (see DATABASE_URL).

In CI, GitHub Actions starts a postgres service container for them.
Locally: docker compose up -d db, then run pytest with DATABASE_URL set.
"""
import pytest

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["db"] == "up"


def test_index_counts_visits(client):
    first = client.get("/").get_data(as_text=True)
    second = client.get("/").get_data(as_text=True)
    assert "It works" in first
    assert first != second  # the counter went up


def test_create_and_list_notes(client):
    res = client.post("/api/notes", json={"text": "hello from the tests"})
    assert res.status_code == 201
    notes = client.get("/api/notes").get_json()
    assert any(n["text"] == "hello from the tests" for n in notes)


@pytest.mark.parametrize("payload", [{}, {"text": ""}, {"text": "x" * 501}])
def test_rejects_invalid_notes(client, payload):
    assert client.post("/api/notes", json=payload).status_code == 400
