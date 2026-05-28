"""
Integration tests for the Likes service (gateway REST API).
Run with:
    pytest tests/ -v
The gateway must be accessible at GATEWAY_URL (default http://localhost:8154).
"""

import os
import pytest
import httpx

BASE = os.getenv("GATEWAY_URL", "http://localhost:8154")


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=BASE, timeout=10) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_like(client):
    r = client.post("/api/likes", json={"target": "post-42"})
    assert r.status_code == 201
    body = r.json()
    assert body["target"] == "post-42"
    assert "id" in body


def test_list_likes(client):
    client.post("/api/likes", json={"target": "list-test"})
    r = client.get("/api/likes")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1


def test_get_like(client):
    created = client.post("/api/likes", json={"target": "get-test"}).json()
    like_id = created["id"]
    r = client.get(f"/api/likes/{like_id}")
    assert r.status_code == 200
    assert r.json()["id"] == like_id
    assert r.json()["target"] == "get-test"


def test_get_like_not_found(client):
    r = client.get("/api/likes/999999")
    assert r.status_code == 404


def test_delete_like(client):
    created = client.post("/api/likes", json={"target": "delete-test"}).json()
    like_id = created["id"]
    r = client.delete(f"/api/likes/{like_id}")
    assert r.status_code == 204
    r2 = client.delete(f"/api/likes/{like_id}")
    assert r2.status_code == 404