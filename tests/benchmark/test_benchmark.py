"""Performance benchmarks for whisperflow.

Run with: pytest tests/benchmark/ --benchmark-only
"""

import json
import os
import time
import wave

import pytest

RESOURCES_DIR = os.path.join(os.path.dirname(__file__), "..", "resources")
TEST_WAV_PATH = os.path.join(RESOURCES_DIR, "3081-166546-0000.wav")
TEST_JSON_PATH = os.path.join(RESOURCES_DIR, "3081-166546-0000.json")
SERVER_URL = "http://localhost:8181"
WS_URL = "ws://localhost:8181/ws"
CHUNK_SIZE = 4096


def _read_wav_chunks(path=TEST_WAV_PATH, chunk_size=CHUNK_SIZE):
    with wave.open(path, "rb") as wf:
        data = wf.readframes(wf.getnframes())
    return [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]


@pytest.fixture(scope="module")
def server_available():
    """Skip benchmark tests if the server is not running."""
    import httpx  # pylint: disable=import-outside-toplevel

    try:
        resp = httpx.get(f"{SERVER_URL}/health", timeout=2)
        if resp.status_code != 200:
            pytest.skip("Whisper Flow server not available")
    except Exception:  # pylint: disable=broad-except
        pytest.skip("Whisper Flow server not available")


def test_health(benchmark, server_available):
    """Benchmark health endpoint latency."""
    import httpx  # pylint: disable=import-outside-toplevel

    def call_health():
        return httpx.get(f"{SERVER_URL}/health", timeout=5)

    result = benchmark(call_health)
    assert result.status_code == 200


def test_send_chunks(server_available):
    """Benchmark full streaming pipeline: WER < 10%, report latency stats."""
    import websocket  # pylint: disable=import-outside-toplevel

    if not os.path.exists(TEST_WAV_PATH):
        pytest.skip("Test audio file not available")

    chunks = _read_wav_chunks()
    results = []
    latencies = []

    ws = websocket.WebSocket()
    ws.connect(WS_URL)

    for chunk in chunks:
        ws.send_binary(chunk)

    # Collect responses with timeout
    ws.settimeout(5.0)
    start = time.time()
    while time.time() - start < 10.0:
        try:
            msg = ws.recv()
            data = json.loads(msg)
            results.append(data)
            latencies.append(data.get("time", 0))
            if not data.get("is_partial", True):
                break
        except Exception:  # pylint: disable=broad-except
            break

    ws.close()

    if not results:
        pytest.skip("No results received from server")

    # Latency statistics
    if latencies:
        mean_latency = sum(latencies) / len(latencies)
        print(f"\nMean latency: {mean_latency:.1f}ms")
        print(f"Min latency: {min(latencies):.1f}ms")
        print(f"Max latency: {max(latencies):.1f}ms")

    # WER validation (if reference exists)
    if os.path.exists(TEST_JSON_PATH):
        with open(TEST_JSON_PATH, encoding="utf-8") as f:
            reference = json.load(f)

        from jiwer import wer  # pylint: disable=import-outside-toplevel

        final = next((r for r in reversed(results) if not r.get("is_partial")), None)
        if final:
            hypothesis = final["data"].get("text", "").strip()
            reference_text = reference.get("text", "").strip()
            error_rate = wer(reference_text, hypothesis)
            print(f"WER: {error_rate:.2%}")
            assert error_rate < 0.10, f"WER {error_rate:.2%} exceeds 10% threshold"
