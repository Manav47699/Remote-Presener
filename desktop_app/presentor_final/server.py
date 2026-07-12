#!/usr/bin/env python3
import asyncio
import json
import socket
import sys
from evdev import UInput, ecodes as e

# Configuration
WEBSOCKET_HOST = "0.0.0.0"
WEBSOCKET_PORT = 8080

# Initialize Virtual Kernel Keyboard Layout
try:
    ui = UInput({e.EV_KEY: [e.KEY_LEFT, e.KEY_RIGHT]})
    print("[*] Virtual Kernel Keyboard initialized successfully.")
except Exception as init_err:
    print(f"[!] Kernel Input Error: {init_err}")
    print("[!] Please run: sudo chmod +0666 /dev/uinput")
    sys.exit(1)

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

async def handle_client(websocket):
    client_ip = websocket.remote_address[0] if websocket.remote_address else "Unknown"
    print(f"\n[+] Client connected from: {client_ip}")
    
    try:
        async for raw_message in websocket:
            payload = json.loads(raw_message)
            if payload.get("type") == "press" and payload.get("key") in ["up", "down"]:
                # Map to kernel keycodes cleanly using the 'e' import
                target_key = e.KEY_LEFT if payload["key"] == "up" else e.KEY_RIGHT
                key_name = "LEFT" if payload["key"] == "up" else "RIGHT"
                print(f"[*] Simulating kernel-level keypress: {key_name}")
                
                # Fire Key Down event, Key Up event, and flush immediately
                ui.write(e.EV_KEY, target_key, 1)
                ui.write(e.EV_KEY, target_key, 0)
                ui.syn()
                
    except asyncio.CancelledError:
        pass
    except Exception as err:  # Changed 'e' to 'err' to prevent variable collision
        print(f"[!] Error handling client: {err}")
    finally:
        print(f"[-] Client {client_ip} session finished.")

async def main():
    local_ip = get_local_ip()
    print("=" * 50)
    print("      KERNEL-LEVEL BACKEND (WAYLAND PROOF)      ")
    print("=" * 50)
    print(f"Local IP Detected : {local_ip}")
    print(f"TARGET LINK FOR PHONE: ws://{local_ip}:{WEBSOCKET_PORT}")
    print("=" * 50)
    print("[*] Waiting for phone commands...")

    async with websockets.serve(handle_client, WEBSOCKET_HOST, WEBSOCKET_PORT):
        await asyncio.Future()

if __name__ == "__main__":
    import websockets
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[-] Server shut down gracefully.")