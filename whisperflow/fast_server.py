"""FastAPI server exposing health, batch transcription, and WebSocket endpoints."""

import json
import logging

from fastapi import FastAPI, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse

from whisperflow import __version__
from whisperflow.transcriber import get_model, transcribe_pcm_chunks, transcribe_pcm_chunks_async
from whisperflow.streaming import TranscribeSession

logger = logging.getLogger(__name__)

app = FastAPI(title="Whisper Flow", version=__version__)

# In-memory session registry {session_id: TranscribeSession}
sessions = {}


@app.get("/health", response_class=PlainTextResponse)
async def health():
    """Return service version string.

    Returns:
        Plain-text version identifier, e.g. "Whisper Flow V1.1.0".
    """
    return f"Whisper Flow V{__version__}"


@app.post("/transcribe_pcm_chunk")
async def transcribe_pcm_chunk(model_name: str, files: list[UploadFile]):
    """Transcribe uploaded PCM audio bytes using the specified model.

    Args:
        model_name: Filename of the model inside whisperflow/models/.
        files: List of uploaded audio files (uses first file only).

    Returns:
        Transcription result dict with 'text', 'segments', and 'language'.
    """
    model = get_model(model_name)
    content = files[0].file.read()
    result = transcribe_pcm_chunks(model, [content])
    return result


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Stream real-time transcription results over a WebSocket connection.

    Accepts binary PCM audio chunks from the client, transcribes them using
    the tumbling window algorithm, and sends back JSON result objects.

    Client sends: raw PCM bytes (16kHz, 16-bit signed, mono)
    Server sends: JSON {"is_partial": bool, "data": {...}, "time": float}
    """
    await websocket.accept()

    model = get_model("tiny.en.pt")

    async def transcribe_async(chunks):
        return await transcribe_pcm_chunks_async(model, chunks)

    async def send_back_async(result):
        await websocket.send_text(json.dumps(result))

    session = TranscribeSession(transcribe_async, send_back_async)
    sessions[str(session.id)] = session

    try:
        while True:
            data = await websocket.receive_bytes()
            session.add_chunk(data)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected (session %s)", session.id)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("WebSocket error (session %s): %s", session.id, exc)
        await websocket.close()
    finally:
        await session.stop()
        sessions.pop(str(session.id), None)


def main():
    """Entry point: start the Uvicorn server on port 8181."""
    import uvicorn  # pylint: disable=import-outside-toplevel

    uvicorn.run(app, host="0.0.0.0", port=8181)


if __name__ == "__main__":
    main()
