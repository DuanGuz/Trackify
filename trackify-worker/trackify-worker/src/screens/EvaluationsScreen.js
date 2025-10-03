import React, { useCallback, useState } from 'react';
import { View, Text, FlatList, RefreshControl, ActivityIndicator, StyleSheet } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { api } from '../api';

export default function EvaluationsScreen() {
  const [items, setItems] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchEvaluaciones = async () => {
    try {
      const { data } = await api.get('/api/evaluaciones/mias/');
      setItems(data || []);
    } catch (e) {
      console.log('Error evaluaciones:', e?.response?.data || e.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      fetchEvaluaciones();
    }, [])
  );

  const onRefresh = () => {
    setRefreshing(true);
    fetchEvaluaciones();
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator />
        <Text>Cargando evaluaciones…</Text>
      </View>
    );
  }

  return (
    <FlatList
      data={items}
      keyExtractor={(it, idx) => String(it.id ?? idx)}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      contentContainerStyle={{ padding: 12 }}
      renderItem={({ item }) => (
        <View style={styles.card}>
          <Text style={styles.score}>Puntaje: {item.puntaje}</Text>
          <Text style={styles.meta}>Supervisor: {item.supervisor_nombre || '—'}</Text>
          <Text style={styles.meta}>Fecha: {item.created_at || '—'}</Text>
          {item.comentarios ? <Text style={styles.comment}>{item.comentarios}</Text> : null}
        </View>
      )}
      ListEmptyComponent={
        <View style={styles.center}>
          <Text>No tienes evaluaciones aún.</Text>
        </View>
      }
    />
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 8 },
  card: { padding: 12, backgroundColor: '#fff', borderRadius: 10, borderWidth: 1, borderColor: '#eee', marginBottom: 12, gap: 6 },
  score: { fontWeight: '800' },
  meta: { color: '#555' },
  comment: { color: '#333' },
});
