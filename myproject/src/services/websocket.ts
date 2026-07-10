type ConnectionStatus = 'CONNECTED' | 'DISCONNECTED' | 'ERROR';

type StatusCallback = (status: ConnectionStatus) => void;

class SocketManager {
  private socket: WebSocket | null = null;
  private statusCallback: StatusCallback | null = null;

  connect(url: string, callback: StatusCallback) {
    this.disconnect();
    this.statusCallback = callback;

    const normalizedUrl = url.startsWith('ws://') || url.startsWith('wss://') ? url : `ws://${url}`;

    try {
      this.socket = new WebSocket(normalizedUrl);
      this.socket.onopen = () => {
        callback('CONNECTED');
      };
      this.socket.onerror = () => {
        callback('ERROR');
      };
      this.socket.onclose = () => {
        callback('DISCONNECTED');
      };
    } catch (error) {
      console.error('Failed to open websocket connection', error);
      callback('ERROR');
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.statusCallback = null;
  }

  sendKeyPress(key: string) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      return;
    }

    this.socket.send(JSON.stringify({ type: 'keypress', key }));
  }
}

export const socketManager = new SocketManager();
