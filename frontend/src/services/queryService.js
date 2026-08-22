import api from "../api/axios";

export const askQuestion = async (question, conversationId = null) => {
  const payload = { question };
  if (conversationId) {
    payload.conversation_id = conversationId;
  }
  const response = await api.post("/query", payload);
  return response.data;
};

export const getHistory = async () => {
  const response = await api.get("/history");
  return response.data;
};

export const clearHistory = async () => {
  const response = await api.delete("/history");
  return response.data;
};