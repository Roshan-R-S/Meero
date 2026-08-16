import axios from 'axios';
import { logger } from './utils/logger';

export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const AUTH_VALUE = import.meta.env.VITE_MEERO_API_KEY || '';

const authHeaders = AUTH_VALUE ? { 'x-meero-api-key': AUTH_VALUE } : {};

const isBackendUnavailableError = (error) => {
  const message = String(error?.message || '').toLowerCase();
  const code = String(error?.code || '').toLowerCase();
  return (
    message.includes('network error') ||
    message.includes('connection refused') ||
    message.includes('connection reset') ||
    code === 'err_network' ||
    code === 'econnrefused' ||
    code === 'econnreset'
  );
};

const notifyServerReachable = (reachable) => {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent('meero:server-reachable', { detail: { reachable } }));
};

export const sendCommand = async (command, options = {}) => {
  try {
    const response = await axios.post(`${API_URL}/command`, {
      command,
      mode: 'voice',
      confirm: Boolean(options.confirm),
      pending_command: options.pendingCommand || null,
    }, { headers: authHeaders });
    notifyServerReachable(true);
    logger.log("[API] /command response:", response.data);
    return response.data;
  } catch (error) {
    logger.error("API Error:", error);
    notifyServerReachable(false);
    return { response: "I cannot reach the server.", action_status: "error" };
  }
};

export const sendVoiceCommand = async (audio, options = {}) => {
  const form = new FormData();
  form.append('audio', audio, 'command.wav');
  form.append('synthesize', String(options.synthesize ?? true));
  if (options.pendingCommand) form.append('pending_command', options.pendingCommand);
  try {
    const response = await axios.post(`${API_URL}/voice-command`, form, { headers: authHeaders });
    notifyServerReachable(true);
    return response.data;
  } catch (error) {
    logger.error("Voice API Error:", error);
    notifyServerReachable(false);
    throw new Error(error.response?.data?.detail || "Local voice processing failed.");
  }
};

export const getHealth = async () => {
  try {
    const response = await axios.get(`${API_URL}/debug/health`, { headers: authHeaders });
    notifyServerReachable(true);
    return { ...response.data, detailed: true };
  } catch (debugError) {
    if (!isBackendUnavailableError(debugError)) {
      logger.log("Debug health unavailable; falling back to public health.", debugError);
    }
    try {
      const response = await axios.get(`${API_URL}/health`);
      notifyServerReachable(true);
      return { ...response.data, detailed: false };
    } catch (error) {
      if (!isBackendUnavailableError(error)) {
        logger.error("Health API Error:", error);
      }
      notifyServerReachable(false);
      return null;
    }
  }
};

export const getSettings = async () => {
  try {
    const response = await axios.get(`${API_URL}/settings`, { headers: authHeaders });
    notifyServerReachable(true);
    return response.data;
  } catch (error) {
    if (!isBackendUnavailableError(error)) {
      logger.error("Settings API Error:", error);
    }
    notifyServerReachable(false);
    return {};
  }
};

export const getModelStatus = async () => {
  try {
    const response = await axios.get(`${API_URL}/model/status`, { headers: authHeaders });
    notifyServerReachable(true);
    return response.data;
  } catch (error) {
    if (!isBackendUnavailableError(error)) {
      logger.error("Model status API Error:", error);
    }
    notifyServerReachable(false);
    return null;
  }
};

export const saveSettings = async (settings) => {
  try {
    const response = await axios.post(`${API_URL}/settings`, settings, { headers: authHeaders });
    notifyServerReachable(true);
    return response.data;
  } catch (error) {
    if (!isBackendUnavailableError(error)) {
      logger.error("Save settings API Error:", error);
    }
    notifyServerReachable(false);
    return { status: "error" };
  }
};

export const exportMemory = async () => {
  try {
    const response = await axios.get(`${API_URL}/memory`, { headers: authHeaders });
    return response.data;
  } catch (error) {
    logger.error("Export memory API Error:", error);
    return null;
  }
};

export const clearMemory = async () => {
  try {
    const response = await axios.delete(`${API_URL}/memory`, { headers: authHeaders });
    return response.data;
  } catch (error) {
    logger.error("Clear memory API Error:", error);
    return { status: "error" };
  }
};
