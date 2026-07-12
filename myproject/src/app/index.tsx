import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, TextInput, Alert, StatusBar } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export default function App() {
  const [url, setUrl] = useState('ws://192.168.16.106:8080');
  const [status, setStatus] = useState<'DISCONNECTED' | 'CONNECTING' | 'CONNECTED'>('DISCONNECTED');
  const [ws, setWs] = useState<WebSocket | null>(null);

  const connect = () => {
    if (!url.startsWith('ws://') && !url.startsWith('wss://')) {
      Alert.alert('Invalid URL', 'URL must start with ws:// or wss://');
      return;
    }

    setStatus('CONNECTING');
    const socket = new WebSocket(url.trim());

    socket.onopen = () => {
      setStatus('CONNECTED');
      setWs(socket);
    };

    socket.onclose = () => {
      setStatus('DISCONNECTED');
      setWs(null);
    };

    socket.onerror = (e) => {
      console.log('WebSocket Error: ', e);
      setStatus('DISCONNECTED');
      setWs(null);
      Alert.alert('Connection Failed', 'Could not sync over local sockets.');
    };
  };

  const disconnect = () => {
    if (ws) {
      ws.close();
    }
  };

  const sendKey = (key: 'up' | 'down') => {
    if (ws && status === 'CONNECTED') {
      ws.send(JSON.stringify({ type: 'press', key: key }));
    } else {
      Alert.alert('Not Connected', 'Please connect to your PC first.');
    }
  };

  // Clean up socket on unmount
  useEffect(() => {
    return () => {
      if (ws) ws.close();
    };
  }, [ws]);

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#11111b" />
      
      <View style={styles.header}>
        <Text style={styles.logo}>Presenter Remote</Text>
        <View style={[styles.badge, status === 'CONNECTED' ? styles.badgeConnected : status === 'CONNECTING' ? styles.badgeConnecting : styles.badgeDisconnected]}>
          <Text style={styles.badgeText}>{status}</Text>
        </View>
      </View>

      {status !== 'CONNECTED' ? (
        <View style={styles.card}>
          <Text style={styles.title}>Connect to PC</Text>
          <Text style={styles.subtitle}>Enter the target link displayed in your PC terminal.</Text>
          
          <TextInput
            style={styles.input}
            value={url}
            onChangeText={setUrl}
            placeholder="ws://192.168.16.106:8080"
            placeholderTextColor="#7a7a9a"
            autoCapitalize="none"
            autoCorrect={false}
          />

          <TouchableOpacity 
            style={styles.connectButton} 
            onPress={connect}
            disabled={status === 'CONNECTING'}
          >
            <Text style={styles.buttonText}>{status === 'CONNECTING' ? 'Connecting...' : 'Connect'}</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <View style={styles.remoteContainer}>
          <TouchableOpacity style={[styles.arrowButton, styles.upButton]} onPress={() => sendKey('up')}>
            <Text style={styles.arrowText}>◀ PREVIOUS (Left)</Text>
          </TouchableOpacity>

          <TouchableOpacity style={[styles.arrowButton, styles.downButton]} onPress={() => sendKey('down')}>
            <Text style={styles.arrowText}>NEXT (Right) ▶</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.disconnectButton} onPress={disconnect}>
            <Text style={styles.disconnectText}>Disconnect</Text>
          </TouchableOpacity>
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#11111b', padding: 20 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 30, paddingTop: 10 },
  logo: { color: '#ffffff', fontSize: 20, fontWeight: 'bold' },
  badge: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20 },
  badgeDisconnected: { backgroundColor: '#3a1e1e' },
  badgeConnecting: { backgroundColor: '#fe8019' },
  badgeConnected: { backgroundColor: '#1e3a24' },
  badgeText: { color: '#ffffff', fontSize: 12, fontWeight: 'bold' },
  card: { backgroundColor: '#1e1e2e', padding: 24, borderRadius: 16, borderHeight: 1, borderColor: '#313244', marginTop: '20%' },
  title: { color: '#ffffff', fontSize: 22, fontWeight: 'bold', marginBottom: 8, textAlign: 'center' },
  subtitle: { color: '#a0a0b0', fontSize: 14, marginBottom: 24, textAlign: 'center' },
  input: { backgroundColor: '#252538', color: '#ffffff', borderRadius: 10, paddingHorizontal: 16, paddingVertical: 14, fontSize: 16, marginBottom: 20, borderWidth: 1, borderColor: '#313244' },
  connectButton: { backgroundColor: '#8839ef', paddingVertical: 14, borderRadius: 10, alignItems: 'center' },
  buttonText: { color: '#ffffff', fontWeight: 'bold', fontSize: 16 },
  remoteContainer: { flex: 1, justifyContent: 'center', gap: 25 },
  arrowButton: { flex: 0.35, borderRadius: 20, justifyContent: 'center', alignItems: 'center', elevation: 3 },
  upButton: { backgroundColor: '#313244', borderWidth: 2, borderColor: '#cba6f7' },
  downButton: { backgroundColor: '#8839ef' },
  arrowText: { color: '#ffffff', fontSize: 24, fontWeight: 'bold' },
  disconnectButton: { backgroundColor: '#3a1e1e', paddingVertical: 14, borderRadius: 10, alignItems: 'center', marginTop: 10 },
  disconnectText: { color: '#ff6b6b', fontWeight: 'bold', fontSize: 16 }
});