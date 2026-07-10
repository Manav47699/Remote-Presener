#!/usr/bin/env python3
"""
Presenter Remote - Desktop Companion Backend
===========================================
A standalone PyQt5 desktop window that embeds a WebSocket server and 
emulates hardware key presses ('up' / 'down') for remote presentations.
"""

import sys
import os
import json
import socket
import asyncio
import threading
from io import BytesIO

# --- CRITICAL X11 FIX FOR NATIVE EXECUTABLES/VENVS ---
# This must run before importing pyautogui or initializing QApplication
# to prevent the 'DisplayConnectionError' from blocking execution on Linux.
if sys.platform.startswith('linux'):
    os.system("xhost +local: > /dev/null 2>&1")

import pyautogui
import qrcode
from PIL import Image
from PyQt5.QtCore import Qt, QObject, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QIcon
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame
import websockets

# --------------------------------------------------------------------------
# Configuration & Constants
# --------------------------------------------------------------------------
WEBSOCKET_HOST = "0.0.0.0"
WEBSOCKET_PORT = 8080
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

# Scaled up Window Parameters
WINDOW_WIDTH = 500
WINDOW_HEIGHT = 580

DARK_STYLESHEET = """
QWidget { background-color: #1e1e2e; color: #e0e0e0; font-family: 'Segoe UI', Arial, sans-serif; }
QLabel#titleLabel { font-size: 24px; font-weight: bold; color: #ffffff; }
QLabel#infoLabel { font-size: 14px; color: #a0a0b0; }
QFrame#qrFrame { background-color: #ffffff; border-radius: 12px; padding: 12px; }
QLabel#statusLabel { font-size: 16px; font-weight: bold; padding: 10px; border-radius: 8px; }
"""

# --------------------------------------------------------------------------
# Helpers & Network Detection
# --------------------------------------------------------------------------
def get_local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
    except OSError:
        ip = "127.0.0.1"
    finally:
        sock.close()
    return ip

def generate_qr_pixmap(data: str) -> QPixmap:
    # Increased box_size to 12 for crisp, high-resolution rendering on large window layout
    qr = qrcode.QRCode(version=1, box_size=12, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    pil_image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    
    buffer = BytesIO()
    pil_image.save(buffer, format="PNG")
    qimage = QImage()
    qimage.loadFromData(buffer.getvalue(), "PNG")
    return QPixmap.fromImage(qimage)

class ConnectionBridge(QObject):
    client_connected = pyqtSignal(str)
    client_disconnected = pyqtSignal()

# --------------------------------------------------------------------------
# Server & Request Processing
# --------------------------------------------------------------------------
class PresentationServer:
    def __init__(self, bridge: ConnectionBridge):
        self.bridge = bridge
        self._current_client = None

    def start(self) -> None:
        threading.Thread(target=lambda: asyncio.run(self._serve()), daemon=True).start()

    async def _serve(self) -> None:
        async with websockets.serve(self._handle_client, WEBSOCKET_HOST, WEBSOCKET_PORT):
            await asyncio.Future()

    async def _handle_client(self, websocket) -> None:
        if self._current_client and self._current_client.open:
            await self._current_client.close()

        self._current_client = websocket
        addr = websocket.remote_address[0] if websocket.remote_address else "unknown"
        self.bridge.client_connected.emit(addr)

        try:
            async for raw_message in websocket:
                payload = json.loads(raw_message)
                if payload.get("type") == "press" and payload.get("key") in ["up", "down"]:
                    pyautogui.press(payload["key"])
        except websockets.ConnectionClosed:
            pass
        finally:
            if self._current_client is websocket:
                self._current_client = None
                self.bridge.client_disconnected.emit()

# --------------------------------------------------------------------------
# UI Window
# --------------------------------------------------------------------------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.bridge = ConnectionBridge()
        self.bridge.client_connected.connect(lambda addr: self._update_status(f"● Connected ({addr})", "background-color: #1e3a24; color: #6bff8f;"))
        self.bridge.client_disconnected.connect(lambda: self._update_status("● Disconnected", "background-color: #3a1e1e; color: #ff6b6b;"))

        local_ip = get_local_ip()
        ws_url = f"ws://{local_ip}:{WEBSOCKET_PORT}"

        # Custom App Branding Configuration
        self.setWindowTitle("Presenter Remote")
        
        # Resolves runtime temp path injection when bundled inside binary extraction environments via PyInstaller
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        logo_path = os.path.join(base_path, "logo.png")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setStyleSheet(DARK_STYLESHEET)

        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("Presenter Remote Backend")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # QR Frame Setup
        qr_frame = QFrame()
        qr_frame.setObjectName("qrFrame")
        qr_layout = QVBoxLayout()
        qr_layout.setContentsMargins(0, 0, 0, 0)
        qr_label = QLabel()
        qr_label.setAlignment(Qt.AlignCenter)
        qr_label.setPixmap(generate_qr_pixmap(ws_url).scaled(320, 320, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        qr_layout.addWidget(qr_label)
        qr_frame.setLayout(qr_layout)

        qr_wrapper = QHBoxLayout()
        qr_wrapper.addStretch()
        qr_wrapper.addWidget(qr_frame)
        qr_wrapper.addStretch()
        layout.addLayout(qr_wrapper)

        target_lbl = QLabel(f"Target Link: {ws_url}")
        target_lbl.setObjectName("infoLabel")
        target_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(target_lbl)

        self.status_label = QLabel("● Disconnected")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("background-color: #3a1e1e; color: #ff6b6b;")
        layout.addWidget(self.status_label)

        layout.addStretch()
        self.setLayout(layout)
        
        self.server = PresentationServer(self.bridge)
        self.server.start()

    def _update_status(self, text, style):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(style)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Bundle matching application runtime icon asset for system docks
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    logo_path = os.path.join(base_path, "logo.png")
    if os.path.exists(logo_path):
        app.setWindowIcon(QIcon(logo_path))

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())