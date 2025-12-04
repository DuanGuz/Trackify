import React, { useEffect, useState, useContext } from "react";
import {
  SafeAreaView,
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { api } from "../api";
import { AuthContext } from "../auth";

function formatRut(rutRaw) {
  if (!rutRaw) return "";
  let rut = rutRaw.replace(/\./g, "").replace(/-/g, "").toUpperCase();
  if (rut.length < 2) return rut;

  const body = rut.slice(0, -1);
  const dv = rut.slice(-1);

  // agregar puntos cada 3 dígitos
  const bodyFmt = body.replace(/\B(?=(\d{3})+(?!\d))/g, ".");

  return `${bodyFmt}-${dv}`;
}

export default function ProfileScreen({ navigation }) {
  const { logout } = useContext(AuthContext);

  const [perfil, setPerfil] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchProfile = async () => {
    try {
      const { data } = await api.get("/api/me/");
      setPerfil(data);
    } catch (e) {
      console.log("Error perfil:", e?.response?.data || e.message);
      // aquí podrías poner un Alert si quieres
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  if (loading) {
    return (
      <SafeAreaView style={styles.fullCenter}>
        <ActivityIndicator size="large" />
        <Text style={{ marginTop: 8 }}>Cargando perfil…</Text>
      </SafeAreaView>
    );
  }

  if (!perfil) {
    return (
      <SafeAreaView style={styles.fullCenter}>
        <Text>No se pudo cargar tu perfil.</Text>
        <TouchableOpacity
          style={[styles.btn, styles.btnPrimary, { marginTop: 12 }]}
          onPress={fetchProfile}
        >
          <Text style={styles.btnPrimaryText}>Reintentar</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  const nombreCompleto = [
    perfil.primer_nombre,
    perfil.segundo_nombre,
    perfil.primer_apellido,
    perfil.segundo_apellido,
  ]
    .filter(Boolean)
    .join(" ");

  const iniciales = (
    (perfil.primer_nombre?.[0] || "") + (perfil.primer_apellido?.[0] || "")
  ).toUpperCase();

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
          {/* Card de cabecera (avatar + nombre) */}
          <View style={[styles.card, styles.cardHeader]}>
            <View style={styles.avatarCircle}>
              <Text style={styles.avatarText}>
                {iniciales || perfil.username?.[0]?.toUpperCase() || "?"}
              </Text>
            </View>
            <Text style={styles.name}>
              {nombreCompleto || perfil.username}
            </Text>
            <Text style={styles.subName}>Usuario de Trackify Worker</Text>
          </View>

          {/* Card de datos de acceso (solo lectura) */}
          <View style={styles.card}>
            <Text style={styles.sectionTitle}>Datos de acceso</Text>
            <Text style={styles.sectionHint}>
              Estos datos son administrados por RRHH. Desde la app solo puedes
              cambiar tu contraseña y cerrar sesión.
            </Text>

            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Usuario</Text>
              <Text style={styles.infoValue}>{perfil.username}</Text>
            </View>

            {!!perfil.email && (
              <View style={styles.infoRow}>
                <Text style={styles.infoLabel}>Email</Text>
                <Text style={styles.infoValue}>{perfil.email}</Text>
              </View>
            )}

            {!!perfil.telefono && (
              <View style={styles.infoRow}>
                <Text style={styles.infoLabel}>Teléfono</Text>
                <Text style={styles.infoValue}>{perfil.telefono}</Text>
              </View>
            )}

            {!!perfil.rut && (
              <View style={styles.infoRow}>
                <Text style={styles.infoLabel}>RUT</Text>
                <Text style={styles.infoValue}>{formatRut(perfil.rut)}</Text>
              </View>
            )}
          </View>

          {/* Card de acciones (cambiar contraseña / logout) */}
          <View style={styles.card}>
            <Text style={styles.sectionTitle}>Seguridad</Text>
            <Text style={styles.sectionHint}>
              Si crees que tu cuenta puede estar comprometida, cambia tu
              contraseña y vuelve a iniciar sesión.
            </Text>

            <View style={styles.actionsRow}>
              <TouchableOpacity
                style={[styles.btn, styles.btnPrimary]}
                onPress={() => navigation.navigate("ChangePassword")}
              >
                <Text style={styles.btnPrimaryText}>Cambiar contraseña</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.btn, styles.btnOutline]}
                onPress={logout}
              >
                <Text style={styles.btnOutlineText}>Cerrar sesión</Text>
              </TouchableOpacity>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  // Fondo tipo dashboard
  container: {
    flex: 1,
    backgroundColor: "#f3f4f6",
  },
  fullCenter: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 24,
  },

  // Cards
  card: {
    backgroundColor: "#ffffff",
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: "#e5e7eb",
    marginBottom: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 1,
  },
  cardHeader: {
    alignItems: "center",
    paddingTop: 24,
    paddingBottom: 20,
  },

  // Avatar y nombre
  avatarCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: "#111827",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 10,
  },
  avatarText: {
    color: "#fff",
    fontSize: 30,
    fontWeight: "700",
  },
  name: {
    fontSize: 20,
    fontWeight: "700",
    color: "#111827",
  },
  subName: {
    marginTop: 4,
    fontSize: 13,
    color: "#6b7280",
  },

  // Secciones
  sectionTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "#111827",
    marginBottom: 4,
  },
  sectionHint: {
    fontSize: 12,
    color: "#6b7280",
    marginBottom: 12,
  },

  infoRow: {
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: "#f3f4f6",
  },
  infoLabel: {
    fontSize: 12,
    color: "#6b7280",
    marginBottom: 2,
  },
  infoValue: {
    fontSize: 14,
    color: "#111827",
    fontWeight: "500",
  },

  // Acciones
  actionsRow: {
    flexDirection: "row",
    marginTop: 8,
    gap: 10,
  },
  btn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 999,
    alignItems: "center",
    justifyContent: "center",
  },
  btnPrimary: {
    backgroundColor: "#0ea5e9",
  },
  btnPrimaryText: {
    color: "#ffffff",
    fontWeight: "600",
    fontSize: 14,
  },
  btnOutline: {
    borderWidth: 1,
    borderColor: "#e11d48",
    backgroundColor: "#fff",
  },
  btnOutlineText: {
    color: "#e11d48",
    fontWeight: "600",
    fontSize: 14,
  },
});
