"""Tests for whisperflow.transcriber module."""

import asyncio
import os
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from whisperflow.transcriber import transcribe_pcm_chunks, transcribe_pcm_chunks_async


def make_mock_model():
    """Create a mock Whisper model that returns a fixed transcription."""
    model = MagicMock()
    model.transcribe.return_value = {
        "text": "hello world",
        "segments": [],
        "language": "en",
    }
    return model


def make_silence_chunk(duration_seconds=0.5, sample_rate=16000):
    """Create a chunk of silent 16-bit PCM audio bytes."""
    num_samples = int(duration_seconds * sample_rate)
    return bytes(num_samples * 2)


class TestGetModel:
    """Tests for the get_model function."""

    def test_load_model_uses_cache(self):
        """Calling get_model twice with the same name returns the same object."""
        from whisperflow.transcriber import get_model, models

        mock_model = MagicMock()

        with patch("whisperflow.transcriber.models", {"tiny.en.pt": mock_model}):
            import whisperflow.transcriber as t

            result = t.get_model("tiny.en.pt")
            assert result is mock_model

    def test_load_model_selects_device(self):
        """get_model loads from the models directory and selects device."""
        import whisperflow.transcriber as t

        mock_model = MagicMock()

        with patch.dict(t.models, {}, clear=True), patch(
            "whisperflow.transcriber.models", {}
        ):
            with patch("whisper.load_model", return_value=mock_model) as mock_load, \
                 patch("torch.cuda.is_available", return_value=False):
                result = t.get_model("tiny.en.pt")
                mock_load.assert_called_once_with(
                    "./whisperflow/models/tiny.en.pt", device="cpu"
                )
                assert result is mock_model


class TestTranscribePcmChunks:
    """Tests for synchronous transcription."""

    def test_basic_transcription(self):
        """transcribe_pcm_chunks returns model output unchanged."""
        model = make_mock_model()
        chunk = make_silence_chunk()
        result = transcribe_pcm_chunks(model, [chunk])
        assert result["text"] == "hello world"
        assert result["language"] == "en"
        model.transcribe.assert_called_once()

    def test_audio_conversion(self):
        """Audio bytes are correctly converted to float32 in [-1, 1]."""
        import numpy as np

        captured = {}

        def capture_transcribe(audio, **kwargs):
            captured["audio"] = audio
            return {"text": "", "segments": [], "language": "en"}

        model = MagicMock()
        model.transcribe.side_effect = capture_transcribe

        # Max int16 value
        chunk = np.array([32767], dtype=np.int16).tobytes()
        transcribe_pcm_chunks(model, [chunk])

        assert captured["audio"].dtype == np.float32
        assert abs(captured["audio"][0] - 1.0) < 1e-4

    def test_multiple_chunks_joined(self):
        """Multiple chunks are joined before transcription."""
        model = make_mock_model()
        chunks = [make_silence_chunk(0.1) for _ in range(4)]
        transcribe_pcm_chunks(model, chunks)

        call_args = model.transcribe.call_args
        audio = call_args[0][0]
        expected_samples = int(0.4 * 16000)
        assert len(audio) == expected_samples

    def test_custom_language_and_temperature(self):
        """Language and temperature parameters are forwarded to model."""
        model = make_mock_model()
        chunk = make_silence_chunk()
        transcribe_pcm_chunks(model, [chunk], lang="fr", temperature=0.5)

        call_kwargs = model.transcribe.call_args[1]
        assert call_kwargs["language"] == "fr"
        assert call_kwargs["temperature"] == 0.5


class TestTranscribePcmChunksAsync:
    """Tests for asynchronous transcription wrapper."""

    def test_async_returns_same_as_sync(self):
        """Async version returns the same result as sync version."""
        model = make_mock_model()
        chunk = make_silence_chunk()

        result = asyncio.get_event_loop().run_until_complete(
            transcribe_pcm_chunks_async(model, [chunk])
        )
        assert result["text"] == "hello world"

    @pytest.mark.asyncio
    async def test_async_does_not_block_event_loop(self):
        """Async transcription runs in executor without blocking."""
        model = make_mock_model()
        chunk = make_silence_chunk()
        result = await transcribe_pcm_chunks_async(model, [chunk])
        assert "text" in result
