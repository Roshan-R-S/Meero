import axios from 'axios';

const API_URL = 'http://localhost:8000';

export const sendCommand = async (command) => {
  try {
    const response = await axios.post(`${API_URL}/command`, { command, mode: 'voice' });
    return response.data;
  } catch (error) {
    console.error("API Error:", error);
    return { response: "I cannot reach the server.", action_status: "error" };
  }
};
