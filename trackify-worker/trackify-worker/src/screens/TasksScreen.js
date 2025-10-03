import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, FlatList, RefreshControl, TouchableOpacity, ActivityIndicator, StyleSheet } from 'react-native';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { api } from '../api';

export default function TasksScreen() {
  const [tasks, setTasks] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);
  const navigation = useNavigation();

  const fetchTasks = async () => {
    try {
      const { data } = await api.get('/api/tareas/mias/');
      setTasks(data || []);
    } catch (e) {
      console.log('Error cargando tareas:', e?.response?.data || e.message);
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

  const renderItem = ({ item }) => (
    <TouchableOpacity
      style={styles.item}
      onPress={() => navigation.navigate('DetalleTarea', { task: item })}
    >
      <View style={{ flex: 1 }}>
        <Text style={styles.title}>{item.titulo}</Text>
        <Text style={styles.desc} numberOfLines={2}>{item.descripcion || '—'}</Text>
        <View style={styles.row}>
          <Text style={styles.badge}>{item.estado}</Text>
          {item.fecha_limite ? <Text style={styles.deadline}>Vence: {item.fecha_limite}</Text> : null}
        </View>
      </View>
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator />
        <Text>Cargando tareas…</Text>
      </View>
    );
  }

  return (
    <FlatList
      data={tasks}
      keyExtractor={(it) => String(it.id)}
      renderItem={renderItem}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      ListEmptyComponent={
        <View style={styles.center}>
          <Text>No tienes tareas asignadas.</Text>
        </View>
      }
      contentContainerStyle={{ padding: 12 }}
    />
  );
}

const styles = StyleSheet.create({
  item: {
    padding: 12,
    backgroundColor: '#fff',
    borderRadius: 10,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#eee',
    gap: 6,
  },
  title: { fontWeight: '700', fontSize: 16 },
  desc: { color: '#555' },
  badge: {
    backgroundColor: '#f1f5f9',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 20,
    fontSize: 12,
    marginRight: 8,
  },
  deadline: { color: '#444', fontSize: 12 },
  row: { flexDirection: 'row', alignItems: 'center', marginTop: 4 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 8, padding: 16 },
});
