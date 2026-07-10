// src/screens/ScanScreen.tsx
import React, { useState } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, Alert, TextInput } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { socketManager } from '../../services/websocket';

interface ScanScreenProps {
  onConnected: () => void;
  onCancel: () => void;
}

export default function ScanScreen({ onConnected, onCancel }: ScanScreenProps) {
  const [inputUrl, setInputUrl] = useState('ws://localhost:8765');

  const connectToTarget = async (target: string) => {
    const normalizedTarget = target.trim();
    if (!normalizedTarget.startsWith('ws://') && !normalizedTarget.startsWith('wss://')) {
      Alert.alert('Invalid URL', 'Please enter a websocket URL such as ws://localhost:8765');
      return;
    }

    socketManager.connect(normalizedTarget, async (status: 'CONNECTED' | 'DISCONNECTED' | 'ERROR') => {
      if (status === 'CONNECTED') {
        try {
          const stored = await AsyncStorage.getItem('@presenter_history');
          let historyList = stored ? JSON.parse(stored) : [];
          if (!historyList.includes(normalizedTarget)) {
            historyList.unshift(normalizedTarget);
            await AsyncStorage.setItem('@presenter_history', JSON.stringify(historyList.slice(0, 5)));
          }
        } catch (e) {
          console.log('Error saving connection target');
        }
        onConnected();
      } else {
        Alert.alert('Connection Stalled', 'Could not sync over local sockets.');
      }
    });
  };

  return (
    <View style={styles.container}>
      <View style={styles.overlay}>
        <Text style={styles.title}>Connect to Presenter</Text>
        <Text style={styles.hintText}>Enter the presenter websocket URL manually if QR scanning is unavailable.</Text>

        <TextInput
          style={styles.input}
          value={inputUrl}
          onChangeText={setInputUrl}
          placeholder="ws://localhost:8765"
          placeholderTextColor="#7a7a9a"
          autoCapitalize="none"
          autoCorrect={false}
        />

        <TouchableOpacity style={styles.connectBtn} onPress={() => connectToTarget(inputUrl)}>
          <Text style={styles.connectText}>Connect</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.cancelBtn} onPress={onCancel}>
          <Text style={styles.cancelText}>Back Dashboard</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#11111b', padding: 24, justifyContent: 'center' },
  overlay: { backgroundColor: '#1e1e2e', borderRadius: 16, padding: 24, alignItems: 'center' },
  title: { color: '#ffffff', fontSize: 22, fontWeight: 'bold', marginBottom: 8 },
  hintText: { color: '#a0a0b0', fontSize: 14, textAlign: 'center', marginBottom: 20 },
  input: { width: '100%', backgroundColor: '#252538', color: '#ffffff', borderRadius: 10, paddingHorizontal: 14, paddingVertical: 12, marginBottom: 14, borderWidth: 1, borderColor: '#313244' },
  connectBtn: { width: '100%', backgroundColor: '#8839ef', paddingVertical: 12, borderRadius: 10, alignItems: 'center', marginBottom: 12 },
  connectText: { color: '#ffffff', fontWeight: 'bold' },
  cancelBtn: { width: '100%', backgroundColor: '#ff5555', paddingHorizontal: 24, paddingVertical: 12, borderRadius: 8, alignItems: 'center' },
  cancelText: { color: '#ffffff', fontWeight: 'bold' },
});