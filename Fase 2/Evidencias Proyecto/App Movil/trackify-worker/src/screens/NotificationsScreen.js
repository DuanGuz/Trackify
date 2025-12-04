// src/screens/NotificationsScreen.js
import React, { useCallback, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  Alert,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { api } from "../api";

function formatDate(dateString) {
  if (!dateString) return "";

  // 1) Intento directo con new Date (ideal si viene en ISO: 2025-11-19T21:30:00Z)
  let d = new Date(dateString);
  if (!isNaN(d.getTime())) {
    return d.toLocaleString(); // respeta la configuración local del dispositivo
  }

  // 2) Intento parsear formato tipo "dd/mm/yyyy HH:MM[:SS]"
  const m = dateString.match(
    /^(\d{2})\/(\d{2})\/(\d{4})[ T](\d{2}):(\d{2})(?::(\d{2}))?$/
  );
  if (m) {
    const [, dd, mm, yyyy, hh, min, ss] = m;
    d = new Date(
      Number(yyyy),
      Number(mm) - 1,
      Number(dd),
      Number(hh),
      Number(min),
      ss ? Number(ss) : 0
    );
    if (!isNaN(d.getTime())) {
      return d.toLocaleString();
    }
  }

  // 3) Fallback: devolvemos el string tal cual para no mostrar "Invalid Date"
  return dateString;
}

export default function NotificationsScreen() {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [tab, setTab] = useState("unread"); // "unread" | "all"
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const computeUnreadCount = (items) =>
    items.filter((n) => !n.is_read).length;

  const normalizeResponse = (data) => {
    // Soporta varios formatos:
    // 1) [{...}, {...}]
    // 2) { items: [...], unread_count: N }
    // 3) { results: [...], unread_count: N }
    let items = [];
    let unread = 0;

    if (Array.isArray(data)) {
      // Respuesta simple: lista de notificaciones
      items = data;
      unread = computeUnreadCount(items);
    } else if (data && typeof data === "object") {
      if (Array.isArray(data.items)) {
        items = data.items;
      } else if (Array.isArray(data.results)) {
        items = data.results;
      }

      if (typeof data.unread_count === "number") {
        unread = data.unread_count;
      } else {
        unread = computeUnreadCount(items);
      }
    }

    return { items, unread };
  };

  const loadNotifications = async (showAlertOnError = true) => {
    try {
      setLoading(true);
      const { data } = await api.get("/api/notificaciones/");
      const { items, unread } = normalizeResponse(data);

      setNotifications(items);
      setUnreadCount(unread);
    } catch (e) {
      console.log("Error cargando notificaciones:", e?.response?.data || e.message);
      if (showAlertOnError) {
        Alert.alert("Error", "No se pudieron cargar las notificaciones.");
      }
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    try {
      setRefreshing(true);
      await loadNotifications(false);
    } finally {
      setRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      loadNotifications(false);
    }, [])
  );

  const handleMarkAllRead = async () => {
    try {
      await api.post("/api/notificaciones/clear/");
      await loadNotifications(false);
    } catch (e) {
      console.log(
        "Error marcando como leídas:",
        e?.response?.data || e.message
      );
      Alert.alert("Error", "No se pudo marcar como leídas.");
    }
  };

  const handleDeleteAll = async () => {
    Alert.alert(
      "Eliminar todas",
      "¿Estás seguro de eliminar todas las notificaciones?",
      [
        { text: "Cancelar", style: "cancel" },
        {
          text: "Eliminar",
          style: "destructive",
          onPress: async () => {
            try {
              await api.post("/api/notificaciones/delete_all/");
              setNotifications([]);
              setUnreadCount(0);
            } catch (e) {
              console.log(
                "Error borrando todas:",
                e?.response?.data || e.message
              );
              Alert.alert(
                "Error",
                "No se pudieron eliminar las notificaciones."
              );
            }
          },
        },
      ]
    );
  };

  const filteredNotifications =
    tab === "unread"
      ? notifications.filter((n) => !n.is_read)
      : notifications;

  return (
    <View style={styles.container}>
      {/* Header tipo Trackify */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Notificaciones</Text>
        <Text style={styles.headerSubtitle}>
          No leídas: {unreadCount}
        </Text>
      </View>

      {/* Tabs: No leídas / Todas */}
      <View style={styles.tabsRow}>
        <TouchableOpacity
          style={[
            styles.tab,
            tab === "unread" && styles.tabActive,
          ]}
          onPress={() => setTab("unread")}
        >
          <Text
            style={[
              styles.tabText,
              tab === "unread" && styles.tabTextActive,
            ]}
          >
            No leídas
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[
            styles.tab,
            tab === "all" && styles.tabActive,
          ]}
          onPress={() => setTab("all")}
        >
          <Text
            style={[
              styles.tabText,
              tab === "all" && styles.tabTextActive,
            ]}
          >
            Todas
          </Text>
        </TouchableOpacity>
      </View>

      {/* Botones de acciones */}
      <View style={styles.actionsRow}>
        <TouchableOpacity
          style={styles.actionBtn}
          onPress={handleMarkAllRead}
        >
          <Text style={styles.actionBtnText}>
            Marcar todas como leídas
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.actionBtn, styles.actionBtnDanger]}
          onPress={handleDeleteAll}
        >
          <Text
            style={[
              styles.actionBtnText,
              styles.actionBtnTextDanger,
            ]}
          >
            Eliminar todas
          </Text>
        </TouchableOpacity>
      </View>

      {/* Lista / Loading */}
      {loading && notifications.length === 0 ? (
        <View style={styles.center}>
          <ActivityIndicator />
          <Text style={styles.loadingText}>
            Cargando notificaciones…
          </Text>
        </View>
      ) : (
        <FlatList
          data={filteredNotifications}
          keyExtractor={(item) => String(item.id)}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
            />
          }
          contentContainerStyle={
            filteredNotifications.length === 0
              ? styles.emptyContainer
              : styles.listContainer
          }
          ListEmptyComponent={
            <Text style={styles.emptyText}>
              {tab === "unread"
                ? "No tienes notificaciones sin leer."
                : "No tienes notificaciones."}
            </Text>
          }
          renderItem={({ item }) => {
            const fechaStr = formatDate(item.created_at);

            return (
              <View
                style={[
                  styles.card,
                  !item.is_read && styles.cardUnread,
                ]}
              >
                <View style={styles.cardHeader}>
                  {!item.is_read && (
                    <View style={styles.unreadDot} />
                  )}
                  <Text
                    style={styles.cardTitle}
                    numberOfLines={2}
                  >
                    Notificación
                  </Text>
                </View>
                <Text style={styles.cardMessage}>
                  {item.mensaje}
                </Text>
                {!!fechaStr && (
                  <Text style={styles.cardMeta}>
                    {fechaStr}
                  </Text>
                )}
              </View>
            );
          }}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f3f4f6",
    padding: 12,
  },
  header: {
    marginBottom: 8,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: "700",
    color: "#111827",
  },
  headerSubtitle: {
    fontSize: 13,
    color: "#6b7280",
    marginTop: 2,
  },
  tabsRow: {
    flexDirection: "row",
    backgroundColor: "#e5e7eb",
    padding: 4,
    borderRadius: 999,
    marginVertical: 8,
  },
  tab: {
    flex: 1,
    paddingVertical: 6,
    borderRadius: 999,
    alignItems: "center",
  },
  tabActive: {
    backgroundColor: "#0ea5e9",
  },
  tabText: {
    fontSize: 13,
    fontWeight: "500",
    color: "#374151",
  },
  tabTextActive: {
    color: "#ffffff",
  },
  actionsRow: {
    flexDirection: "row",
    gap: 8,
    marginBottom: 8,
  },
  actionBtn: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "#d1d5db",
    backgroundColor: "#ffffff",
    alignItems: "center",
  },
  actionBtnDanger: {
    borderColor: "#ef4444",
  },
  actionBtnText: {
    fontSize: 12,
    fontWeight: "500",
    color: "#111827",
  },
  actionBtnTextDanger: {
    color: "#b91c1c",
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  loadingText: {
    fontSize: 13,
    color: "#6b7280",
  },
  listContainer: {
    paddingVertical: 4,
    paddingBottom: 16,
  },
  emptyContainer: {
    flexGrow: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 16,
  },
  emptyText: {
    color: "#6b7280",
    fontSize: 14,
    textAlign: "center",
  },
  card: {
    backgroundColor: "#ffffff",
    borderRadius: 12,
    padding: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: "#e5e7eb",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  cardUnread: {
    borderColor: "#0ea5e9",
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 4,
    gap: 4,
  },
  unreadDot: {
    width: 8,
    height: 8,
    borderRadius: 999,
    backgroundColor: "#0ea5e9",
  },
  cardTitle: {
    fontSize: 14,
    fontWeight: "600",
    color: "#111827",
  },
  cardMessage: {
    fontSize: 13,
    color: "#374151",
    marginTop: 4,
  },
  cardMeta: {
    fontSize: 11,
    color: "#9ca3af",
    marginTop: 6,
  },
});
