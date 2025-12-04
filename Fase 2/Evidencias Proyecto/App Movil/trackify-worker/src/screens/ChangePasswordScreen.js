// src/screens/ChangePasswordScreen.js
import React, { useState, useContext } from "react";
import {
  SafeAreaView,
  View,
  Text,
  TextInput,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from "react-native";
import { api } from "../api";
import { AuthContext } from "../auth";

export default function ChangePasswordScreen({ navigation }) {
  const { logout } = useContext(AuthContext);

  const [newPassword1, setNewPassword1] = useState("");
  const [newPassword2, setNewPassword2] = useState("");
  const [saving, setSaving] = useState(false);

  const handleChangePassword = async () => {
    if (saving) return;

    if (!newPassword1 || !newPassword2) {
      Alert.alert("Atención", "Debes ingresar ambas contraseñas.");
      return;
    }
    if (newPassword1 !== newPassword2) {
      Alert.alert("Atención", "Las contraseñas no coinciden.");
      return;
    }
    if (newPassword1.length < 8) {
      Alert.alert(
        "Atención",
        "La contraseña debe tener al menos 8 caracteres."
      );
      return;
    }

    try {
      setSaving(true);
      const { data } = await api.post("/api/password/change/", {
        new_password1: newPassword1,
        new_password2: newPassword2,
      });

      setNewPassword1("");
      setNewPassword2("");

      Alert.alert(
        "Contraseña actualizada",
        "Tu contraseña se cambió correctamente. Deberás iniciar sesión de nuevo.",
        [
          {
            text: "Aceptar",
            onPress: () => {
              logout();
            },
          },
        ]
      );
    } catch (e) {
      console.log("Error cambio password:", e?.response?.data || e.message);
      const resp = e?.response?.data;
      const msg =
        (resp && resp.detail) ||
        (Array.isArray(resp?.errors) ? resp.errors.join("\n") : null) ||
        "No se pudo actualizar la contraseña.";
      Alert.alert("Error", msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.card}>
            <Text style={styles.title}>Cambiar contraseña</Text>
            <Text style={styles.subtitle}>
              Ingresa tu nueva contraseña. Debe cumplir las políticas de
              seguridad definidas por la empresa.
            </Text>

            <Text style={styles.label}>Nueva contraseña</Text>
            <TextInput
              style={styles.input}
              secureTextEntry
              value={newPassword1}
              onChangeText={setNewPassword1}
              placeholder="Ingresa tu nueva contraseña"
            />

            <Text style={styles.label}>Confirmar nueva contraseña</Text>
            <TextInput
              style={styles.input}
              secureTextEntry
              value={newPassword2}
              onChangeText={setNewPassword2}
              placeholder="Vuelve a escribir la nueva contraseña"
            />

            <TouchableOpacity
              style={[styles.btn, saving && styles.btnDisabled]}
              onPress={handleChangePassword}
              disabled={saving}
            >
              {saving ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.btnText}>Actualizar contraseña</Text>
              )}
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.linkBtn}
              onPress={() => navigation.goBack()}
            >
              <Text style={styles.linkText}>Volver al perfil</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f3f4f6",
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 24,
  },
  card: {
    backgroundColor: "#ffffff",
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: "#e5e7eb",
    marginTop: 8,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 1,
  },
  title: {
    fontSize: 18,
    fontWeight: "700",
    color: "#111827",
  },
  subtitle: {
    marginTop: 4,
    fontSize: 13,
    color: "#6b7280",
    marginBottom: 16,
  },
  label: {
    fontSize: 13,
    color: "#374151",
    marginBottom: 6,
    marginTop: 10,
  },
  input: {
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 10,
    padding: 12,
    fontSize: 16,
    backgroundColor: "#fff",
  },
  btn: {
    marginTop: 20,
    paddingVertical: 12,
    borderRadius: 999,
    backgroundColor: "#0ea5e9",
    alignItems: "center",
    justifyContent: "center",
  },
  btnDisabled: {
    opacity: 0.7,
  },
  btnText: {
    color: "#ffffff",
    fontWeight: "600",
    fontSize: 15,
  },
  linkBtn: {
    marginTop: 16,
    alignItems: "center",
  },
  linkText: {
    fontSize: 13,
    color: "#0ea5e9",
  },
});
