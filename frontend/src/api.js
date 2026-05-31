import axios from 'axios';
import { logger } from './utils/logger';

export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
// Prefer Node-style env when running tests (Vitest sets process.env.VITEST),
// otherwise prefer Vite's import.meta.env for browser/dev usage.
const isTest = typeof process !== 'undefined' && Boolean(process.env && process.env.VITEST);
let envApiKey = '';
if (isTest) {
  envApiKey = (typeof process !== 'undefined' && process.env && process.env.VITE_MEERO_API_KEY) || '';
} else {
  envApiKey = (typeof process !== 'undefined' && process.env && process.env.VITE_MEERO_API_KEY) || import.meta.env?.VITE_MEERO_API_KEY || '';
}
export const API_KEY = envApiKey || '';

const authHeaders = API_KEY ? { 'x-meero-api-key': API_KEY } : {};

export const sendCommand = async (command, options = {}) => {
  try {
    const response = await axios.post(`${API_URL}/command`, {
      command,
      mode: 'voice',
      confirm: Boolean(options.confirm),
      pending_command: options.pendingCommand || null,
    }, { headers: authHeaders });
    // Notify UI that server is reachable
    try { window.dispatchEvent(new CustomEvent('meero:server-reachable', { detail: { reachable: true } })); } catch (e) { /* ignore */ }
    logger.log("[API] /command response:", response.data);
    return response.data;
  } catch (error) {
    logger.error("API Error:", error);
    try { window.dispatchEvent(new CustomEvent('meero:server-reachable', { detail: { reachable: false } })); } catch (e) { /* ignore */ }
    return { response: "I cannot reach the server.", action_status: "error" };
  }
};

export const getHealth = async () => {
  try {
    const response = await axios.get(`${API_URL}/debug/health`, { headers: authHeaders });
    try { window.dispatchEvent(new CustomEvent('meero:server-reachable', { detail: { reachable: true } })); } catch (e) { }
    return { ...response.data, detailed: true };
  } catch (debugError) {
    logger.log("Debug health unavailable; falling back to public health.", debugError);
    try {
      const response = await axios.get(`${API_URL}/health`);
      try { window.dispatchEvent(new CustomEvent('meero:server-reachable', { detail: { reachable: true } })); } catch (e) { }
      return { ...response.data, detailed: false };
    } catch (error) {
      logger.error("Health API Error:", error);
      try { window.dispatchEvent(new CustomEvent('meero:server-reachable', { detail: { reachable: false } })); } catch (e) { }
      return null;
    }
  }
};

export const getSettings = async () => {
  try {
    const response = await axios.get(`${API_URL}/settings`, { headers: authHeaders });
    try { window.dispatchEvent(new CustomEvent('meero:server-reachable', { detail: { reachable: true } })); } catch (e) { }
    return response.data;
  } catch (error) {
    logger.error("Settings API Error:", error);
    try { window.dispatchEvent(new CustomEvent('meero:server-reachable', { detail: { reachable: false } })); } catch (e) { }
    return {};
  }
};

export const saveSettings = async (settings) => {
  try {
    const response = await axios.post(`${API_URL}/settings`, settings, { headers: authHeaders });
    try { window.dispatchEvent(new CustomEvent('meero:server-reachable', { detail: { reachable: true } })); } catch (e) { }
    return response.data;
  } catch (error) {
    logger.error("Save settings API Error:", error);
    try { window.dispatchEvent(new CustomEvent('meero:server-reachable', { detail: { reachable: false } })); } catch (e) { }
    return { status: "error" };
  }
};
