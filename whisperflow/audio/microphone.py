"""Microphone module: real-time audio capture and playback via PyAudio."""

import asyncio
import numpy as np


SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_FRAMES = 1024
AUDIO_FORMAT = None  # Set at runtime from pyaudio constants


def _get_pyaudio():
    """Import PyAudio lazily to avoid import errors when not installed."""
    import pyaudio  # pylint: disable=import-outside-toplevel

    return pyaudio


def is_silent(data, silence_threshold=500):
    """Determine whether an audio chunk is silent.

    Args:
        data: Raw PCM bytes (16-bit signed integers).
        silence_threshold: Peak amplitude below this value is considered silent.

    Returns:
        True if the chunk is silent, False otherwise.
    """
    array = np.frombuffer(data, dtype=np.int16)
    return int(np.max(np.abs(array))) < silence_threshold


async def capture_audio(queue_chunks, stop_event):
    """Continuously capture microphone audio and enqueue chunks.

    Reads 1024-frame chunks from the default input device at 16kHz mono
    and puts them onto queue_chunks until stop_event is set.

    Args:
        queue_chunks: asyncio.Queue to receive captured PCM bytes.
        stop_event: asyncio.Event that signals capture to stop.
    """
    pyaudio = _get_pyaudio()
    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK_FRAMES,
    )

    try:
        while not stop_event.is_set():
            data = stream.read(CHUNK_FRAMES, exception_on_overflow=False)
            queue_chunks.put_nowait(data)
            await asyncio.sleep(0.001)
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()


async def play_audio(queue_chunks, stop_event):
    """Continuously read audio chunks from a queue and play them back.

    Writes PCM bytes to the default output device at 16kHz mono
    until stop_event is set.

    Args:
        queue_chunks: asyncio.Queue supplying PCM bytes to play.
        stop_event: asyncio.Event that signals playback to stop.
    """
    pyaudio = _get_pyaudio()
    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        output=True,
        frames_per_buffer=CHUNK_FRAMES,
    )

    try:
        while not stop_event.is_set():
            if not queue_chunks.empty():
                data = await queue_chunks.get()
                stream.write(data)
            await asyncio.sleep(0.001)
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()
