import api from "../api/axios";

export const getDocuments = async () => {
  const response = await api.get("/documents");
  return response.data;
};

export const getSingleDocument = async (documentId) => {
  const response = await api.get(`/documents/${documentId}`);
  return response.data;
};

export const getDocumentStats = async () => {
  const response = await api.get("/documents/stats");
  return response.data;
};

export const deleteDocument = async (documentId) => {
  const response = await api.delete(`/documents/${documentId}`);
  return response.data;
};