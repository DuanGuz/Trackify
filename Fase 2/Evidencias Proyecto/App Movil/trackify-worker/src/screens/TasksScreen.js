// src/screens/TasksScreen.js
import React, {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  SafeAreaView,
  View,
  Text,
  FlatList,
  RefreshControl,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { api } from "../api";

const ESTADOS = ["Todos", "Pendiente", "En progreso", "Atrasada", "Finalizada"];

const ESTADO_COLORS = {
  Pendiente: "#f97316", // naranja
  "En progreso": "#0ea5e9", // celeste
  Atrasada: "#ef4444", // rojo
  Finalizada: "#22c55e", // verde
};

export default function TasksScreen({ navigation }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [search, setSearch] = useState("");
  const [estadoFilter, setEstadoFilter] = useState("Todos");

  const fetchTasks = async () => {
    try {
      const { data } = await api.get("/api/tareas/mias/");
      setTasks(Array.isArray(data) ? data : []);
    } catch (e) {
      console.log("Error cargando tareas:", e?.response?.data || e.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      fetchTasks();
    }, [])
  );

  const onRefresh = () => {
    setRefreshing(true);
    fetchTasks();
  };

  // === Filtro por texto + estado ===
  const filteredTasks = useMemo(() => {
    const term = search.trim().toLowerCase();

    return tasks.filter((t) => {
      // filtro por estado
      if (estadoFilter !== "Todos" && t.estado !== estadoFilter) {
        return false;
      }

      // filtro por texto
      if (!term) return true;
      const haystack = [
        t.titulo || "",
        t.descripcion || "",
        t.estado || "",
      ]
        .join(" ")
        .toLowerCase();

      return haystack.includes(term);
    });
  }, [tasks, search, estadoFilter]);

  // === Render de cada fila (tipo fila de tabla) ===
  const renderItem = ({ item }) => {
    const color = ESTADO_COLORS[item.estado] || "#64748b";
    const fecha = item.fecha_limite_fmt || item.fecha_limite || null;

    return (
      <TouchableOpacity
        style={styles.rowCard}
        onPress={() => navigation.navigate("DetalleTarea", { task: item })}
      >
        <View style={styles.rowHeader}>
          <Text style={styles.rowTitle} numberOfLines={1}>
            {item.titulo}
          </Text>
          <View
            style={[
              styles.badge,
              { backgroundColor: color, borderColor: color },
            ]}
          >
            <Text style={styles.badgeText}>{item.estado}</Text>
          </View>
        </View>

        <Text style={styles.rowDesc} numberOfLines={2}>
          {item.descripcion || "Sin descripción."}
        </Text>

        <View style={styles.rowMeta}>
          {fecha ? (
            <Text style={styles.metaText}>Vence: {fecha}</Text>
          ) : null}
          {item.created_at_fmt || item.created_at ? (
            <Text style={styles.metaText}>
              Creada: {item.created_at_fmt || item.created_at}
            </Text>
          ) : null}
        </View>
      </TouchableOpacity>
    );
  };

  // === Vista de carga / vacío ===
  if (loading) {
    return (
      <SafeAreaView style={styles.fullCenter}>
        <ActivityIndicator size="large" />
        <Text style={{ marginTop: 8 }}>Cargando tus tareas…</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      {/* Header tipo Trackify: título + filtros arriba */}
      <View style={styles.headerCard}>
        <Text style={styles.headerTitle}>Tareas</Text>
        <Text style={styles.headerSubtitle}>
          Revisa y actualiza las tareas asignadas.
        </Text>

        {/* Buscador */}
        <View style={styles.searchWrapper}>
          <TextInput
            style={styles.searchInput}
            placeholder="Buscar por título, descripción..."
            placeholderTextColor="#9ca3af"
            value={search}
            onChangeText={setSearch}
          />
        </View>

        {/* Filtros por estado */}
        <View style={styles.filterRow}>
          {ESTADOS.map((e) => {
            const selected = estadoFilter === e;
            const color =
              e === "Todos" ? "#6b7280" : ESTADO_COLORS[e] || "#64748b";
            return (
              <TouchableOpacity
                key={e}
                onPress={() => setEstadoFilter(e)}
                style={[
                  styles.filterChip,
                  selected && {
                    backgroundColor: color,
                    borderColor: color,
                  },
                ]}
              >
                <Text
                  style={[
                    styles.filterChipText,
                    selected && { color: "#ffffff" },
                  ]}
                >
                  {e}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </View>

      {/* Lista de tareas */}
      <FlatList
        data={filteredTasks}
        keyExtractor={(item) => String(item.id)}
        renderItem={renderItem}
        contentContainerStyle={
          filteredTasks.length === 0 ? styles.emptyList : styles.listContent
        }
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListEmptyComponent={
          <View style={styles.emptyBox}>
            <Text style={styles.emptyTitle}>Sin tareas para mostrar</Text>
            <Text style={styles.emptySubtitle}>
              No encontramos tareas con los filtros actuales.
            </Text>
          </View>
        }
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  // Fondo tipo dashboard Trackify
  container: {
    flex: 1,
    backgroundColor: "#f3f4f6",
  },
  fullCenter: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 16,
  },

  // Card de encabezado (buscador + filtros)
  headerCard: {
    marginHorizontal: 12,
    marginTop: 12,
    marginBottom: 4,
    padding: 12,
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
  headerTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#111827",
  },
  headerSubtitle: {
    marginTop: 2,
    fontSize: 13,
    color: "#6b7280",
  },
  searchWrapper: {
    marginTop: 10,
  },
  searchInput: {
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 8,
    fontSize: 14,
    backgroundColor: "#f9fafb",
  },
  filterRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    marginTop: 10,
    gap: 8,
  },
  filterChip: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "#d1d5db",
    backgroundColor: "#ffffff",
  },
  filterChipText: {
    fontSize: 13,
    color: "#111827",
  },

  // Lista
  listContent: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    paddingBottom: 16,
  },

  // Fila/card de tarea
  rowCard: {
    backgroundColor: "#ffffff",
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: "#e5e7eb",
    marginBottom: 8,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 1.5,
    elevation: 1,
  },
  rowHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 4,
  },
  rowTitle: {
    flex: 1,
    fontSize: 15,
    fontWeight: "600",
    color: "#111827",
    marginRight: 8,
  },
  rowDesc: {
    fontSize: 13,
    color: "#4b5563",
    marginBottom: 6,
  },
  rowMeta: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  metaText: {
    fontSize: 11,
    color: "#6b7280",
  },

  // Badge de estado
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    borderWidth: 1,
  },
  badgeText: {
    fontSize: 11,
    fontWeight: "600",
    color: "#ffffff",
  },

  // Lista vacía
  emptyList: {
    flexGrow: 1,
    paddingHorizontal: 16,
    paddingVertical: 24,
    justifyContent: "center",
  },
  emptyBox: {
    alignItems: "center",
    justifyContent: "center",
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "#111827",
  },
  emptySubtitle: {
    marginTop: 4,
    fontSize: 13,
    color: "#6b7280",
    textAlign: "center",
  },
});
