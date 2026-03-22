"""Transcriber module: model loading and audio inference."""

import asyncio
import os

import numpy as np

models = {}


def get_model(file_name="tiny.en.pt"):
    """Load and cache a Whisper model by filename.

    Args:
        file_name: Model filename inside whisperflow/models/.

    Returns:
        Loaded Whisper model instance.
    """
    import whisper
    import torch

    if file_name not in models:
        models_dir = os.environ.get('WHISPERFLOW_MODELS_DIR', './whisperflow/models')
        model_path = os.path.join(models_dir, file_name)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        models[file_name] = whisper.load_model(model_path, device=device)
    return models[file_name]


def transcribe_pcm_chunks(model, chunks, lang="en", temperature=0.1, log_prob=-0.5):
    """Transcribe a list of PCM byte chunks using a Whisper model.

    Args:
        model: Loaded Whisper model.
        chunks: List of bytes objects containing 16-bit signed PCM audio.
        lang: Language code for transcription.
        temperature: Sampling temperature (lower = more deterministic).
        log_prob: Log-probability threshold for confidence filtering.

    Returns:
        Dict with 'text', 'segments', and 'language' keys.
    """
    audio_bytes = b"".join(chunks)
    audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
    audio_array = audio_array / 32768.0

    result = model.transcribe(
        audio_array,
        fp16=False,
        language=lang,
        logprob_threshold=log_prob,
        temperature=temperature,
    )
    return result


async def transcribe_pcm_chunks_async(
    model, chunks, lang="en", temperature=0.1, log_prob=-0.5
):
    """Async wrapper for transcribe_pcm_chunks using a thread executor.

    Args:
        model: Loaded Whisper model.
        chunks: List of bytes objects containing 16-bit signed PCM audio.
        lang: Language code for transcription.
        temperature: Sampling temperature.
        log_prob: Log-probability threshold.

    Returns:
        Dict with transcription result.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        lambda: transcribe_pcm_chunks(model, chunks, lang, temperature, log_prob),
    )
