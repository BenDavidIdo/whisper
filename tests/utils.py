"""Test utilities for whisperflow tests."""

import os
import struct
import wave


RESOURCES_DIR = os.path.join(os.path.dirname(__file__), "resources")
TEST_WAV_PATH = os.path.join(RESOURCES_DIR, "3081-166546-0000.wav")
TEST_JSON_PATH = os.path.join(RESOURCES_DIR, "3081-166546-0000.json")

SAMPLE_RATE = 16000
CHUNK_SIZE = 4096


def read_wav_chunks(wav_path=TEST_WAV_PATH, chunk_size=CHUNK_SIZE):
    """Read a WAV file and yield raw PCM byte chunks.

    Args:
        wav_path: Path to a 16kHz mono 16-bit WAV file.
        chunk_size: Number of bytes per chunk.

    Yields:
        bytes: Sequential PCM chunks of the specified size.
    """
    with wave.open(wav_path, "rb") as wf:
        data = wf.readframes(wf.getnframes())

    for i in range(0, len(data), chunk_size):
        yield data[i : i + chunk_size]


def generate_silence(duration_seconds=1.0, sample_rate=SAMPLE_RATE):
    """Generate silent PCM bytes.

    Args:
        duration_seconds: Duration of silence in seconds.
        sample_rate: Sample rate in Hz.

    Returns:
        bytes: Silent 16-bit PCM audio data.
    """
    num_samples = int(duration_seconds * sample_rate)
    return struct.pack(f"<{num_samples}h", *([0] * num_samples))


def generate_sine_wave(frequency=440.0, duration_seconds=1.0, sample_rate=SAMPLE_RATE):
    """Generate a sine wave as PCM bytes.

    Args:
        frequency: Frequency in Hz.
        duration_seconds: Duration in seconds.
        sample_rate: Sample rate in Hz.

    Returns:
        bytes: 16-bit signed PCM audio data.
    """
    import math

    num_samples = int(duration_seconds * sample_rate)
    samples = [
        int(32767 * math.sin(2 * math.pi * frequency * i / sample_rate))
        for i in range(num_samples)
    ]
    return struct.pack(f"<{num_samples}h", *samples)
