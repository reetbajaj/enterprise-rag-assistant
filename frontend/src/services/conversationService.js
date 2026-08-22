import api from "../api/axios";

export const getConversations = async () => {
  const response = await api.get("/conversations");
  return response.data;
};

export const createConversation = async (title = "New Conversation") => {
  const response = await api.post("/conversations", { title });
  return response.data;
};

export const getConversation = async (conversationId) => {
  const response = await api.get(`/conversations/${conversationId}`);
  return response.data;
};

export const renameConversation = async (conversationId, title) => {
  const response = await api.patch(`/conversations/${conversationId}`, { title });
  return response.data;
};

export const deleteConversation = async (conversationId) => {
  const response = await api.delete(`/conversations/${conversationId}`);
  return response.data;
};

export const clearAllConversations = async () => {
  const response = await api.delete("/conversations");
  return response.data;
};
