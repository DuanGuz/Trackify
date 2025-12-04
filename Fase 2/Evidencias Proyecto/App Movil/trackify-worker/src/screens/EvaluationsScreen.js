// src/screens/EvaluationsScreen.js
import React, { useCallback, useState } from "react";
import {
  SafeAreaView,
  View,
  Text,
  StyleSheet,
  FlatList,
  RefreshControl,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { api } from "../api";

// Color según puntaje
function scoreColor(score) {
  if (score >= 4) return "#22c55e"; // verde
  if (score === 3) return "#facc15"; // amarillo
  return "#ef4444"; // rojo
}

export default function EvaluationsScreen() {
  const [items, setItems] = useState([]);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setRefreshing(true);
      const { data } = await api.get("/api/evaluaciones/mias/");
      setItems(Array.isArray(data) ? data : []);
    } catch (e) {
      console.log("Error evaluaciones:", e?.response?.data || e.message);
    } finally {
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      fetchData();
    }, [fetchData])
  );

  const promedio =
    items.length > 0
      ? (items.reduce((acc, it) => acc + (it.puntaje || 0), 0) / items.length).toFixed(1)
      : null;

  const renderItem = ({ item }) => {
    const color = scoreColor(item.puntaje || 0);

    return (
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <View style={{ flex: 1 }}>
            <Text style={styles.cardTitle}>
              {item.supervisor_nombre || "Evaluación de desempeño"}
            </Text>
            {item.created_at_fmt && (
              <Text style={styles.cardDate}>{item.created_at_fmt}</Text>
            )}
          </View>

          <View
            style={[
              styles.scoreBadge,
              { borderColor: color, backgroundColor: color + "22" },
            ]}
          >
            <Text style={[styles.scoreValue, { color }]}>{item.puntaje}</Text>
            <Text style={styles.scoreLabel}>/ 5</Text>
          </View>
        </View>

        {item.comentarios ? (
          <>
            <Text style={styles.label}>Comentario</Text>
            <Text style={styles.comment}>{item.comentarios}</Text>
          </>
        ) : (
          <Text style={styles.noComment}>Sin comentarios adicionales.</Text>
        )}
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Resumen tipo dashboard */}
      <View style={styles.headerCard}>
        <Text style={styles.headerTitle}>Evaluaciones de desempeño</Text>
        <Text style={styles.headerSubtitle}>
          Aquí puedes revisar tus evaluaciones históricas.
        </Text>

        <View style={styles.summaryRow}>
          <View style={styles.summaryBox}>
            <Text style={styles.summaryLabel}>Cantidad</Text>
            <Text style={styles.summaryValue}>{items.length}</Text>
          </View>
          <View style={styles.summaryBox}>
            <Text style={styles.summaryLabel}>Promedio</Text>
            <Text style={styles.summaryValue}>
              {promedio !== null ? promedio : "--"}
            </Text>
          </View>
        </View>
      </View>

      {/* Lista de cards */}
      <FlatList
        data={items}
        keyExtractor={(item, idx) => String(item.id || idx)}
        renderItem={renderItem}
        contentContainerStyle={
          items.length === 0
            ? styles.listEmptyContainer
            : { paddingHorizontal: 12, paddingBottom: 16 }
        }
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={fetchData} />
        }
        ListEmptyComponent={
          <Text style={styles.emptyText}>
            Aún no tienes evaluaciones registradas.
          </Text>
        }
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f3f4f6",
  },
  headerCard: {
    marginHorizontal: 12,
    marginTop: 12,
    marginBottom: 8,
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
  headerTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#111827",
  },
  headerSubtitle: {
    marginTop: 4,
    fontSize: 13,
    color: "#6b7280",
  },
  summaryRow: {
    flexDirection: "row",
    marginTop: 12,
    gap: 12,
  },
  summaryBox: {
    flex: 1,
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 10,
    backgroundColor: "#f9fafb",
    borderWidth: 1,
    borderColor: "#e5e7eb",
  },
  summaryLabel: {
    fontSize: 12,
    color: "#6b7280",
    marginBottom: 2,
  },
  summaryValue: {
    fontSize: 16,
    fontWeight: "600",
    color: "#111827",
  },

  card: {
    backgroundColor: "#ffffff",
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: "#e5e7eb",
    marginTop: 8,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 6,
  },
  cardTitle: {
    fontSize: 15,
    fontWeight: "600",
    color: "#111827",
  },
  cardDate: {
    fontSize: 12,
    color: "#9ca3af",
    marginTop: 2,
  },
  scoreBadge: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    borderWidth: 1,
    marginLeft: 8,
  },
  scoreValue: {
    fontSize: 16,
    fontWeight: "700",
  },
  scoreLabel: {
    fontSize: 12,
    color: "#4b5563",
    marginLeft: 2,
  },
  label: {
    marginTop: 8,
    fontSize: 13,
    fontWeight: "600",
    color: "#111827",
    marginBottom: 2,
  },
  comment: {
    fontSize: 13,
    color: "#4b5563",
  },
  noComment: {
    fontSize: 12,
    color: "#9ca3af",
    marginTop: 4,
  },
  listEmptyContainer: {
    flexGrow: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 24,
  },
  emptyText: {
    fontSize: 14,
    color: "#6b7280",
    textAlign: "center",
  },
});
