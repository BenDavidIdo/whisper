import { contextBridge, ipcRenderer } from 'electron';

/**
 * Typed API exposed to the renderer via contextBridge.
 * All communication with the main process goes through these methods.
 */
const api = {
  /** Called when the fn key is held — renderer should start mic capture */
  onStartRecording: (cb: () => void) => {
    ipcRenderer.on('start-recording', cb);
  },

  /** Called when the fn key is released — renderer should stop mic capture */
  onStopRecording: (cb: () => void) => {
    ipcRenderer.on('stop-recording', cb);
  },

  /**
   * Send a PCM audio chunk (Int16, 16 kHz mono) to the main process,
   * which forwards it over WebSocket to the Whisper Flow server.
   */
  sendAudioChunk: (buffer: ArrayBuffer) => {
    ipcRenderer.send('audio-chunk', buffer);
  },

  /**
   * Fired when the server emits a transcript (partial or final).
   * @param isFinal true when the server closes a speech segment
   */
  onTranscript: (cb: (text: string, isFinal: boolean) => void) => {
    ipcRenderer.on('transcript', (_event, text: string, isFinal: boolean) => {
      cb(text, isFinal);
    });
  },

  /** Remove all listeners for a given channel (clean-up on unmount) */
  removeAllListeners: (channel: string) => {
    ipcRenderer.removeAllListeners(channel);
  },
} as const;

export type WhisperClientAPI = typeof api;

contextBridge.exposeInMainWorld('api', api);
