import React, { useState } from 'react';
import { View, Text, ActivityIndicator, StyleSheet, Alert, TextInput, Button } from 'react-native';
import { api } from '../api';

const ESTADOS = ['Pendiente', 'En progreso', 'Atrasada', 'Finalizada'];

export default function TaskDetailScreen({ route }) {
  const { task } = route.params || {};
  const [estado, setEstado] = useState(task?.estado || 'Pendiente');
  const [comentario, setComentario] = useState('');
  const [saving, setSaving] = useState(false);

  if (!task) {
    return (
      <View style={styles.center}>
        <Text>No se encontró la tarea.</Text>
      </View>
    );
  }

  const handleUpdateState = async () => {
    if (!estado) return Alert.alert('Falta estado', 'Selecciona un estado');
    try {
      setSaving(true);
      await api.patch(`/api/tareas/${task.id}/estado/`, {
        estado,
        comentario: comentario?.trim() || null,
      });
      Alert.alert('OK', 'Estado actualizado');
      setComentario('');
    } catch (e) {
      console.log('Error actualizando estado:', e?.response?.data || e.message);
      Alert.alert('Error', 'No se pudo actualizar el estado');
    } finally {
      setSaving(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{task.titulo}</Text>
      <Text style={styles.label}>Descripción:</Text>
      <Text style={styles.paragraph}>{task.descripcion || '—'}</Text>

      <View style={{ height: 10 }} />

      <Text style={styles.label}>Estado actual:</Text>
      <View style={styles.estadoBox}>
        {ESTADOS.map((e) => (
          <Text
            key={e}
            onPress={() => setEstado(e)}
            style={[
              styles.estadoPill,
              estado === e && { backgroundColor: '#0ea5e9', color: '#fff', borderColor: '#0ea5e9' },
            ]}
          >
            {e}
          </Text>
        ))}
      </View>

      <Text style={styles.label}>Comentario (opcional):</Text>
      <TextInput
        style={styles.input}
        placeholder="Añade un comentario…"
        value={comentario}
        onChangeText={setComentario}
        multiline
      />

      <Button title={saving ? 'Guardando…' : 'Actualizar estado'} onPress={handleUpdateState} disabled={saving} />

      <View style={{ height: 14 }} />
      {task.fecha_limite ? <Text style={styles.meta}>Fecha límite: {task.fecha_limite}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, gap: 10 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 8 },
  title: { fontSize: 18, fontWeight: '700' },
  label: { fontWeight: '600', marginTop: 6 },
  paragraph: { color: '#444', lineHeight: 20 },
  estadoBox: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginVertical: 8 },
  estadoPill: {
    paddingHorizontal: 10, paddingVertical: 6,
    borderRadius: 20, borderWidth: 1, borderColor: '#ddd', color: '#111',
  },
  input: { borderWidth: 1, borderColor: '#ddd', borderRadius: 8, padding: 10, minHeight: 60, textAlignVertical: 'top' },
  meta: { color: '#555' },
});
