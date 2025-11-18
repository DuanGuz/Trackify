// App.js
import React, { useEffect } from "react";
import * as Notifications from "expo-notifications";

import { AuthProvider } from "./src/auth";
import AppNavigator from "./src/AppNavigator";
import { navigate } from "./src/navigationRef";

// Cómo se muestran las notificaciones en foreground
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

// función que decide a dónde ir según el payload
function handleNotificationNavigation(data) {
  if (!data) return;
  const tipo = data.tipo;

  if (tipo === "tarea" && data.tarea_id) {
    // Ir al detalle de la tarea
    navigate("DetalleTarea", { taskId: data.tarea_id });
  } else if (tipo === "evaluacion") {
    // Ir a la pestaña de Evaluaciones
    navigate("Evaluaciones");
  } else if (tipo === "notificaciones") {
    // Por si algún día quieres mandar algo genérico
    navigate("Notificaciones");
  }
}

export default function App() {
  useEffect(() => {
    // 1) Si la app estaba cerrada y se abrió desde una notificación:
    (async () => {
      const lastResponse =
        await Notifications.getLastNotificationResponseAsync();
      if (lastResponse?.notification?.request?.content?.data) {
        handleNotificationNavigation(
          lastResponse.notification.request.content.data
        );
      }
    })();

    // 2) Listener cuando el usuario toca una notificación (foreground/background)
    const sub = Notifications.addNotificationResponseReceivedListener(
      (response) => {
        const data =
          response?.notification?.request?.content?.data || null;
        handleNotificationNavigation(data);
      }
    );

    return () => {
      sub.remove();
    };
  }, []);

  return (
    <AuthProvider>
      <AppNavigator />
    </AuthProvider>
  );
}
