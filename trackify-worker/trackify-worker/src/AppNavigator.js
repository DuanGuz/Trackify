// src/AppNavigator.js
import React, { useContext, useEffect, useState } from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";

import { AuthContext } from "./auth";

import LoginScreen from "./screens/LoginScreen";
import TasksScreen from "./screens/TasksScreen";
import TaskDetailScreen from "./screens/TaskDetailScreen";
import EvaluationsScreen from "./screens/EvaluationsScreen";
import ProfileScreen from "./screens/ProfileScreen";
import ChangePasswordScreen from "./screens/ChangePasswordScreen";
import NotificationsScreen from "./screens/NotificationsScreen";
import SplashOverlay from "./components/SplashOverlay";

const Stack = createNativeStackNavigator();
const Tabs = createBottomTabNavigator();

function MainTabs() {
  return (
    <Tabs.Navigator>
      <Tabs.Screen
        name="Tareas"
        component={TasksScreen}
        options={{
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="list" size={size} color={color} />
          ),
          headerShown: true,
          title: "Tareas",
        }}
      />
      <Tabs.Screen
        name="Evaluaciones"
        component={EvaluationsScreen}
        options={{
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="clipboard" size={size} color={color} />
          ),
          headerShown: true,
          title: "Evaluaciones",
        }}
      />
      <Tabs.Screen
        name="Notificaciones"
        component={NotificationsScreen}
        options={{
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="notifications" size={size} color={color} />
          ),
          headerShown: true,
          title: "Notificaciones",
        }}
      />
      <Tabs.Screen
        name="PerfilTab"
        component={ProfileScreen}
        options={{
          tabBarLabel: "Perfil",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="person" size={size} color={color} />
          ),
          headerShown: true,
          title: "Perfil",
        }}
      />
    </Tabs.Navigator>
  );
}

export default function AppNavigator() {
  const { token, bootstrapped } = useContext(AuthContext);
  const [showSplash, setShowSplash] = useState(true);
  const [splashMounted, setSplashMounted] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => setShowSplash(false), 2200);
    return () => clearTimeout(t);
  }, []);

  const isLoading = !bootstrapped || showSplash;

  return (
    <>
      <NavigationContainer>
        {token ? (
          <Stack.Navigator>
            <Stack.Screen
              name="Home"
              component={MainTabs}
              options={{ headerShown: false }}
            />
            <Stack.Screen
              name="DetalleTarea"
              component={TaskDetailScreen}
              options={{ title: "Detalle de Tarea" }}
            />
            <Stack.Screen
              name="ChangePassword"
              component={ChangePasswordScreen}
              options={{ title: "Cambiar contraseña" }}
            />
          </Stack.Navigator>
        ) : (
          <Stack.Navigator>
            <Stack.Screen
              name="Login"
              component={LoginScreen}
              options={{ title: "Ingresar" }}
            />
          </Stack.Navigator>
        )}
      </NavigationContainer>

      {splashMounted && (
        <SplashOverlay
          visible={isLoading}
          onHidden={() => setSplashMounted(false)}
        />
      )}
    </>
  );
}
