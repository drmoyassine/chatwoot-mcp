import { createContext, useContext, useState, useEffect, useCallback } from "react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // null = checking, false = not authenticated, object = authenticated
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem("mcp_token") || "");

  const axiosAuth = useCallback(() => {
    const instance = axios.create({ baseURL: BACKEND_URL, withCredentials: true });
    if (token) {
      instance.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    }
    // Auto-logout on 401
    instance.interceptors.response.use(
      (r) => r,
      (err) => {
        if (err.response?.status === 401 && !err.config.url?.includes("/auth/login")) {
          setUser(false);
          setToken("");
          localStorage.removeItem("mcp_token");
        }
        return Promise.reject(err);
      }
    );
    return instance;
  }, [token]);

  useEffect(() => {
    if (!token) {
      setUser(false);
      return;
    }
    const api = axiosAuth();
    api.get("/api/auth/me")
      .then((r) => setUser(r.data))
      .catch(() => {
        setUser(false);
        setToken("");
        localStorage.removeItem("mcp_token");
      });
  }, [token, axiosAuth]);

  const login = async (email, password) => {
    const resp = await axios.post(`${BACKEND_URL}/api/auth/login`, { email, password }, { withCredentials: true });
    const { token: newToken, email: userEmail } = resp.data;
    localStorage.setItem("mcp_token", newToken);
    setToken(newToken);
    setUser({ email: userEmail });
    return resp.data;
  };

  const logout = async () => {
    try {
      await axiosAuth().post("/api/auth/logout");
    } catch {}
    localStorage.removeItem("mcp_token");
    setToken("");
    setUser(false);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, axiosAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
