import sys
import os
import json
import socket
import asyncio
import threading
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import qrcode
import pyautogui
import websockets

# Disable PyAutoGUI delay for instant cursor tracking
pyautogui.PAUSE = 0

# 1. Automatically find your PC's local IP address
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

LOCAL_IP = get_local_ip()
WS_PORT = 8080
CONNECTION_STRING = f"ws://{LOCAL_IP}:{WS_PORT}"


class CompanionApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
        # Start the WebSocket server in a separate background thread
        threading.Thread(target=self.start_websocket_loop, daemon=True).start()

    def initUI(self):
        # Window configuration
        self.setWindowTitle('PC Remote Companion')
        self.setFixedSize(350, 450)
        self.setStyleSheet("background-color: #121212; color: white;")
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        # Title Label
        title_label = QLabel('PC Remote Companion')
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #00adb5; margin-bottom: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Instructions Label
        info_label = QLabel('Connect to the same network\nand scan this QR Code:')
        info_label.setStyleSheet("font-size: 14px; color: #bbbbbb; margin-bottom: 10px;")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)

        # QR Code Label
        self.qr_label = QLabel()
        self.generate_qr_image()
        self.qr_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.qr_label)

        # Connection String Status Label
        self.status_label = QLabel(f"Target: {CONNECTION_STRING}")
        self.status_label.setStyleSheet("font-size: 11px; color: #888888; margin-top: 15px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def generate_qr_image(self):
        # Generate the QR Code matrix using the python qrcode library
        qr = qrcode.QRCode(version=1, box_size=5, border=2)
        qr.add_data(CONNECTION_STRING)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img_path = "connection_qr.png"
        img.save(img_path)
        
        # Load image into PyQt Pixmap and update GUI
        pixmap = QPixmap(img_path)
        self.qr_label.setPixmap(pixmap)
        
        # Clean up the file afterward
        if os.path.exists(img_path):
            os.remove(img_path)

    # 2. WebSocket Engine Setup
    def start_websocket_loop(self):
        asyncio.run(self.main_server())

    async def main_server(self):
        async with websockets.serve(self.handle_mobile_client, "0.0.0.0", WS_PORT):
            await asyncio.Future()

    async def handle_mobile_client(self, websocket):
        self.update_status("📱 Mobile App Connected!")
        try:
            async for message in websocket:
                data = json.loads(message)
                
                # Handle Touchpad movement
                if data.get("type") == "move":
                    pyautogui.moveRel(data["dx"], data["dy"])
                    
        except websockets.exceptions.ConnectionClosed:
            self.update_status("❌ Disconnected. Waiting...")

    def update_status(self, text):
        # Safely update text from background thread
        self.status_label.setText(text)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = CompanionApp()
    ex.show()
    sys.exit(app.exec_())