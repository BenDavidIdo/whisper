"""Tests for whisperflow.audio.microphone module."""

import asyncio
import struct

import numpy as np
import pytest

from whisperflow.audio.microphone import is_silent


class TestIsSilent:
    """Tests for the is_silent amplitude checker."""

    def _make_pcm(self, values):
        """Pack a list of int16 values into PCM bytes."""
        return struct.pack(f"<{len(values)}h", *values)

    def test_all_zeros_is_silent(self):
        data = self._make_pcm([0] * 100)
        assert is_silent(data) is True

    def test_below_threshold_is_silent(self):
        data = self._make_pcm([499, -499, 100])
        assert is_silent(data, silence_threshold=500) is True

    def test_at_threshold_is_not_silent(self):
        data = self._make_pcm([500])
        assert is_silent(data, silence_threshold=500) is False

    def test_above_threshold_is_not_silent(self):
        data = self._make_pcm([0, 0, 1000, 0])
        assert is_silent(data, silence_threshold=500) is False

    def test_negative_spike_is_not_silent(self):
        """Negative values above threshold magnitude should not be silent."""
        data = self._make_pcm([-1000])
        assert is_silent(data, silence_threshold=500) is False

    def test_custom_threshold(self):
        data = self._make_pcm([200])
        assert is_silent(data, silence_threshold=100) is False
        assert is_silent(data, silence_threshold=300) is True
