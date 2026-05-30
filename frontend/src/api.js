import axios from 'axios';
import { logger } from './utils/logger';

export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const API_KEY = import.meta.env.VITE_MEERO_API_KEY || ''; // pragma: allowlist secret

const authHeaders = API_KEY ? { 'x-meero-api-key': API_KEY } : {};

export const sendCommand = async (command, options = {}) => {
  try {
    const response = await axios.post(`${API_URL}/command`, {
      command,
      mode: 'voice',
      confirm: Boolean(options.confirm),
      pending_command: options.pendingCommand || null,
    }, { headers: authHeaders });
    logger.log("[API] /command response:", response.data);
    return response.data;
  } catch (error) {
    logger.error("API Error:", error);
    return { response: "I cannot reach the server.", action_status: "error" };
  }
};

export const getHealth = async () => {
  try {
    const response = await axios.get(`${API_URL}/health`, { headers: authHeaders });
    return response.data;
  } catch (error) {
    logger.error("Health API Error:", error);
    return null;
  }
};

export const getSettings = async () => {
  try {
    const response = await axios.get(`${API_URL}/settings`, { headers: authHeaders });
    return response.data;
  } catch (error) {
    logger.error("Settings API Error:", error);
    return {};
  }
};

export const saveSettings = async (settings) => {
  try {
    const response = await axios.post(`${API_URL}/settings`, settings, { headers: authHeaders });
    return response.data;
  } catch (error) {
    logger.error("Save settings API Error:", error);
    return { status: "error" };
  }
};
