"""Tests for whisperflow.streaming module."""

import asyncio
from queue import Queue
from unittest.mock import AsyncMock, MagicMock

import pytest

from whisperflow.streaming import (
    TranscribeSession,
    get_all,
    should_close_segment,
    transcribe,
)


class TestGetAll:
    """Tests for the get_all queue drain utility."""

    def test_empty_queue_returns_empty_list(self):
        q = Queue()
        assert get_all(q) == []

    def test_none_returns_empty_list(self):
        assert get_all(None) == []

    def test_drains_all_items(self):
        q = Queue()
        for i in range(5):
            q.put_nowait(i)
        result = get_all(q)
        assert result == [0, 1, 2, 3, 4]
        assert q.empty()

    def test_single_item(self):
        q = Queue()
        q.put_nowait(b"chunk")
        assert get_all(q) == [b"chunk"]


class TestShouldCloseSegment:
    """Tests for segment closure detection logic."""

    def make_result(self, text):
        return {"data": {"text": text}, "is_partial": True}

    def test_no_prev_result_does_not_close(self):
        result = self.make_result("hello")
        assert should_close_segment(result, None, cycles=5) is False

    def test_same_text_sufficient_cycles_closes(self):
        r = self.make_result("hello world")
        assert should_close_segment(r, r, cycles=1) is True

    def test_same_text_insufficient_cycles_stays_open(self):
        r = self.make_result("hello")
        assert should_close_segment(r, r, cycles=0, max_cycles=1) is False

    def test_different_text_does_not_close(self):
        r1 = self.make_result("hello")
        r2 = self.make_result("hello world")
        assert should_close_segment(r2, r1, cycles=5) is False

    def test_custom_max_cycles(self):
        r = self.make_result("test")
        assert should_close_segment(r, r, cycles=2, max_cycles=3) is False
        assert should_close_segment(r, r, cycles=3, max_cycles=3) is True


class TestTranscribeLoop:
    """Tests for the transcribe coroutine (tumbling window loop)."""

    @pytest.mark.asyncio
    async def test_empty_queue_skips_transcription(self):
        """When the queue is empty no transcription should be called."""
        should_stop = [False]
        queue = Queue()
        transcriber = AsyncMock(return_value={"text": ""})
        results = []

        async def collect(r):
            results.append(r)
            should_stop[0] = True  # stop after first non-empty iteration

        # Run for a short time then stop
        should_stop[0] = True  # stop immediately since queue is empty
        await asyncio.wait_for(
            transcribe(should_stop, queue, transcriber, collect), timeout=0.5
        )

        transcriber.assert_not_called()
        assert results == []

    @pytest.mark.asyncio
    async def test_chunk_produces_result(self):
        """A queued chunk should produce a result from the transcription loop."""
        should_stop = [False]
        queue = Queue()
        queue.put_nowait(b"\x00" * 1024)

        call_count = 0

        async def mock_transcriber(chunks):
            nonlocal call_count
            call_count += 1
            return {"text": "hello", "segments": [], "language": "en"}

        results = []

        async def collect(r):
            results.append(r)
            should_stop[0] = True

        await asyncio.wait_for(
            transcribe(should_stop, queue, mock_transcriber, collect), timeout=2.0
        )

        assert len(results) >= 1
        assert results[0]["data"]["text"] == "hello"
        assert "time" in results[0]

    @pytest.mark.asyncio
    async def test_segment_closes_on_stable_text(self):
        """Segment should be marked not partial when text stabilises."""
        should_stop = [False]
        queue = Queue()
        queue.put_nowait(b"\x00" * 1024)

        call_count = 0

        async def mock_transcriber(chunks):
            nonlocal call_count
            call_count += 1
            return {"text": "stable text", "segments": [], "language": "en"}

        final_results = []

        async def collect(r):
            final_results.append(r)
            if not r["is_partial"]:
                should_stop[0] = True
            elif call_count >= 5:
                should_stop[0] = True

        await asyncio.wait_for(
            transcribe(should_stop, queue, mock_transcriber, collect), timeout=3.0
        )

        # Should have produced at least one final result
        non_partial = [r for r in final_results if not r["is_partial"]]
        assert len(non_partial) >= 1


class TestTranscribeSession:
    """Tests for the TranscribeSession class."""

    @pytest.mark.asyncio
    async def test_session_has_unique_id(self):
        """Two sessions should have different IDs."""
        calls = []

        async def transcriber(chunks):
            return {"text": "", "segments": [], "language": "en"}

        async def send_back(result):
            calls.append(result)

        s1 = TranscribeSession(transcriber, send_back)
        s2 = TranscribeSession(transcriber, send_back)
        assert s1.id != s2.id
        await s1.stop()
        await s2.stop()

    @pytest.mark.asyncio
    async def test_add_chunk_queues_data(self):
        """add_chunk should place data in the session queue."""
        sent = []

        async def transcriber(chunks):
            return {"text": "queued", "segments": [], "language": "en"}

        async def send_back(result):
            sent.append(result)

        session = TranscribeSession(transcriber, send_back)
        session.add_chunk(b"\x00" * 512)
        assert not session.queue.empty()
        await session.stop()

    @pytest.mark.asyncio
    async def test_stop_terminates_gracefully(self):
        """stop() should complete without error."""
        async def transcriber(chunks):
            return {"text": "", "segments": [], "language": "en"}

        async def send_back(result):
            pass

        session = TranscribeSession(transcriber, send_back)
        await session.stop()
        assert session.should_stop[0] is True
