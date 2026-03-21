# Whisper Flow — Mac Client

Hold **fn** (Globe key) to dictate. Release to insert the transcription at the cursor.

```
fn held  →  mic opens, floating waveform pill appears
fn released  →  final transcript is pasted into the active app
```

## How it works

1. `uiohook-napi` intercepts the global `fn`/Globe key (keycode 63) without stealing app focus
2. The overlay window appears at the bottom-centre of the screen — a pill with animated waveform bars matching the macOS dictation aesthetic
3. Mic audio is captured at 16 kHz mono via Web Audio API and sent as PCM Int16 over WebSocket to the Whisper Flow server (`ws://localhost:8181/ws`)
4. Live partial transcripts appear in the pill while you speak
5. On release, the final text is pasted via `Cmd+V` into whatever was focused before you started dictating

## Setup

### Prerequisites

- macOS (the fn key hook requires macOS)
- Node.js 18+
- **Accessibility permission** — macOS will prompt you to grant it on first run (required for global key events and osascript paste)
- Whisper Flow server running on port 8181: `./run.sh -run-server` from the repo root

### Install & run

```bash
cd mac-client
npm install
npm run dev
```

### Build distributable

```bash
npm run dist
# → dist/Whisper Flow-1.0.0-arm64.dmg (Apple Silicon)
# → dist/Whisper Flow-1.0.0.dmg       (Intel)
```

## Fallback key

If the `fn` key isn't interceptable on your system, you can use **F18** instead —
the main process listens for both. Map any key to F18 via System Preferences → Keyboard → Shortcuts,
or use Karabiner-Elements.

## Architecture

```
Main process (Node.js/Electron)
  ├── uiohook-napi       global fn key listener
  ├── BrowserWindow      transparent, non-focusable floating overlay
  ├── ws.WebSocket       streams PCM audio → Whisper Flow server
  └── osascript          pastes final transcript into active app

Preload (contextBridge)
  └── exposes typed IPC API to renderer

Renderer (React + Tailwind)
  ├── Web Audio API      mic capture @ 16 kHz, Float32→Int16 conversion
  ├── AnalyserNode       frequency data for real-time bar animation
  └── SpeechIndicator    animated waveform pill component
```
