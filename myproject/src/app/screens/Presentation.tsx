// src/screens/Presentation.tsx
import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, Text, View, TouchableOpacity } from 'react-native';
import { socketManager } from '../../services/websocket';

interface PresentationProps {
  onDisconnected: () => void;
}

export default function Presentation({ onDisconnected }: PresentationProps) {
  const [isLocked, setIsLocked] = useState(false);
  const lastTap = useRef<number | null>(null);

  useEffect(() => {
    if (typeof document !== 'undefined') {
      const previousTitle = document.title;
      document.title = 'Presenter Remote Active';

      return () => {
        document.title = previousTitle;
      };
    }
  }, []);

  const handleDoubleTapCloseOrOpen = () => {
    const now = Date.now();
    const DOUBLE_TAP_DELAY = 300;
    
    if (lastTap.current && (now - lastTap.current) < DOUBLE_TAP_DELAY) {
      setIsLocked(!isLocked);
    }
    lastTap.current = now;
  };

  const handleDisconnect = () => {
    socketManager.disconnect();
    onDisconnected();
  };

  return (
    <TouchableOpacity 
      style={styles.container} 
      activeOpacity={1} 
      onPress={handleDoubleTapCloseOrOpen}
    >
      {isLocked ? (
        <View style={styles.lockedStateContainer}>
          <Text style={styles.lockIcon}>🔒</Text>
          <Text style={styles.lockTitle}>Screen Shield Active</Text>
          <Text style={styles.lockSubtitle}>Double-tap quickly anywhere to resume visibility</Text>
          <Text style={styles.volumeHint}>Physical volume keys remain completely active</Text>
        </View>
      ) : (
        <View style={styles.activeStateContainer}>
          <Text style={styles.title}>Controller Connected</Text>
          <Text style={styles.subtitle}>Double-tap quickly to lock screen interface visibility</Text>

          <View style={styles.cardInfo}>
            <Text style={styles.infoTitle}>Pocket Control Active</Text>
            <Text style={styles.infoBody}>• Press Volume Up button ➔ Previous Slide</Text>
            <Text style={styles.infoBody}>• Press Volume Down button ➔ Next Slide</Text>
          </View>

          <TouchableOpacity style={styles.exitBtn} onPress={handleDisconnect}>
            <Text style={styles.exitText}>Disconnect Presenter</Text>
          </TouchableOpacity>
        </View>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#11111b', padding: 24, justifyContent: 'center' },
  lockedStateContainer: { alignItems: 'center', justifyContent: 'center' },
  lockIcon: { fontSize: 64, marginBottom: 16 },
  lockTitle: { fontSize: 22, fontWeight: 'bold', color: '#ff5555' },
  lockSubtitle: { fontSize: 14, color: '#7a7a9a', marginTop: 6, textAlign: 'center' },
  volumeHint: { fontSize: 12, color: '#6bff8f', marginTop: 24, fontWeight: '600' },
  activeStateContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 26, fontWeight: 'bold', color: '#ffffff', marginBottom: 6 },
  subtitle: { fontSize: 13, color: '#a0a0b0', textAlign: 'center', marginBottom: 40 },
  cardInfo: { backgroundColor: '#1e1e2e', padding: 20, borderRadius: 14, width: '100%', borderWidth: 1, borderColor: '#313244', marginBottom: 40 },
  infoTitle: { color: '#6bff8f', fontSize: 15, fontWeight: 'bold', marginBottom: 10 },
  infoBody: { color: '#e0e0e0', fontSize: 14, marginVertical: 4, fontWeight: '500' },
  exitBtn: { backgroundColor: '#313244', paddingVertical: 14, paddingHorizontal: 32, borderRadius: 10 },
  exitText: { color: '#f38ba8', fontWeight: 'bold', fontSize: 15 },
});