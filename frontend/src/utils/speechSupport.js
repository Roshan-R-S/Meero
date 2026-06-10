export const getBrowserSpeechRecognition = () => {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
};

export const browserSpeechRecognitionSupported = () =>
  Boolean(getBrowserSpeechRecognition());

export const localAudioCaptureSupported = () =>
  typeof navigator !== "undefined" &&
  Boolean(navigator.mediaDevices?.getUserMedia) &&
  typeof window !== "undefined" &&
  Boolean(window.AudioContext || window.webkitAudioContext);
