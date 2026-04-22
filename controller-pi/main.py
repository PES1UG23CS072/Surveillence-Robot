#!/usr/bin/env python3
"""WebSocket to serial bridge for robot movement commands.

Listens on ws://0.0.0.0:8020 and relays allowed movement commands to an
Arduino connected over serial.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from typing import Optional

import serial
from serial.tools import list_ports
from websockets.server import WebSocketServerProtocol, serve

ALLOWED_COMMANDS = {"stop", "forward", "back", "left", "right"}


class SerialBridge:
    def __init__(self, baudrate: int = 115200, preferred_port: str = "/dev/ttyUSB0") -> None:
        self.baudrate = baudrate
        self.preferred_port = preferred_port
        self._serial: Optional[serial.Serial] = None
        self._lock = asyncio.Lock()

    def _detect_port(self) -> str:
        # Prefer an explicit USB serial path if it exists.
        ports = list(list_ports.comports())
        available = {port.device for port in ports}
        if self.preferred_port in available:
            return self.preferred_port

        # Prefer likely Arduino devices next.
        for port in ports:
            text = " ".join(
                [
                    str(port.description or ""),
                    str(port.manufacturer or ""),
                    str(port.product or ""),
                ]
            ).lower()
            if "arduino" in text:
                return port.device

        for port in ports:
            if port.device.startswith("/dev/ttyUSB") or port.device.startswith("/dev/ttyACM"):
                return port.device

        raise RuntimeError("No Arduino-compatible serial port found")

    async def ensure_open(self) -> serial.Serial:
        async with self._lock:
            if self._serial is not None and self._serial.is_open:
                return self._serial

            port = self._detect_port()
            logging.info("Opening serial connection on %s @ %d", port, self.baudrate)
            self._serial = serial.Serial(port=port, baudrate=self.baudrate, timeout=0.1)
            # Give Arduino a moment after opening serial.
            await asyncio.sleep(2)
            return self._serial

    async def send(self, message: str) -> None:
        if message not in ALLOWED_COMMANDS:
            return

        try:
            ser = await self.ensure_open()
            ser.write(f"{message}\n".encode("utf-8"))
            ser.flush()
            logging.info("Relayed command: %s", message)
        except Exception:
            logging.exception("Serial write failed, will retry on next command")
            await self.close()

    async def close(self) -> None:
        async with self._lock:
            if self._serial is not None:
                try:
                    self._serial.close()
                finally:
                    self._serial = None


async def ws_handler(websocket: WebSocketServerProtocol, bridge: SerialBridge) -> None:
    remote = websocket.remote_address
    logging.info("Controller connected: %s", remote)
    try:
        async for raw in websocket:
            cmd = str(raw).strip().lower()
            if cmd not in ALLOWED_COMMANDS:
                logging.warning("Ignoring unsupported command from %s: %r", remote, raw)
                continue
            await bridge.send(cmd)
    except Exception:
        logging.exception("WebSocket client error: %s", remote)
    finally:
        logging.info("Controller disconnected: %s", remote)


async def run_server(host: str, port: int, baudrate: int, preferred_port: str) -> None:
    bridge = SerialBridge(baudrate=baudrate, preferred_port=preferred_port)

    async def handler(websocket: WebSocketServerProtocol) -> None:
        await ws_handler(websocket, bridge)

    async with serve(handler, host, port):
        logging.info("WebSocket server started at ws://%s:%d", host, port)
        await asyncio.Future()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Robot control WebSocket to serial bridge")
    parser.add_argument("--host", default="0.0.0.0", help="WebSocket bind host")
    parser.add_argument("--port", type=int, default=8020, help="WebSocket bind port")
    parser.add_argument("--baudrate", type=int, default=115200, help="Serial baudrate")
    parser.add_argument(
        "--serial-port",
        default="/dev/ttyUSB0",
        help="Preferred serial port; auto-detect is used if unavailable",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run_server(args.host, args.port, args.baudrate, args.serial_port))


if __name__ == "__main__":
    main()
