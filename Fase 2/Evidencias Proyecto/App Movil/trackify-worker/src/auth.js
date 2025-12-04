// src/auth.js
import React, { createContext, useEffect, useState } from "react";
import * as SecureStore from "expo-secure-store";
import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import { api, setAuthToken } from "./api";

export const AuthContext = createContext({
  token: null,
  bootstrapped: false,
  login: async () => false,
  logout: async () => {},
});

// --- Helper: registra el token de Expo en tu backend ---
async function registerForPushTokenOnBackend() {
  try {
    if (!Device.isDevice) {
      console.log("Las notificaciones push requieren un dispositivo físico");
      return;
    }

    // Pedir permisos
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    if (existingStatus !== "granted") {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    if (finalStatus !== "granted") {
      console.log("Permiso de notificaciones no concedido");
      return;
    }

    // Obtener token de Expo
    const tokenData = await Notifications.getExpoPushTokenAsync();
    const expoPushToken = tokenData.data;
    console.log("Expo push token:", expoPushToken);

    // Enviar token a tu API (requiere estar autenticado)
    await api.post("/api/expo/register-token/", {
      expo_push_token: expoPushToken,
    });
  } catch (e) {
    console.log(
      "Error registrando push token:",
      e?.response?.data || e.message
    );
  }
}

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(null);
  const [bootstrapped, setBootstrapped] = useState(false);

  // Al iniciar la app: revisar si hay token guardado
  useEffect(() => {
    (async () => {
      try {
        const t = await SecureStore.getItemAsync("token");
        if (t) {
          setToken(t);
          setAuthToken(t);
          // Podrías registrar el push token aquí también si quieres
        }
      } finally {
        setBootstrapped(true);
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

      // una vez autenticado, registramos el push token
      await registerForPushTokenOnBackend();

      return true;
    } catch (e) {
      console.log("Error login:", e?.response?.data || e.message);
      return false;
    }
  };

  const logout = async () => {
    try {
      await SecureStore.deleteItemAsync("token");
    } catch {}
    setToken(null);
    setAuthToken(null);
  };

  return (
    <AuthContext.Provider value={{ token, bootstrapped, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
