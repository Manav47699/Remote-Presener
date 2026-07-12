// src/app/screens/Presentation.tsx
import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, Text, View, TouchableOpacity } from 'react-native';
import * as Haptics from 'expo-haptics';
import { socketManager } from '../../services/websocket';

// Safely require the native module to prevent Expo Go from crashing during compilation
let VolumeManager: any = null;
try {
  VolumeManager = require('expo-volume-manager').VolumeManager;
} catch (e) {
  console.log('[Presentation] VolumeManager is unavailable in Expo Go.');
}

interface PresentationProps {
  onDisconnected: () => void;
}

export default function Presentation({ onDisconnected }: PresentationProps) {
  const [isLocked, setIsLocked] = useState(false);
  const [nativeVolumeSupported, setNativeVolumeSupported] = useState(false);
  const lastTap = useRef<number | null>(null);

  useEffect(() => {
    if (!VolumeManager) return;

    try {
      setNativeVolumeSupported(true);
      // Suppress the Android native volume slider popup overlay
      VolumeManager.showNativeVolumeUI({ enabled: false });

      // Listen to volume button shifts relative to a baseline median index
      const subscription = VolumeManager.addVolumeListener((result: any) => {
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
        
        if (result.volume > 0.5) {
          socketManager.sendKeyPress('up');
        } else {
          socketManager.sendKeyPress('down');
        }
        
        // Snap audio state registry center-point back immediately to capture continuous presses
        VolumeManager.setVolume(0.5);
      });

      // Calibrate audio baseline index immediately on screen mount
      VolumeManager.setVolume(0.5);

      return () => {
        subscription.remove();
        VolumeManager.showNativeVolumeUI({ enabled: true });
      };
    } catch (err) {
      setNativeVolumeSupported(false);
    }
  }, []);

  const handlePress = (direction: 'up' | 'down') => {
    if (isLocked) return;
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    socketManager.sendKeyPress(direction);
  };

  const handleDoubleTapCloseOrOpen = () => {
    const now = Date.now();
    const DOUBLE_TAP_DELAY = 300;
    
    if (lastTap.current && (now - lastTap.current) < DOUBLE_TAP_DELAY) {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      setIsLocked(!isLocked);
    }
    lastTap.current = now;
  };

  const handleDisconnect = () => {
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
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
          {nativeVolumeSupported && (
            <Text style={styles.volumeHint}>Physical volume keys remain active</Text>
          )}
        </View>
      ) : (
        <View style={styles.activeStateContainer}>
          <View style={styles.topInfo}>
            <Text style={styles.title}>Controller Connected</Text>
            <Text style={styles.subtitle}>Double-tap quickly to lock screen interface visibility</Text>
          </View>

          {/* Interactive touch targets fallback so you can use the screen directly too */}
          <View style={styles.fallbackDeck}>
            <TouchableOpacity style={[styles.pad, styles.prevPad]} onPress={() => handlePress('up')}>
              <Text style={styles.padArrow}>▲</Text>
              <Text style={styles.padLabel}>PREVIOUS SLIDE</Text>
            </TouchableOpacity>
            
            <TouchableOpacity style={[styles.pad, styles.nextPad]} onPress={() => handlePress('down')}>
              <Text style={styles.padArrow}>▼</Text>
              <Text style={styles.padLabel}>NEXT SLIDE</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.bottomGroup}>
            <View style={styles.cardInfo}>
              <Text style={styles.infoTitle}>Pocket Control Status:</Text>
              <Text style={styles.infoBody}>
                {nativeVolumeSupported 
                  ? "✓ Volume buttons mapped and fully active." 
                  : "⚠ Using on-screen pads (Build native APK for volume button support)."}
              </Text>
            </View>

            <TouchableOpacity style={styles.exitBtn} onPress={handleDisconnect}>
              <Text style={styles.exitText}>Disconnect Presenter</Text>
            </TouchableOpacity>
          </View>
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
  activeStateContainer: { flex: 1, justifyContent: 'space-between', alignItems: 'center' },
  topInfo: { alignItems: 'center', marginTop: 10 },
  title: { fontSize: 26, fontWeight: 'bold', color: '#ffffff', marginBottom: 6 },
  subtitle: { fontSize: 13, color: '#a0a0b0', textAlign: 'center' },
  fallbackDeck: { width: '100%', flex: 1, marginVertical: 24, gap: 12 },
  pad: { flex: 1, borderRadius: 14, justifyContent: 'center', alignItems: 'center' },
  prevPad: { backgroundColor: '#1e1e2e', borderWidth: 1, borderColor: '#313244' },
  nextPad: { backgroundColor: '#8839ef' },
  padArrow: { fontSize: 36, color: '#ffffff' },
  padLabel: { fontSize: 12, fontWeight: 'bold', color: '#ffffff', marginTop: 6, letterSpacing: 1 },
  bottomGroup: { width: '100%', alignItems: 'center' },
  cardInfo: { backgroundColor: '#1e1e2e', padding: 16, borderRadius: 14, width: '100%', borderWidth: 1, borderColor: '#313244', marginBottom: 20 },
  infoTitle: { color: '#6bff8f', fontSize: 14, fontWeight: 'bold', marginBottom: 4 },
  infoBody: { color: '#e0e0e0', fontSize: 13, fontWeight: '500' },
  exitBtn: { backgroundColor: '#313244', paddingVertical: 14, paddingHorizontal: 32, borderRadius: 10, width: '100%', alignItems: 'center' },
  exitText: { color: '#f38ba8', fontWeight: 'bold', fontSize: 15 },
});