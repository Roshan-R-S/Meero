import axios from 'axios';

const API_URL = 'http://localhost:8000';

export const sendCommand = async (command, options = {}) => {
  try {
    const response = await axios.post(`${API_URL}/command`, {
      command,
      mode: 'voice',
      confirm: Boolean(options.confirm),
      pending_command: options.pendingCommand || null,
    });
    console.log("[API] /command response:", response.data);
    return response.data;
  } catch (error) {
    console.error("API Error:", error);
    return { response: "I cannot reach the server.", action_status: "error" };
  }
};
