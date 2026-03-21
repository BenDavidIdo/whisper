"""ChatRoom module: orchestrates listener, processor, and speaker coroutines."""

import asyncio


class ChatRoom:
    """Coordinates microphone input, audio processing, and speaker output.

    Runs three async components concurrently:
    - listener: captures audio from a source into an input queue
    - processor: transforms audio from input queue to output queue
    - speaker: plays audio from the output queue

    Attributes:
        listener: Async callable(queue_in, stop_event).
        speaker: Async callable(queue_in, stop_event).
        processor: Async callable(queue_in, queue_out, stop_event).
        audio_in: Queue connecting listener to processor.
        audio_out: Queue connecting processor to speaker.
        stop_chat_event: asyncio.Event used to signal shutdown.
    """

    def __init__(self, listener, speaker, processor):
        """Initialise a ChatRoom with the three component callables.

        Args:
            listener: Async callable(queue_in, stop_event) that captures audio.
            speaker: Async callable(queue_in, stop_event) that plays audio.
            processor: Async callable(queue_in, queue_out, stop_event) that
                processes audio (e.g., transcription).
        """
        self.listener = listener
        self.speaker = speaker
        self.processor = processor
        self.audio_in = asyncio.Queue()
        self.audio_out = asyncio.Queue()
        self.stop_chat_event = asyncio.Event()

    async def start_chat(self):
        """Start all components concurrently and block until they all finish.

        Clears the stop event before launching so the room can be restarted.
        """
        self.stop_chat_event.clear()
        await asyncio.gather(
            self.listener(self.audio_in, self.stop_chat_event),
            self.processor(self.audio_in, self.audio_out, self.stop_chat_event),
            self.speaker(self.audio_out, self.stop_chat_event),
        )

    def stop_chat(self):
        """Signal all components to stop by setting the stop event."""
        self.stop_chat_event.set()
