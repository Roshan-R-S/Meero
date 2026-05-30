import { useCallback, useEffect, useState } from "react";
import { getHealth, getSettings, saveSettings } from "../api";

export default function useHealthSettings({ wakeWordEnabled, setWakeWordEnabled }) {
  const [voiceRate, setVoiceRate] = useState(1);
  const [voicePitch, setVoicePitch] = useState(1);
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
    };
    loadStatus();
    return () => {
      cancelled = true;
    };
  }, [setWakeWordEnabled]);

  const saveAssistantSettings = useCallback(async () => {
    return saveSettings({
      wake_word_enabled: wakeWordEnabled,
      voice_rate: voiceRate,
      voice_pitch: voicePitch,
    });
  }, [wakeWordEnabled, voiceRate, voicePitch]);

  return {
    apiHealth,
    lastHealthCheckedAt,
    refreshHealth,
    saveAssistantSettings,
    voicePitch,
    setVoicePitch,
    voiceRate,
    setVoiceRate,
  };
}
