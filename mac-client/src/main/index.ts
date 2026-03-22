import { app, BrowserWindow, ipcMain, clipboard, screen, systemPreferences, dialog } from 'electron';
import { join } from 'path';
import { exec, spawn } from 'child_process';
import type { ChildProcess } from 'child_process';
import { promisify } from 'util';
import WebSocket from 'ws';
import { uIOhook, UiohookKey } from 'uiohook-napi';

const execAsync = promisify(exec);

// ── Constants ────────────────────────────────────────────────────────────────

const WS_URL = 'ws://localhost:8181/ws';
const WINDOW_WIDTH = 240;
const WINDOW_HEIGHT = 64;

// macOS fn/Globe key keycode in libuiohook (kVK_Function = 63)
const FN_KEYCODE = 63;

// ── Server process ───────────────────────────────────────────────────────────

let serverProcess: ChildProcess | null = null;

function launchServer(): void {
  if (!app.isPackaged) return; // dev mode: user runs the server manually

  const bin = join(process.resourcesPath, 'server', 'whisper-server');

  serverProcess = spawn(bin, [], {
    detached: false,
    stdio: 'ignore',
    env: { ...process.env, WHISPERFLOW_PORT: '8181' },
  });

  serverProcess.on('error', (err) => {
    console.error('[whisper-client] Failed to start bundled server:', err.message);
  });

  serverProcess.on('exit', (code) => {
    console.log('[whisper-client] Server exited with code', code);
    serverProcess = null;
  });
}

function stopServer(): void {
  if (serverProcess) {
    serverProcess.kill('SIGTERM');
    serverProcess = null;
  }
}

// ── State ────────────────────────────────────────────────────────────────────

let overlayWindow: BrowserWindow | null = null;
let wsClient: WebSocket | null = null;
let isRecording = false;
let finalTranscript = '';
let partialTranscript = '';

// ── Window ───────────────────────────────────────────────────────────────────

function createOverlayWindow(): BrowserWindow {
  const { width: screenW, height: screenH } = screen.getPrimaryDisplay().workAreaSize;

  const win = new BrowserWindow({
    width: WINDOW_WIDTH,
    height: WINDOW_HEIGHT,
    x: Math.round((screenW - WINDOW_WIDTH) / 2),
    y: screenH - 120,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    focusable: false, // critical: don't steal focus from active app
    resizable: false,
    movable: false,
    hasShadow: false,
    show: false,
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  win.setAlwaysOnTop(true, 'floating');

  if (process.env['ELECTRON_RENDERER_URL']) {
    win.loadURL(process.env['ELECTRON_RENDERER_URL']);
  } else {
    win.loadFile(join(__dirname, '../renderer/index.html'));
  }

  return win;
}

// ── WebSocket ────────────────────────────────────────────────────────────────

function openWebSocket(): Promise<WebSocket> {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(WS_URL);

    ws.on('open', () => resolve(ws));
    ws.on('error', (err) => reject(err));

    ws.on('message', (data: WebSocket.RawData) => {
      try {
        const msg = JSON.parse(data.toString()) as {
          is_partial: boolean;
          data: { text: string };
        };

        const text = msg.data?.text?.trim() ?? '';
        if (!text) return;

        if (msg.is_partial) {
          partialTranscript = text;
          overlayWindow?.webContents.send('transcript', text, false);
        } else {
          finalTranscript = text;
          overlayWindow?.webContents.send('transcript', text, true);
        }
      } catch {
        // ignore malformed messages
      }
    });

    ws.on('close', () => {
      wsClient = null;
    });
  });
}

// ── Text injection ───────────────────────────────────────────────────────────

/**
 * Types text into the currently focused application by temporarily using the
 * clipboard and simulating Cmd+V. This is the most reliable approach on macOS
 * because it works in all apps (terminal, browser, native apps, etc.).
 */
async function injectText(text: string): Promise<void> {
  if (!text.trim()) return;

  const previous = clipboard.readText();
  clipboard.writeText(text);

  try {
    // osascript paste works even if our window is not focused
    await execAsync(
      `osascript -e 'tell application "System Events" to keystroke "v" using command down'`,
    );
  } finally {
    // Restore clipboard after paste completes
    setTimeout(() => clipboard.writeText(previous), 200);
  }
}

// ── Recording lifecycle ──────────────────────────────────────────────────────

async function startRecording(): Promise<void> {
  if (isRecording) return;
  isRecording = true;
  finalTranscript = '';
  partialTranscript = '';

  // Show overlay immediately so the user gets feedback
  overlayWindow?.show();

  try {
    wsClient = await openWebSocket();
  } catch {
    console.error('[whisper-client] Cannot reach Whisper Flow at', WS_URL);
    overlayWindow?.webContents.send('server-error');
    isRecording = false;
    // Hide after a moment so the user sees the error
    await new Promise((r) => setTimeout(r, 2000));
    overlayWindow?.hide();
    return;
  }

  overlayWindow?.webContents.send('start-recording');
}

async function stopRecording(): Promise<void> {
  if (!isRecording) return;
  isRecording = false;

  overlayWindow?.webContents.send('stop-recording');

  // Give the server a moment to emit the final transcript
  await new Promise((r) => setTimeout(r, 600));

  wsClient?.close();
  wsClient = null;

  const text = finalTranscript || partialTranscript;
  overlayWindow?.hide();

  if (text) {
    await injectText(text);
  }
}

// ── IPC ──────────────────────────────────────────────────────────────────────

ipcMain.on('audio-chunk', (_event, buffer: ArrayBuffer) => {
  if (wsClient?.readyState === WebSocket.OPEN) {
    wsClient.send(Buffer.from(buffer));
  }
});

// ── Global fn key listener ───────────────────────────────────────────────────

function setupFnKeyListener(): void {
  uIOhook.on('keydown', (event) => {
    // FN_KEYCODE 63 = macOS fn/Globe key via libuiohook
    // Falls back to UiohookKey.F18 if fn is not interceptable on your system
    if (event.keycode === FN_KEYCODE || event.keycode === UiohookKey.F18) {
      startRecording();
    }
  });

  uIOhook.on('keyup', (event) => {
    if (event.keycode === FN_KEYCODE || event.keycode === UiohookKey.F18) {
      stopRecording();
    }
  });

  uIOhook.start();
}

// ── App lifecycle ─────────────────────────────────────────────────────────────

app.whenReady().then(() => {
  // uIOhook and osascript both require Accessibility permission on macOS.
  // Without it, global key events fire nothing and paste silently fails.
  if (process.platform === 'darwin') {
    const trusted = systemPreferences.isTrustedAccessibilityClient(false);
    if (!trusted) {
      // Prompt the system to show the Accessibility permission dialog
      systemPreferences.isTrustedAccessibilityClient(true);
      dialog.showMessageBoxSync({
        type: 'warning',
        title: 'Accessibility Permission Required',
        message:
          'Whisper Flow needs Accessibility access to detect the fn key and paste text.\n\n' +
          '1. Open System Settings → Privacy & Security → Accessibility\n' +
          '2. Enable Whisper Flow\n' +
          '3. Relaunch Whisper Flow',
        buttons: ['Quit'],
      });
      app.quit();
      return;
    }
  }

  launchServer();
  overlayWindow = createOverlayWindow();
  setupFnKeyListener();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      overlayWindow = createOverlayWindow();
    }
  });
});

app.on('window-all-closed', () => {
  uIOhook.stop();
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  uIOhook.stop();
  wsClient?.close();
  stopServer();
});
