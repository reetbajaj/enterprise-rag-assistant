import { useState, useEffect } from "react";
import { AuthContext } from "./AuthContextBase";
import { loginUser, registerUser, getCurrentUser, logoutUser } from "../services/authService";

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const initAuth = async () => {
      const savedToken = localStorage.getItem("token");
      if (savedToken) {
        try {
          const userData = await getCurrentUser();
          if (isMounted) {
            setUser(userData);
            setToken(savedToken);
          }
        } catch (error) {
          console.warn("Session expired or invalid token:", error);
          logoutUser();
          if (isMounted) {
            setUser(null);
            setToken(null);
          }
        }
      } else {
        if (isMounted) {
          setUser(null);
          setToken(null);
        }
      }
      if (isMounted) {
        setLoading(false);
      }
    };

    initAuth();
    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (email, password) => {
    const data = await loginUser(email, password);
    if (data.access_token) {
      localStorage.setItem("token", data.access_token);
      setToken(data.access_token);
      if (data.user) {
        setUser(data.user);
      } else {
        const userData = await getCurrentUser();
        setUser(userData);
      }
      return data;
    }
    throw new Error("No access token returned");
  };

  const register = async (email, password) => {
    const data = await registerUser(email, password);
    if (data.access_token) {
      localStorage.setItem("token", data.access_token);
      setToken(data.access_token);
      setUser({ id: data.user_id, email: data.email });
      return data;
    }
    return data;
  };

  const logout = () => {
    logoutUser();
    setUser(null);
    setToken(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        isAuthenticated: !!token,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
