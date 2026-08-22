import api from "../api/axios";

export const registerUser = async (email, password) => {
  const response = await api.post("/auth/register", {
    email,
    password,
  });
  return response.data;
};

export const loginUser = async (email, password) => {
  // Support standard JSON login (backend supports both JSON and form data)
  const response = await api.post("/auth/login", {
    email,
    password,
  });
  return response.data;
};

export const getCurrentUser = async () => {
  const response = await api.get("/auth/me");
  return response.data;
};

export const logoutUser = () => {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
};