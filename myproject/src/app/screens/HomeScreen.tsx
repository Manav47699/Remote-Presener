// src/screens/HomeScreen.tsx
import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, FlatList } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { socketManager } from '../../services/websocket';

interface HomeScreenProps {
  onNavigateToScan: () => void;
  onConnected: () => void;
}

export default function HomeScreen({ onNavigateToScan, onConnected }: HomeScreenProps) {
  const [history, setHistory] = useState<string[]>([]);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const stored = await AsyncStorage.getItem('@presenter_history');
      if (stored) setHistory(JSON.parse(stored));
    } catch (e) {
      console.log('Failed to load history');
    }
  };

  const connectToRecent = (url: string) => {
    socketManager.connect(url, (status: 'CONNECTED' | 'DISCONNECTED' | 'ERROR') => {
      if (status === 'CONNECTED') {
        onConnected();
      }
    });
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.logoText}>Presenter Remote</Text>
        <Text style={styles.tagline}>Wireless Presentation Deck</Text>
      </View>

      <TouchableOpacity style={styles.scanButton} onPress={onNavigateToScan}>
        <Text style={styles.scanButtonText}>Scan for Devices</Text>
      </TouchableOpacity>

      <Text style={styles.sectionTitle}>Recent Connections</Text>
      
      {history.length === 0 ? (
        <Text style={styles.emptyText}>No recent devices found.</Text>
      ) : (
        <FlatList
          data={history}
          keyExtractor={(item) => item}
          renderItem={({ item }) => (
            <TouchableOpacity style={styles.historyCard} onPress={() => connectToRecent(item)}>
              <Text style={styles.historyText}>{item.replace('ws://', '')}</Text>
              <Text style={styles.connectLabel}>Tap to Reconnect →</Text>
            </TouchableOpacity>
          )}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#1e1e2e', padding: 24, justifyContent: 'center' },
  header: { alignItems: 'center', marginBottom: 40, marginTop: 40 },
  logoText: { fontSize: 32, fontWeight: 'bold', color: '#ffffff' },
  tagline: { fontSize: 14, color: '#a0a0b0', marginTop: 4 },
  scanButton: { backgroundColor: '#8839ef', paddingVertical: 16, borderRadius: 12, alignItems: 'center', marginBottom: 40 },
  scanButtonText: { color: '#ffffff', fontSize: 18, fontWeight: 'bold' },
  sectionTitle: { fontSize: 16, fontWeight: 'bold', color: '#e0e0e0', marginBottom: 12 },
  emptyText: { color: '#7a7a9a', textAlign: 'center', marginTop: 20 },
  historyCard: { backgroundColor: '#252538', padding: 16, borderRadius: 10, marginBottom: 10, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderWidth: 1, borderColor: '#303046' },
  historyText: { color: '#ffffff', fontSize: 15, fontWeight: '500' },
  connectLabel: { color: '#8839ef', fontSize: 13, fontWeight: '600' },
});