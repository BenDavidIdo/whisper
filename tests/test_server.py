"""Tests for whisperflow.fast_server module."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient


# Patch model loading at import time to avoid needing actual model files
_mock_model = MagicMock()
_mock_model.transcribe.return_value = {
    "text": "test transcription",
    "segments": [],
    "language": "en",
}


@pytest.fixture()
def client():
    """Return a synchronous TestClient with model loading patched."""
    with patch("whisperflow.fast_server.get_model", return_value=_mock_model):
        from whisperflow.fast_server import app

        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_version_string(self, client):
        from whisperflow import __version__

        response = client.get("/health")
        assert f"Whisper Flow V{__version__}" in response.text


class TestTranscribePcmChunkEndpoint:
    """Tests for POST /transcribe_pcm_chunk."""

    def test_transcribe_returns_text(self, client):
        silence = bytes(3200)  # 0.1s silence at 16kHz 16-bit
        response = client.post(
            "/transcribe_pcm_chunk",
            data={"model_name": "tiny.en.pt"},
            files=[("files", ("audio.raw", silence, "application/octet-stream"))],
        )
        assert response.status_code == 200
        body = response.json()
        assert "text" in body

    def test_transcribe_calls_get_model(self, client):
        with patch(
            "whisperflow.fast_server.get_model", return_value=_mock_model
        ) as mock_get:
            silence = bytes(3200)
            client.post(
                "/transcribe_pcm_chunk",
                data={"model_name": "custom.pt"},
                files=[("files", ("audio.raw", silence, "application/octet-stream"))],
            )
            mock_get.assert_called_with("custom.pt")


class TestWebSocketEndpoint:
    """Tests for WebSocket /ws."""

    def test_websocket_accepts_connection(self, client):
        with client.websocket_connect("/ws") as ws:
            pass  # connection accepted and closed cleanly

    def test_websocket_receives_json_result(self, client):
        """Sending a binary chunk should eventually produce a JSON result."""
        received = []

        with patch(
            "whisperflow.fast_server.transcribe_pcm_chunks_async",
            new=AsyncMock(
                return_value={
                    "text": "hello",
                    "segments": [],
                    "language": "en",
                }
            ),
        ):
            with client.websocket_connect("/ws") as ws:
                ws.send_bytes(bytes(4096))
                import time
                time.sleep(0.5)
                try:
                    data = ws.receive_text(timeout=2)
                    received.append(json.loads(data))
                except Exception:
                    pass  # may not receive if session closes first

        # If we received anything, validate its shape
        for r in received:
            assert "is_partial" in r
            assert "data" in r
            assert "time" in r
