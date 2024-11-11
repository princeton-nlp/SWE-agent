from __future__ import annotations

import pytest
from flask_socketio import SocketIOTestClient

from sweagent.api.server import app, socketio


@pytest.fixture
def client():
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture
def socket_client():
    client = SocketIOTestClient(app, socketio)
    yield client
    client.disconnect()


def test_index(client):
    """Test the index page"""
    response = client.get("/")
    assert response.status_code == 200


def test_run_options(client):
    """Test the /run endpoint OPTIONS method for CORS preflight"""
    response = client.open("/run", method="OPTIONS")
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "*"


def test_stop(client):
    """Test the /stop endpoint"""
    response = client.get("/stop")
    assert response.status_code == 202
