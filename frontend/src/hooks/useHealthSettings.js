import { useCallback, useEffect, useState } from "react";
import { getHealth, getSettings, saveSettings } from "../api";

export default function useHealthSettings({ wakeWordEnabled, setWakeWordEnabled }) {
  const [voiceRate, setVoiceRate] = useState(1);
  const [voicePitch, setVoicePitch] = useState(1);
  const [micEnabled, setMicEnabled] = useState(true);
  const [textOutputEnabled, setTextOutputEnabled] = useState(true);
  const [showHistory, setShowHistory] = useState(false);
  const [textInputEnabled, setTextInputEnabled] = useState(true);
  const [localVoiceEnabled, setLocalVoiceEnabled] = useState(true);
  const [browserSpeechFallbackEnabled, setBrowserSpeechFallbackEnabled] = useState(false);
  const [apiHealth, setApiHealth] = useState(null);
  const [lastHealthCheckedAt, setLastHealthCheckedAt] = useState(null);

  const refreshHealth = useCallback(async () => {
    const health = await getHealth();
    setApiHealth(health);
    setLastHealthCheckedAt(new Date().toISOString());
    return health;
  }, []);

  useEffect(() => {
    let cancelled = false;
    const loadStatus = async () => {
      const [health, settings] = await Promise.all([getHealth(), getSettings()]);
      if (cancelled) return;
      setApiHealth(health);
      setLastHealthCheckedAt(new Date().toISOString());
      if (typeof settings.wake_word_enabled === "boolean") {
        setWakeWordEnabled(settings.wake_word_enabled);
      }
      if (typeof settings.voice_rate === "number") setVoiceRate(settings.voice_rate);
      if (typeof settings.voice_pitch === "number") setVoicePitch(settings.voice_pitch);
      if (typeof settings.mic_enabled === "boolean") setMicEnabled(settings.mic_enabled);
      if (typeof settings.text_output_enabled === "boolean") setTextOutputEnabled(settings.text_output_enabled);
      if (typeof settings.show_history === "boolean") setShowHistory(settings.show_history);
      if (typeof settings.text_input_enabled === "boolean") setTextInputEnabled(settings.text_input_enabled);
      if (typeof settings.local_voice_enabled === "boolean") setLocalVoiceEnabled(settings.local_voice_enabled);
      if (typeof settings.browser_speech_fallback_enabled === "boolean") {
        setBrowserSpeechFallbackEnabled(settings.browser_speech_fallback_enabled);
      }
    };
    loadStatus();
    return () => {
      cancelled = true;
    };
  }, [setWakeWordEnabled]);

  const saveAssistantSettings = useCallback(async () => {
    const payload = {
      wake_word_enabled: wakeWordEnabled,
      voice_rate: voiceRate,
      voice_pitch: voicePitch,
      mic_enabled: micEnabled,
      text_output_enabled: textOutputEnabled,
      show_history: showHistory,
      text_input_enabled: textInputEnabled,
      local_voice_enabled: localVoiceEnabled,
      browser_speech_fallback_enabled: browserSpeechFallbackEnabled,
    };
    return saveSettings(payload);
  }, [wakeWordEnabled, voiceRate, voicePitch, micEnabled, textOutputEnabled, showHistory, textInputEnabled, localVoiceEnabled, browserSpeechFallbackEnabled]);

  return {
    apiHealth,
    lastHealthCheckedAt,
    refreshHealth,
    saveAssistantSettings,
    voicePitch,
    setVoicePitch,
    voiceRate,
    setVoiceRate,
    micEnabled,
    setMicEnabled,
    textOutputEnabled,
    setTextOutputEnabled,
    showHistory,
    setShowHistory,
    textInputEnabled,
    setTextInputEnabled,
    localVoiceEnabled,
    setLocalVoiceEnabled,
    browserSpeechFallbackEnabled,
    setBrowserSpeechFallbackEnabled,
  };
}
