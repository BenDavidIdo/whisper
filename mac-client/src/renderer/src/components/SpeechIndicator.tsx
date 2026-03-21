import { useEffect, useRef } from 'react';

interface Props {
  analyser: AnalyserNode | null;
  isRecording: boolean;
}

const BAR_COUNT = 12;
const MIN_HEIGHT = 3;
const MAX_HEIGHT = 28;

/**
 * Animated waveform bars — identical in look to the macOS dictation indicator.
 *
 * - Idle (not recording): each bar gently breathes with a staggered CSS animation
 * - Recording: bars animate in real-time from the Web Audio AnalyserNode
 *
 * Inspired by ElevenLabs' open-source shadcn speech visualizer.
 */
export function SpeechIndicator({ analyser, isRecording }: Props) {
  const barRefs = useRef<(HTMLDivElement | null)[]>([]);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }

    if (!isRecording || !analyser) {
      // Reset bars to idle height; CSS animation takes over via className
      barRefs.current.forEach((bar) => {
        if (bar) bar.style.height = '';
      });
      return;
    }

    // Disable CSS animation while JS drives the heights
    barRefs.current.forEach((bar) => {
      if (bar) bar.style.animationName = 'none';
    });

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    // Distribute bars evenly across the lower half of the frequency spectrum
    // (voice frequencies live roughly in the first 40% of the FFT bins)
    const binStep = Math.floor((bufferLength * 0.4) / BAR_COUNT);

    const draw = () => {
      analyser.getByteFrequencyData(dataArray);

      barRefs.current.forEach((bar, i) => {
        if (!bar) return;
        const binValue = dataArray[i * binStep] ?? 0;
        const ratio = binValue / 255;
        // Ease the value so quiet audio still shows some movement
        const easedRatio = Math.pow(ratio, 0.6);
        const height = Math.max(MIN_HEIGHT, Math.round(easedRatio * MAX_HEIGHT));
        bar.style.height = `${height}px`;
      });

      rafRef.current = requestAnimationFrame(draw);
    };

    rafRef.current = requestAnimationFrame(draw);

    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, [analyser, isRecording]);

  return (
    <div
      className="flex items-center justify-center gap-[3px] px-5"
      style={{ height: `${MAX_HEIGHT + 24}px` }}
    >
      {Array.from({ length: BAR_COUNT }).map((_, i) => (
        <div
          key={i}
          ref={(el) => {
            barRefs.current[i] = el;
          }}
          className="w-[3px] rounded-full bg-white"
          style={{
            height: `${MIN_HEIGHT}px`,
            animationName: isRecording ? 'none' : 'breathe',
            animationDuration: '1.2s',
            animationDelay: `${i * 80}ms`,
            animationTimingFunction: 'ease-in-out',
            animationIterationCount: 'infinite',
            animationDirection: 'alternate',
            transition: isRecording ? 'height 60ms ease-out' : 'none',
          }}
        />
      ))}
    </div>
  );
}
