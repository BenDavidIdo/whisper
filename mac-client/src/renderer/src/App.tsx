import { useEffect, useRef, useState, useCallback } from 'react';
import { SpeechIndicator } from './components/SpeechIndicator';
import type { WhisperClientAPI } from '../../preload';

declare global {
  interface Window {
    api: WhisperClientAPI;
  }
}

// PCM chunk size in samples (4096 @ 16 kHz ≈ 256 ms — matches server recommendation)
const PCM_CHUNK_SAMPLES = 4096;

// ── Mic capture helpers ───────────────────────────────────────────────────────

interface AudioSession {
  context: AudioContext;
  analyser: AnalyserNode;
  processor: ScriptProcessorNode;
  stream: MediaStream;
}

async function openMic(): Promise<AudioSession> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      sampleRate: 16000,
      channelCount: 1,
    },
  });

  // Request 16 kHz directly — browser handles downsampling
  const context = new AudioContext({ sampleRate: 16000 });
  const source = context.createMediaStreamSource(stream);

  const analyser = context.createAnalyser();
  analyser.fftSize = 256;
  analyser.smoothingTimeConstant = 0.8;

  // ScriptProcessor is deprecated but universally available without COOP headers.
  // Switch to AudioWorklet once Electron ships with full Worklet support enabled.
  const processor = context.createScriptProcessor(PCM_CHUNK_SAMPLES, 1, 1);

  source.connect(analyser);
  source.connect(processor);
  processor.connect(context.destination);

  return { context, analyser, processor, stream };
}

function closeMic(session: AudioSession): void {
  session.processor.disconnect();
  session.analyser.disconnect();
  session.stream.getTracks().forEach((t) => t.stop());
  session.context.close();
}

function float32ToInt16(float32: Float32Array): ArrayBuffer {
  const int16 = new Int16Array(float32.length);
  for (let i = 0; i < float32.length; i++) {
    int16[i] = Math.max(-32768, Math.min(32767, Math.round(float32[i] * 32767)));
  }
  return int16.buffer;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function App() {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const sessionRef = useRef<AudioSession | null>(null);

  const handleStartRecording = useCallback(async () => {
    if (sessionRef.current) return;

    try {
      const session = await openMic();
      sessionRef.current = session;

      session.processor.onaudioprocess = (event) => {
        const float32 = event.inputBuffer.getChannelData(0);
        const pcm = float32ToInt16(float32);
        window.api.sendAudioChunk(pcm);
      };

      setIsRecording(true);
      setTranscript('');
    } catch (err) {
      console.error('[renderer] Mic access denied:', err);
    }
  }, []);

  const handleStopRecording = useCallback(() => {
    if (sessionRef.current) {
      closeMic(sessionRef.current);
      sessionRef.current = null;
    }
    setIsRecording(false);
  }, []);

  useEffect(() => {
    window.api.onStartRecording(handleStartRecording);
    window.api.onStopRecording(handleStopRecording);
    window.api.onTranscript((text, isFinal) => {
      setTranscript(text);
      if (isFinal) {
        // Keep the final text visible for a moment before window hides
        setTimeout(() => setTranscript(''), 500);
      }
    });

    return () => {
      window.api.removeAllListeners('start-recording');
      window.api.removeAllListeners('stop-recording');
      window.api.removeAllListeners('transcript');
    };
  }, [handleStartRecording, handleStopRecording]);

  return (
    <div className="flex h-full w-full items-end justify-center pb-2">
      {/* Floating pill */}
      <div
        className="relative flex flex-col items-center overflow-hidden rounded-full"
        style={{
          background: 'rgba(20, 20, 20, 0.88)',
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          boxShadow: '0 4px 24px rgba(0,0,0,0.5)',
          minWidth: 160,
        }}
      >
        <SpeechIndicator
          analyser={sessionRef.current?.analyser ?? null}
          isRecording={isRecording}
        />

        {/* Live transcript ticker — fades in when there's text */}
        {transcript ? (
          <p
            className="w-full truncate px-4 pb-2 text-center text-[11px] font-medium text-white/70"
            style={{ maxWidth: 220 }}
          >
            {transcript}
          </p>
        ) : null}
      </div>

      {/* Breathe keyframe injected via style tag to avoid PostCSS config changes */}
      <style>{`
        @keyframes breathe {
          from { height: 3px; }
          to   { height: 14px; }
        }
      `}</style>
    </div>
  );
}
