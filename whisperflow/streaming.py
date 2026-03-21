"""Streaming module: tumbling window segmentation and session management."""

import asyncio
import time
import uuid
from queue import Queue


def get_all(queue):
    """Drain all pending items from a queue into a list.

    Args:
        queue: A Queue instance or None.

    Returns:
        List of all items currently in the queue.
    """
    items = []
    if queue is None:
        return items
    while not queue.empty():
        items.append(queue.get_nowait())
    return items


def should_close_segment(result, prev_result, cycles, max_cycles=1):
    """Determine whether the current speech segment should be finalized.

    A segment closes when transcription output has been identical for
    at least max_cycles consecutive processing iterations, indicating a
    natural speech pause.

    Args:
        result: Current transcription result dict.
        prev_result: Previous transcription result dict (or None).
        cycles: Number of consecutive identical transcription cycles.
        max_cycles: Minimum identical cycles before closing (default 1).

    Returns:
        True if the segment should be closed, False otherwise.
    """
    if prev_result is None:
        return False
    current_text = result.get("data", {}).get("text", "")
    prev_text = prev_result.get("data", {}).get("text", "")
    return cycles >= max_cycles and current_text == prev_text


async def transcribe(should_stop, queue, transcriber, segment_closed):
    """Infinite transcription loop implementing the tumbling window algorithm.

    Continuously drains the audio queue, runs transcription on the accumulated
    window, and emits partial or final results via segment_closed.

    Args:
        should_stop: A single-element list [bool] used as a mutable stop flag.
        queue: Queue receiving raw PCM byte chunks.
        transcriber: Async callable (chunks) -> transcription result dict.
        segment_closed: Async callable (result_dict) -> None, receives results.
    """
    window = []
    prev_result = None
    cycles = 0

    while not should_stop[0]:
        await asyncio.sleep(0.01)

        new_chunks = get_all(queue)
        window.extend(new_chunks)

        if not window:
            continue

        start = time.time()
        transcription = await transcriber(window)
        elapsed_ms = (time.time() - start) * 1000

        result = {
            "is_partial": True,
            "data": transcription,
            "time": elapsed_ms,
        }

        current_text = transcription.get("text", "")
        prev_text = (prev_result or {}).get("data", {}).get("text", "")

        if current_text == prev_text:
            cycles += 1
        else:
            cycles = 0

        if should_close_segment(result, prev_result, cycles):
            result["is_partial"] = False
            window = []
            cycles = 0
            prev_result = None
        else:
            prev_result = result

        await segment_closed(result)


class TranscribeSession:
    """A stateful streaming transcription session.

    Manages a background transcription loop that consumes audio chunks
    queued from the caller and emits results via a callback.

    Attributes:
        id: Unique UUID for this session.
        queue: Queue for incoming PCM audio chunks.
        should_stop: Mutable flag list to signal loop termination.
        task: The background asyncio task running the transcription loop.
    """

    def __init__(self, transcribe_async, send_back_async):
        """Create a new transcription session and start the background loop.

        Args:
            transcribe_async: Async callable (chunks) -> transcription dict.
            send_back_async: Async callable (result_dict) -> None.
        """
        self.id = uuid.uuid4()
        self.queue = Queue()
        self.should_stop = [False]
        self.task = asyncio.create_task(
            transcribe(
                self.should_stop,
                self.queue,
                transcribe_async,
                send_back_async,
            )
        )

    def add_chunk(self, chunk: bytes):
        """Queue an audio chunk for transcription.

        Args:
            chunk: Raw PCM bytes (16kHz, 16-bit, mono).
        """
        self.queue.put_nowait(chunk)

    async def stop(self):
        """Gracefully stop the transcription loop and await task completion."""
        self.should_stop[0] = True
        await self.task
