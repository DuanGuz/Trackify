// App.js
import React from 'react';
import { AuthProvider } from './src/auth';
import AppNavigator from './src/AppNavigator'; // ajusta ruta si está en src/

export default function App() {
  return (
    <AuthProvider>
      <AppNavigator />
    </AuthProvider>
  );
}
