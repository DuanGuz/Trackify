// src/screens/TaskDetailScreen.js
import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  ActivityIndicator,
  StyleSheet,
  Alert,
  TextInput,
  TouchableOpacity,
  ScrollView,
} from "react-native";
import { api } from "../api";

const ESTADOS = ["Pendiente", "En progreso", "Atrasada", "Finalizada"];

const ESTADO_COLORS = {
  Pendiente: "#f97316", // naranja
  "En progreso": "#0ea5e9", // celeste
  Atrasada: "#ef4444", // rojo
  Finalizada: "#22c55e", // verde
};

export default function TaskDetailScreen({ route }) {
  const { task } = route.params || {};
  const [detalle, setDetalle] = useState(null);      // 👈 aquí guardamos lo que viene del API detalle
  const [estado, setEstado] = useState(task?.estado || "Pendiente");
  const [comentario, setComentario] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Cargar detalle desde el backend
  const fetchDetalle = async () => {
    if (!task?.id) return;
    try {
      setLoading(true);
      const { data } = await api.get(`/api/tareas/${task.id}/`);
      setDetalle(data);
      // Sincronizamos el estado con lo que venga del backend
      if (data?.estado) {
        setEstado(data.estado);
      }
    } catch (e) {
      console.log("Error cargando detalle tarea:", e?.response?.data || e.message);
      Alert.alert("Error", "No se pudo cargar el detalle de la tarea.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetalle();
  }, [task?.id]);

  if (!task) {
    return (
      <View style={styles.center}>
        <Text>No se encontró la tarea.</Text>
      </View>
    );
  }

  const handleUpdateState = async () => {
    if (!estado) {
      return Alert.alert("Falta estado", "Selecciona un estado");
    }

    try {
      setSaving(true);
      await api.patch(`/api/tareas/${task.id}/estado/`, {
        estado,
        comentario: comentario?.trim() || null,
      });

      Alert.alert("OK", "Estado actualizado");

      // Limpiar input de comentario
      setComentario("");

      // Volvemos a cargar el detalle (estado + comentarios actualizados)
      await fetchDetalle();
    } catch (e) {
      console.log("Error actualizando estado:", e?.response?.data || e.message);
      const resp = e?.response?.data;
      const msg =
        (resp && resp.detail) ||
        "No se pudo actualizar el estado. Revisa tu conexión o inténtalo más tarde.";
      Alert.alert("Error", msg);
    } finally {
      setSaving(false);
    }
  };

  if (loading && !detalle) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
        <Text style={{ marginTop: 8 }}>Cargando detalle…</Text>
      </View>
    );
  }

  const estadoColor = ESTADO_COLORS[estado] || "#64748b";
  const titulo = detalle?.titulo || task.titulo;
  const descripcion = detalle?.descripcion ?? task.descripcion;
  const fechaLimite =
    detalle?.fecha_limite_fmt || detalle?.fecha_limite || task.fecha_limite_fmt || task.fecha_limite;
  const creada =
    detalle?.created_at_fmt || detalle?.created_at || task.created_at_fmt || task.created_at;
  const comentarios = detalle?.comentarios || [];

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={{ paddingBottom: 24 }}>
        <View style={styles.card}>
          {/* Título + estado actual */}
          <View style={styles.headerRow}>
            <Text style={styles.title} numberOfLines={2}>
              {titulo}
            </Text>
            <View
              style={[
                styles.badge,
                { backgroundColor: estadoColor, borderColor: estadoColor },
              ]}
            >
              <Text style={styles.badgeText}>{estado}</Text>
            </View>
          </View>

          {/* Descripción */}
          <Text style={styles.label}>Descripción</Text>
          <Text style={styles.paragraph}>
            {descripcion || "Sin descripción."}
          </Text>

          {/* Fechas */}
          <View style={styles.metaBox}>
            {fechaLimite ? (
              <Text style={styles.meta}>Fecha límite: {fechaLimite}</Text>
            ) : null}
            {creada ? <Text style={styles.meta}>Creada: {creada}</Text> : null}
          </View>

          {/* Selector de estado */}
          <Text style={[styles.label, { marginTop: 16 }]}>Cambiar estado</Text>
          <View style={styles.estadoBox}>
            {ESTADOS.map((e) => {
              const color = ESTADO_COLORS[e] || "#64748b";
              const selected = estado === e;
              return (
                <TouchableOpacity
                  key={e}
                  onPress={() => setEstado(e)}
                  style={[
                    styles.estadoPill,
                    selected && {
                      backgroundColor: color,
                      borderColor: color,
                    },
                  ]}
                >
                  <Text
                    style={[
                      styles.estadoPillText,
                      selected && { color: "#ffffff" },
                    ]}
                  >
                    {e}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>

          {/* Comentarios existentes */}
          <Text style={[styles.label, { marginTop: 16 }]}>Comentarios</Text>
          {comentarios.length === 0 ? (
            <Text style={styles.commentsEmpty}>
              Aún no hay comentarios en esta tarea.
            </Text>
          ) : (
            <View style={{ maxHeight: 250 }}>
              <ScrollView
                nestedScrollEnabled
                style={styles.commentsBox}
                contentContainerStyle={{ paddingBottom: 8 }}
              >
                {comentarios.map((c) => (
                  <View key={c.id} style={styles.commentItem}>
                    <View style={styles.commentHeader}>
                      <Text style={styles.commentAuthor}>
                        {c.usuario_nombre || "Usuario"}
                      </Text>
                      {!!c.created_at_fmt && (
                        <Text style={styles.commentDate}>{c.created_at_fmt}</Text>
                      )}
                    </View>
                    <Text style={styles.commentText}>{c.contenido}</Text>
                  </View>
                ))}
              </ScrollView>
            </View>
          )}

          {/* Nuevo comentario */}
          <Text style={[styles.label, { marginTop: 16 }]}>
            Añadir comentario (opcional)
          </Text>
          <TextInput
            style={styles.input}
            placeholder="Añade un comentario…"
            value={comentario}
            onChangeText={setComentario}
            multiline
          />

          {/* Botón guardar */}
          <TouchableOpacity
            style={[styles.button, saving && styles.buttonDisabled]}
            onPress={handleUpdateState}
            disabled={saving}
          >
            {saving ? (
              <ActivityIndicator color="#ffffff" />
            ) : (
              <Text style={styles.buttonText}>Actualizar estado</Text>
            )}
          </TouchableOpacity>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  // Fondo tipo dashboard Trackify
  container: {
    flex: 1,
    backgroundColor: "#f3f4f6",
    padding: 12,
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  // Card central
  card: {
    padding: 16,
    backgroundColor: "#ffffff",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#e5e7eb",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    marginBottom: 8,
  },
  title: {
    flex: 1,
    fontSize: 18,
    fontWeight: "700",
    color: "#111827",
    marginRight: 8,
  },
  label: {
    fontWeight: "600",
    marginTop: 8,
    marginBottom: 4,
    color: "#111827",
  },
  paragraph: {
    color: "#4b5563",
    lineHeight: 20,
    fontSize: 14,
  },
  metaBox: {
    marginTop: 10,
    gap: 2,
  },
  meta: {
    fontSize: 12,
    color: "#6b7280",
  },
  // Badge de estado en el header
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    borderWidth: 1,
  },
  badgeText: {
    fontSize: 12,
    fontWeight: "600",
    color: "#ffffff",
  },
  // Píldoras de estados
  estadoBox: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    marginVertical: 8,
  },
  estadoPill: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "#d1d5db",
    backgroundColor: "#ffffff",
  },
  estadoPillText: {
    fontSize: 13,
    color: "#111827",
  },
  // Comentarios
  commentsBox: {
    marginTop: 4,
    borderWidth: 1,
    borderColor: "#e5e7eb",
    borderRadius: 8,
    padding: 8,
    backgroundColor: "#f9fafb",
    gap: 8,
  },
  commentsEmpty: {
    fontSize: 13,
    color: "#6b7280",
    fontStyle: "italic",
  },
  commentItem: {
    paddingVertical: 4,
    borderBottomWidth: 1,
    borderBottomColor: "#e5e7eb",
  },
  commentHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 2,
  },
  commentAuthor: {
    fontSize: 13,
    fontWeight: "600",
    color: "#111827",
  },
  commentDate: {
    fontSize: 11,
    color: "#9ca3af",
  },
  commentText: {
    fontSize: 13,
    color: "#4b5563",
  },
  // Comentario nuevo
  input: {
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 8,
    padding: 10,
    minHeight: 70,
    textAlignVertical: "top",
    fontSize: 14,
    marginTop: 2,
    backgroundColor: "#ffffff",
  },
  // Botón principal
  button: {
    marginTop: 16,
    paddingVertical: 12,
    borderRadius: 999,
    backgroundColor: "#0ea5e9",
    alignItems: "center",
    justifyContent: "center",
  },
  buttonDisabled: {
    opacity: 0.7,
  },
  buttonText: {
    color: "#ffffff",
    fontWeight: "600",
    fontSize: 15,
  },
});
