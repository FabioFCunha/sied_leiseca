import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../api/client.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem("user");
    const token = localStorage.getItem("accessToken");
    if (!raw || !token) {
      return null;
    }
    try {
      return JSON.parse(raw);
    } catch {
      localStorage.removeItem("accessToken");
      localStorage.removeItem("refreshToken");
      localStorage.removeItem("user");
      return null;
    }
  });

  const login = (payload) => {
    localStorage.setItem("accessToken", payload.access);
    localStorage.setItem("refreshToken", payload.refresh);
    localStorage.setItem("user", JSON.stringify(payload.user));
    setUser(payload.user);
  };

  const logout = () => {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    localStorage.removeItem("user");
    setUser(null);
  };

  useEffect(() => {
    const token = localStorage.getItem("accessToken");
    if (!token) return;
    api("/auth/me/", { redirectOnUnauthorized: false })
      .then((currentUser) => {
        localStorage.setItem("user", JSON.stringify(currentUser));
        setUser(currentUser);
      })
      .catch(() => {
        logout();
        if (window.location.pathname !== "/login") {
          window.location.href = "/login";
        }
      });
  }, []);

  const updateUser = (updatedUser) => {
    localStorage.setItem("user", JSON.stringify(updatedUser));
    setUser(updatedUser);
  };

  const value = useMemo(() => ({ user, login, logout, updateUser, isAuthenticated: Boolean(user) }), [user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
