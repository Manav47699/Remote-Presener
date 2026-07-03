#!/usr/bin/env python3
"""
Remote PC Controller - Desktop Companion Backend
==================================================

A self-contained PyQt5 desktop application that:
  * Displays a QR code encoding a WebSocket URL (ws://<LOCAL_IP>:8080)
  * Runs an asyncio WebSocket server on a background thread
  * Accepts JSON control messages from a paired React Native mobile app
  * Translates those messages into real mouse/keyboard actions via PyAutoGUI

Only a single client may be connected at a time. If a new client connects,
the previous connection is dropped.

Run with:
    python app.py
"""

import sys
import json
import socket
import asyncio
import threading
import traceback
from io import BytesIO

import pyautogui
import qrcode
from PIL import Image
from PyQt5.QtCore import Qt, QObject, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QFont
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
)

import websockets
from websockets.server import WebSocketServerProtocol


# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

WEBSOCKET_HOST = "0.0.0.0"
WEBSOCKET_PORT = 8080
WINDOW_WIDTH = 350
WINDOW_HEIGHT = 450
QR_BOX_SIZE = 8
QR_BORDER = 2

# Special / named keys supported directly by pyautogui.press().
# These map 1:1 to pyautogui's internal KEYBOARD_KEYS names.
SPECIAL_KEYS = {
    "enter",
    "backspace",
    "delete",
    "esc",
    "tab",
    "home",
    "end",
    "pageup",
    "pagedown",
    "insert",
    "space",
    "left",
    "right",
    "up",
    "down",
}

# Message types handled by the protocol dispatcher.
MSG_MOVE = "move"
MSG_LEFT_CLICK = "left_click"
MSG_RIGHT_CLICK = "right_click"
MSG_DOUBLE_CLICK = "double_click"
MSG_MOUSE_DOWN = "mouse_down"
MSG_MOUSE_UP = "mouse_up"
MSG_SCROLL = "scroll"
MSG_KEY = "key"
MSG_TEXT = "text"
MSG_HOTKEY = "hotkey"


# --------------------------------------------------------------------------
# PyAutoGUI global configuration
# --------------------------------------------------------------------------

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False


# --------------------------------------------------------------------------
# Networking helpers
# --------------------------------------------------------------------------

def get_local_ip() -> str:
    """
    Detect the machine's local IPv4 address on the active network
    (e.g. the phone's hotspot or local Wi-Fi network).

    Uses a UDP "connect" trick which does not actually send any packets,
    but forces the OS to pick the correct outbound interface/IP.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        ip_address = sock.getsockname()[0]
    except OSError:
        ip_address = "127.0.0.1"
    finally:
        sock.close()
    return ip_address


def build_websocket_url(ip_address: str, port: int) -> str:
    """Build the ws:// URL that the mobile app will scan / connect to."""
    return f"ws://{ip_address}:{port}"


# --------------------------------------------------------------------------
# QR Code generation
# --------------------------------------------------------------------------

def generate_qr_pixmap(data: str) -> QPixmap:
    """
    Generate a QR code for the given data string and return it as a
    QPixmap ready to be displayed inside a QLabel. The QR image is
    generated fully in-memory (no file is written to disk).
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=QR_BOX_SIZE,
        border=QR_BORDER,
    )
    qr.add_data(data)
    qr.make(fit=True)

    pil_image: Image.Image = qr.make_image(fill_color="black", back_color="white")
    pil_image = pil_image.convert("RGB")

    buffer = BytesIO()
    pil_image.save(buffer, format="PNG")
    buffer.seek(0)

    qimage = QImage()
    qimage.loadFromData(buffer.getvalue(), "PNG")
    return QPixmap.fromImage(qimage)


# --------------------------------------------------------------------------
# Input Controller - wraps all PyAutoGUI interactions
# --------------------------------------------------------------------------

class InputController:
    """
    Translates parsed JSON command dictionaries into real mouse/keyboard
    events using PyAutoGUI. Kept isolated from networking/GUI concerns
    so the dispatch logic stays simple and testable.
    """

    def __init__(self):
        # Dispatch table mapping message "type" -> handler method.
        self._handlers = {
            MSG_MOVE: self.handle_move,
            MSG_LEFT_CLICK: self.handle_left_click,
            MSG_RIGHT_CLICK: self.handle_right_click,
            MSG_DOUBLE_CLICK: self.handle_double_click,
            MSG_MOUSE_DOWN: self.handle_mouse_down,
            MSG_MOUSE_UP: self.handle_mouse_up,
            MSG_SCROLL: self.handle_scroll,
            MSG_KEY: self.handle_key,
            MSG_TEXT: self.handle_text,
            MSG_HOTKEY: self.handle_hotkey,
        }

    def dispatch(self, message: dict) -> None:
        """Look up and execute the handler for the given message's type."""
        msg_type = message.get("type")
        handler = self._handlers.get(msg_type)

        if handler is None:
            print(f"[WARN] Unknown packet type: {msg_type!r} -> {message}")
            return

        handler(message)

    # ---- Mouse -----------------------------------------------------

    def handle_move(self, message: dict) -> None:
        dx = message.get("dx", 0)
        dy = message.get("dy", 0)
        pyautogui.moveRel(int(dx), int(dy))

    def handle_left_click(self, message: dict) -> None:
        pyautogui.click()

    def handle_right_click(self, message: dict) -> None:
        pyautogui.rightClick()

    def handle_double_click(self, message: dict) -> None:
        pyautogui.doubleClick()

    def handle_mouse_down(self, message: dict) -> None:
        pyautogui.mouseDown()

    def handle_mouse_up(self, message: dict) -> None:
        pyautogui.mouseUp()

    def handle_scroll(self, message: dict) -> None:
        amount = message.get("amount", 0)
        pyautogui.scroll(int(amount))

    # ---- Keyboard ----------------------------------------------------

    def handle_key(self, message: dict) -> None:
        """
        Handle both single characters (letters, numbers, punctuation,
        symbols) and named special keys (enter, backspace, esc, etc.)
        through a single call to pyautogui.press(), avoiding hundreds
        of explicit if/elif branches.
        """
        key = message.get("key", "")
        if not key:
            return

        normalized = key.lower() if key.lower() in SPECIAL_KEYS else key

        try:
            pyautogui.press(normalized)
        except Exception:
            print(f"[WARN] Unsupported key press: {key!r}")

    def handle_text(self, message: dict) -> None:
        text = message.get("text", "")
        if text:
            pyautogui.write(text)

    def handle_hotkey(self, message: dict) -> None:
        keys = message.get("keys", [])
        if not keys:
            return
        try:
            pyautogui.hotkey(*keys)
        except Exception:
            print(f"[WARN] Unsupported hotkey combination: {keys!r}")


# --------------------------------------------------------------------------
# Qt signal bridge (thread-safe GUI updates from the WebSocket thread)
# --------------------------------------------------------------------------

class ConnectionBridge(QObject):
    """
    Bridges the asyncio WebSocket thread and the Qt main thread.
    Qt signals are thread-safe: emitting from a worker thread and
    connecting a slot on the main thread queues the call correctly.
    """

    client_connected = pyqtSignal(str)
    client_disconnected = pyqtSignal()


# --------------------------------------------------------------------------
# WebSocket Server
# --------------------------------------------------------------------------

class RemoteControlServer:
    """
    Runs an asyncio WebSocket server on its own thread/event loop so
    the PyQt GUI event loop is never blocked. Only one client may be
    connected at a time; a new connection evicts the previous one.
    """

    def __init__(self, bridge: ConnectionBridge, host: str, port: int):
        self.bridge = bridge
        self.host = host
        self.port = port
        self.controller = InputController()

        self._loop: asyncio.AbstractEventLoop | None = None
        self._current_client: WebSocketServerProtocol | None = None
        self._server_thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the WebSocket server on a dedicated background thread."""
        self._server_thread = threading.Thread(
            target=self._run_event_loop, daemon=True
        )
        self._server_thread.start()

    def _run_event_loop(self) -> None:
        """Entry point for the background thread: owns its own event loop."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_until_complete(self._serve())
        except Exception:
            print("[ERROR] WebSocket server crashed:")
            traceback.print_exc()

    async def _serve(self) -> None:
        print(f"[INFO] Server started on ws://{self.host}:{self.port}")
        async with websockets.serve(self._handle_client, self.host, self.port):
            # Run forever until the process exits.
            await asyncio.Future()

    async def _handle_client(self, websocket: WebSocketServerProtocol) -> None:
        """
        Handle the lifecycle of a single client connection: eviction of
        any prior client, message loop, and cleanup on disconnect.
        """
        # Only one active client is allowed. Kick the previous one out.
        if self._current_client is not None and self._current_client.open:
            print("[INFO] New client connected, dropping previous client.")
            try:
                await self._current_client.close(reason="Replaced by new client")
            except Exception:
                pass

        self._current_client = websocket
        client_address = websocket.remote_address[0] if websocket.remote_address else "unknown"
        print(f"[INFO] Client connected: {client_address}")
        self.bridge.client_connected.emit(client_address)

        try:
            async for raw_message in websocket:
                self._process_message(raw_message)
        except websockets.ConnectionClosed:
            pass
        except Exception:
            print("[ERROR] Unexpected error in client message loop:")
            traceback.print_exc()
        finally:
            # Only clear/notify if this socket is still the active one
            # (it may have already been replaced by a newer connection).
            if self._current_client is websocket:
                self._current_client = None
                print(f"[INFO] Client disconnected: {client_address}")
                self.bridge.client_disconnected.emit()

    def _process_message(self, raw_message: str) -> None:
        """
        Parse and dispatch a single incoming WebSocket text frame.
        Never raises: malformed JSON or handler errors are caught and
        logged so the server keeps running.
        """
        print(f"[RECV] {raw_message}")

        try:
            message = json.loads(raw_message)
        except (json.JSONDecodeError, TypeError) as exc:
            print(f"[WARN] Ignoring malformed JSON: {exc}")
            return

        if not isinstance(message, dict):
            print(f"[WARN] Ignoring non-object JSON payload: {message!r}")
            return

        try:
            self.controller.dispatch(message)
        except Exception:
            print("[ERROR] Exception while handling message:")
            traceback.print_exc()


# --------------------------------------------------------------------------
# PyQt5 Main Window
# --------------------------------------------------------------------------

DARK_STYLESHEET = """
QWidget {
    background-color: #1e1e2e;
    color: #e0e0e0;
    font-family: 'Segoe UI', Arial, sans-serif;
}

QLabel#titleLabel {
    font-size: 18px;
    font-weight: bold;
    color: #ffffff;
}

QLabel#instructionsLabel {
    font-size: 11px;
    color: #a0a0b0;
}

QLabel#infoLabel {
    font-size: 11px;
    color: #c0c0d0;
}

QFrame#qrFrame {
    background-color: #ffffff;
    border-radius: 8px;
    padding: 8px;
}

QLabel#statusLabel {
    font-size: 13px;
    font-weight: bold;
    padding: 6px;
    border-radius: 6px;
}
"""

STATUS_DISCONNECTED_STYLE = "background-color: #3a1e1e; color: #ff6b6b;"
STATUS_CONNECTED_STYLE = "background-color: #1e3a24; color: #6bff8f;"


class MainWindow(QWidget):
    """Main desktop companion window: title, QR code, IP info, status."""

    def __init__(self):
        super().__init__()

        self.bridge = ConnectionBridge()
        self.bridge.client_connected.connect(self.on_client_connected)
        self.bridge.client_disconnected.connect(self.on_client_disconnected)

        self.local_ip = get_local_ip()
        self.ws_url = build_websocket_url(self.local_ip, WEBSOCKET_PORT)

        self._init_ui()

        self.server = RemoteControlServer(self.bridge, WEBSOCKET_HOST, WEBSOCKET_PORT)
        self.server.start()

    # ---- UI setup ------------------------------------------------------

    def _init_ui(self) -> None:
        self.setWindowTitle("Remote PC Controller")
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setStyleSheet(DARK_STYLESHEET)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # Title
        title_label = QLabel("Remote PC Controller")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Instructions
        instructions_label = QLabel(
            "Open the mobile app and scan the QR code below to connect."
        )
        instructions_label.setObjectName("instructionsLabel")
        instructions_label.setAlignment(Qt.AlignCenter)
        instructions_label.setWordWrap(True)
        layout.addWidget(instructions_label)

        # QR Code
        qr_frame = QFrame()
        qr_frame.setObjectName("qrFrame")
        qr_layout = QVBoxLayout()
        qr_layout.setContentsMargins(0, 0, 0, 0)

        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignCenter)
        qr_pixmap = generate_qr_pixmap(self.ws_url)
        self.qr_label.setPixmap(
            qr_pixmap.scaled(220, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        qr_layout.addWidget(self.qr_label)
        qr_frame.setLayout(qr_layout)

        qr_wrapper = QHBoxLayout()
        qr_wrapper.addStretch()
        qr_wrapper.addWidget(qr_frame)
        qr_wrapper.addStretch()
        layout.addLayout(qr_wrapper)

        # IP Address
        self.ip_label = QLabel(f"IP Address: {self.local_ip}")
        self.ip_label.setObjectName("infoLabel")
        self.ip_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.ip_label)

        # WebSocket URL
        self.url_label = QLabel(f"WebSocket: {self.ws_url}")
        self.url_label.setObjectName("infoLabel")
        self.url_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.url_label)

        # Connection status
        self.status_label = QLabel("● Disconnected")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(STATUS_DISCONNECTED_STYLE)
        layout.addWidget(self.status_label)

        layout.addStretch()
        self.setLayout(layout)

    # ---- Slots (invoked safely on the Qt main thread via signals) ------

    def on_client_connected(self, client_address: str) -> None:
        self.status_label.setText(f"● Connected ({client_address})")
        self.status_label.setStyleSheet(STATUS_CONNECTED_STYLE)

    def on_client_disconnected(self) -> None:
        self.status_label.setText("● Disconnected")
        self.status_label.setStyleSheet(STATUS_DISCONNECTED_STYLE)


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()