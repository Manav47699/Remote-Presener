// App.tsx
import React, { useState } from 'react';
import { SafeAreaView, StyleSheet, StatusBar } from 'react-native';
import HomeScreen from './screens/HomeScreen';
import ScanScreen from './screens/ScanScreen';
import Presentation from './screens/Presentation';

type ActiveView = 'DASHBOARD' | 'SCANNER' | 'REMOTE';

export default function App() {
  const [currentView, setCurrentView] = useState<ActiveView>('DASHBOARD');

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#1e1e2e" />

      {currentView === 'DASHBOARD' && (
        <HomeScreen 
          onNavigateToScan={() => setCurrentView('SCANNER')} 
          onConnected={() => setCurrentView('REMOTE')} 
        />
      )}

      {currentView === 'SCANNER' && (
        <ScanScreen 
          onConnected={() => setCurrentView('REMOTE')} 
          onCancel={() => setCurrentView('DASHBOARD')} 
        />
      )}

      {currentView === 'REMOTE' && (
        <Presentation onDisconnected={() => setCurrentView('DASHBOARD')} />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#1e1e2e' },
});