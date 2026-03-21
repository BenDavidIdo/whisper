# Whisper Flow

Real-time speech-to-text streaming using OpenAI's Whisper model. Delivers incremental transcripts with sub-second latency via WebSocket streaming.

## Features

- **Real-time streaming**: Continuous audio transcription over WebSocket
- **Tumbling window segmentation**: Detects natural speech pauses without fixed time cutoffs
- **Low latency**: ~275ms mean transcription latency
- **REST API**: Batch transcription via HTTP POST
- **GPU acceleration**: Auto-detects CUDA, falls back to CPU

## Architecture

```
Audio Input (WebSocket/HTTP)
         ↓
    Queue Buffer
         ↓
  Transcription Loop (tumbling window)
         ↓
   Segment Closure Logic (speech pattern detection)
         ↓
  Output Events (partial/final transcripts)
```

## Quick Start

### Prerequisites

- Python 3.8+
- PortAudio development libraries: `sudo apt-get install portaudio19-dev`
- Whisper model file in `whisperflow/models/` (e.g., `tiny.en.pt`)

### Install

```bash
pip install -r requirements.txt
pip install -e .
```

### Download model

```bash
mkdir -p whisperflow/models
python -c "import whisper; whisper.load_model('tiny.en')"
# Then move ~/.cache/whisper/tiny.en.pt to whisperflow/models/
```

### Run server

```bash
./run.sh -run-server
# Or directly:
python -m uvicorn whisperflow.fast_server:app --host 0.0.0.0 --port 8181
```

### Docker

```bash
docker build -t whisperflow .
docker run -p 8181:8181 -v $(pwd)/whisperflow/models:/app/whisperflow/models whisperflow
```

## API

### Health check

```
GET /health
→ "Whisper Flow V1.1.0"
```

### Batch transcription

```
POST /transcribe_pcm_chunk
Form: model_name=tiny.en.pt, files=<audio bytes>
→ {"text": "...", "segments": [...], "language": "en"}
```

### Streaming transcription

```
WebSocket /ws
Send: binary PCM audio chunks (16kHz, 16-bit, mono)
Receive: {"is_partial": bool, "data": {"text": "..."}, "time": float}
```

## Audio Format

- Sample rate: 16,000 Hz
- Bit depth: 16-bit signed integer PCM
- Channels: Mono
- Chunk size: 4096 bytes recommended

## Development

```bash
./run.sh -local     # Full setup, lint, test
./run.sh -test      # Lint and test only
./run.sh -benchmark # Performance benchmarks
```

## Testing

```bash
pytest tests/ --cov=whisperflow --cov-report=term-missing
```

## License

MIT License
