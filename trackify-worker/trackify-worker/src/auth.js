// src/auth.js
import * as SecureStore from "expo-secure-store";
import React, { createContext, useEffect, useState } from "react";
import { api, setAuthToken } from "./api";

export const AuthContext = createContext({
  token: null,
  bootstrapped: false,
  login: async () => false,
  logout: async () => {},
});

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(null);
  const [bootstrapped, setBootstrapped] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const t = await SecureStore.getItemAsync("token");
        if (t) {
          setToken(t);
          setAuthToken(t);
        }
      } finally {
        setBootstrapped(true); // <- ya sabemos si hay token o no
      }
    })();
  }, []);

  const login = async (username, password) => {
    try {
      const { data } = await api.post("/api/token/", { username, password });
      const access = data?.access;
      if (!access) return false;
      await SecureStore.setItemAsync("token", access);
      setToken(access);
      setAuthToken(access);
      return true;
    } catch {
      return false;
    }
  };

  const logout = async () => {
    await SecureStore.deleteItemAsync("token");
    setToken(null);
    setAuthToken(null);
  };

  return (
    <AuthContext.Provider value={{ token, bootstrapped, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
