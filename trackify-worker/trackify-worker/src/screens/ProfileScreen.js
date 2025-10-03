import React, { useEffect, useState, useContext } from "react";
import {
  SafeAreaView,
  View,
  Text,
  TextInput,
  Button,
  StyleSheet,
  Image,
  Platform,
  KeyboardAvoidingView,
  ScrollView,
  TouchableWithoutFeedback,
  Keyboard,
  Alert,
  Dimensions,
  ActivityIndicator,
} from "react-native";
import { api } from "../api";
import { AuthContext } from "../auth";

const { width } = Dimensions.get("window");
const KEYBOARD_VERTICAL_OFFSET = Platform.OS === "ios" ? 80 : 0;

export default function ProfileScreen() {
  const { logout } = useContext(AuthContext);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [perfil, setPerfil] = useState({
    username: "",
    email: "",
    telefono: "",
    primer_nombre: "",
    segundo_nombre: "",
    primer_apellido: "",
    segundo_apellido: "",
    rut: "",
  });

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const { data } = await api.get("/api/me/");
        if (!mounted) return;
        setPerfil((p) => ({ ...p, ...data }));
      } catch (e) {
        Alert.alert("Error", "No se pudo cargar el perfil.");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const onChange = (k, v) => setPerfil((p) => ({ ...p, [k]: v }));

  const onSave = async () => {
    try {
      setSaving(true);
      const payload = {
        email: perfil.email ?? "",
        telefono: perfil.telefono ?? "",
      };
      await api.patch("/api/me/", payload);
      Alert.alert("Éxito", "Perfil actualizado.");
      Keyboard.dismiss();
    } catch (e) {
      Alert.alert("Error", "No se pudo guardar. Revisa los datos.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.center}>
        <ActivityIndicator />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        keyboardVerticalOffset={KEYBOARD_VERTICAL_OFFSET}
      >
        <TouchableWithoutFeedback onPress={Keyboard.dismiss} accessible={false}>
          <ScrollView
            contentContainerStyle={styles.scrollContent}
            keyboardShouldPersistTaps="handled"
          >
            {/* Cabecera */}
            <View style={styles.header}>
              <Image
                source={require("../../assets/logo.png")}
                style={styles.avatar}
                resizeMode="contain"
              />
              <Text style={styles.name}>
                {`${perfil.primer_nombre || ""} ${perfil.primer_apellido || ""}`.trim() ||
                  perfil.username}
              </Text>
              {perfil.rut ? <Text style={styles.meta}>RUT: {perfil.rut}</Text> : null}
            </View>

            {/* Campos editables */}
            <View style={styles.form}>
              <Text style={styles.label}>Usuario</Text>
              <TextInput style={styles.input} value={perfil.username} editable={false} />

              <Text style={styles.label}>Email</Text>
              <TextInput
                style={styles.input}
                value={perfil.email}
                onChangeText={(v) => onChange("email", v)}
                autoCapitalize="none"
                keyboardType="email-address"
                returnKeyType="next"
              />

              <Text style={styles.label}>Teléfono</Text>
              <TextInput
                style={styles.input}
                value={perfil.telefono}
                onChangeText={(v) => onChange("telefono", v)}
                keyboardType="phone-pad"
                returnKeyType="done"
                onSubmitEditing={onSave}
              />

              <Text style={styles.label}>Primer nombre</Text>
              <TextInput style={styles.input} value={perfil.primer_nombre} editable={false} />

              <Text style={styles.label}>Segundo nombre</Text>
              <TextInput style={styles.input} value={perfil.segundo_nombre} editable={false} />

              <Text style={styles.label}>Primer apellido</Text>
              <TextInput style={styles.input} value={perfil.primer_apellido} editable={false} />

              <Text style={styles.label}>Segundo apellido</Text>
              <TextInput style={styles.input} value={perfil.segundo_apellido} editable={false} />

              <View style={styles.btnWrap}>
                <Button
                  title={saving ? "Guardando..." : "Guardar cambios"}
                  onPress={onSave}
                  disabled={saving}
                />
              </View>

              <View style={styles.btnWrap}>
                <Button title="Cerrar sesión" color="red" onPress={logout} />
              </View>
            </View>
          </ScrollView>
        </TouchableWithoutFeedback>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#fff" },
  flex: { flex: 1 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: "#fff" },
  scrollContent: {
    flexGrow: 1,
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 20,
  },
  header: { alignItems: "center", marginTop: 8, marginBottom: 10 },
  avatar: { width: width * 0.35, height: width * 0.35, marginBottom: 8 },
  name: { fontSize: 18, fontWeight: "600", color: "#111827" },
  meta: { fontSize: 13, color: "#6b7280", marginTop: 4 },
  form: { marginTop: 10 },
  label: { fontSize: 13, color: "#374151", marginBottom: 6, marginTop: 10 },
  input: {
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 10,
    padding: 12,
    fontSize: 16,
    backgroundColor: "#fff",
  },
  btnWrap: { marginTop: 16 },
});
