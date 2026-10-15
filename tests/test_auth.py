import os
import sys

# Ensure root directory is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_login_success_admin():
    """Verify dispatcher_admin login returns 200, JWT access token, and user profile."""
    payload = {
        "username": "dispatcher_admin",
        "password": "emergency2026!"
    }
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"
    assert data["user"]["username"] == "dispatcher_admin"
    assert data["user"]["role"] == "Chief Dispatch Supervisor"
    assert data["user"]["dispatcher_id"] == "CAD-911-01"
    assert "dispatch" in data["user"]["permissions"]

def test_login_success_paramedic():
    """Verify paramedic_user login returns 200, JWT access token, and user profile."""
    payload = {
        "username": "paramedic_user",
        "password": "medic123"
    }
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert data["user"]["username"] == "paramedic_user"
    assert data["user"]["role"] == "Field Triage Paramedic"

def test_login_invalid_password():
    """Verify incorrect password returns 401 Unauthorized."""
    payload = {
        "username": "dispatcher_admin",
        "password": "wrongpassword"
    }
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 401
    data = response.json()
    assert "Invalid dispatcher credentials" in data["detail"]

def test_login_nonexistent_user():
    """Verify non-existent username returns 401 Unauthorized."""
    payload = {
        "username": "unknown_intruder",
        "password": "password123"
    }
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 401
    data = response.json()
    assert "Invalid dispatcher credentials" in data["detail"]

def test_auth_me_with_valid_token():
    """Verify GET /auth/me with valid bearer token returns user profile."""
    # First log in to obtain token
    login_res = client.post("/auth/login", json={
        "username": "dispatcher_admin",
        "password": "emergency2026!"
    })
    token = login_res.json()["access_token"]

    # Verify session
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/auth/me", headers=headers)
    assert me_res.status_code == 200
    data = me_res.json()
    assert data["valid"] is True
    assert data["user"]["username"] == "dispatcher_admin"

def test_auth_me_without_token():
    """Verify GET /auth/me without token returns 401."""
    res = client.get("/auth/me")
    assert res.status_code == 401

def test_auth_me_with_invalid_token():
    """Verify GET /auth/me with bogus token returns 401."""
    headers = {"Authorization": "Bearer invalid.bogus.jwt.token"}
    res = client.get("/auth/me", headers=headers)
    assert res.status_code == 401
