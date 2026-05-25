// Simple Sci-Fi Sound Synthesizer using Web Audio API
// AudioContext is lazily created on first use to avoid browser autoplay policy warnings.

let audioCtx = null;

const getAudioCtx = () => {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  // Resume if suspended (browsers suspend until user gesture)
  if (audioCtx.state === "suspended") {
    audioCtx.resume();
  }
  return audioCtx;
};

const playTone = (freq, type, duration, delay = 0) => {
    const ctx = getAudioCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = type;
    osc.frequency.setValueAtTime(freq, ctx.currentTime + delay);

    gain.gain.setValueAtTime(0.1, ctx.currentTime + delay);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + delay + duration);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(ctx.currentTime + delay);
    osc.stop(ctx.currentTime + delay + duration);
};

export const playStartup = () => {
    const ctx = getAudioCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.frequency.setValueAtTime(100, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(800, ctx.currentTime + 1);

    gain.gain.setValueAtTime(0, ctx.currentTime);
    gain.gain.linearRampToValueAtTime(0.2, ctx.currentTime + 0.5);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 1.5);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start();
    osc.stop(ctx.currentTime + 1.5);
};

export const playListeningStart = () => {
    // Classic "Homing" chirp
    playTone(800, 'sine', 0.1);
    playTone(1200, 'sine', 0.1, 0.1);
};

export const playListeningStop = () => {
    // Confirmation "Done" chirp
    playTone(1200, 'sine', 0.1);
    playTone(600, 'sine', 0.1, 0.1);
};

export const playProcessing = () => {
    // Computational noise
    for (let i = 0; i < 3; i++) {
        playTone(400 + Math.random() * 200, 'square', 0.05, i * 0.08);
    }
};

export const playSuccess = () => {
    // Harmonious chord
    playTone(440, 'sine', 0.5);
    playTone(554, 'sine', 0.5); // C#
    playTone(659, 'sine', 0.5); // E
};
