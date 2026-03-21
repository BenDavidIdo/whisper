"""Tests for whisperflow.chat_room module."""

import asyncio

import pytest

from whisperflow.chat_room import ChatRoom


class TestChatRoom:
    """Tests for the ChatRoom orchestration class."""

    @pytest.mark.asyncio
    async def test_chat_room_starts_and_stops(self):
        """All three components should run and the room should stop cleanly."""
        events = []

        async def listener(queue_in, stop_event):
            events.append("listener_start")
            await stop_event.wait()
            events.append("listener_stop")

        async def processor(queue_in, queue_out, stop_event):
            events.append("processor_start")
            await stop_event.wait()
            events.append("processor_stop")

        async def speaker(queue_in, stop_event):
            events.append("speaker_start")
            await stop_event.wait()
            events.append("speaker_stop")

        room = ChatRoom(listener, speaker, processor)

        async def stopper():
            await asyncio.sleep(0.05)
            room.stop_chat()

        await asyncio.gather(room.start_chat(), stopper())

        assert "listener_start" in events
        assert "processor_start" in events
        assert "speaker_start" in events
        assert "listener_stop" in events
        assert "processor_stop" in events
        assert "speaker_stop" in events

    @pytest.mark.asyncio
    async def test_stop_chat_sets_event(self):
        """stop_chat() should set the stop_chat_event."""
        room = ChatRoom(None, None, None)
        room.stop_chat()
        assert room.stop_chat_event.is_set()

    @pytest.mark.asyncio
    async def test_start_clears_stop_event(self):
        """start_chat() should clear the stop_chat_event before running."""
        started = []

        async def listener(queue_in, stop_event):
            started.append(True)
            stop_event.set()

        async def processor(queue_in, queue_out, stop_event):
            await stop_event.wait()

        async def speaker(queue_in, stop_event):
            await stop_event.wait()

        room = ChatRoom(listener, speaker, processor)
        room.stop_chat()  # Set event before starting
        await room.start_chat()  # Should clear and then run

        assert started  # listener was called

    @pytest.mark.asyncio
    async def test_audio_queues_are_separate(self):
        """audio_in and audio_out should be distinct Queue objects."""
        room = ChatRoom(None, None, None)
        assert room.audio_in is not room.audio_out

    @pytest.mark.asyncio
    async def test_data_flows_listener_to_processor(self):
        """Data put by listener in audio_in should be readable by processor."""
        received = []

        async def listener(queue_in, stop_event):
            await queue_in.put(b"audio_chunk")
            await asyncio.sleep(0.05)
            stop_event.set()

        async def processor(queue_in, queue_out, stop_event):
            await stop_event.wait()
            while not queue_in.empty():
                received.append(await queue_in.get())

        async def speaker(queue_in, stop_event):
            await stop_event.wait()

        room = ChatRoom(listener, speaker, processor)
        await room.start_chat()

        assert received == [b"audio_chunk"]
