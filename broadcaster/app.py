from __future__ import annotations

import asyncio
import contextlib

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import websockets
from websockets.exceptions import ConnectionClosed


app = FastAPI(title="Broadcaster")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

eye_module_url = "ws://127.0.0.1:3010/ws"
connected_clients: set[WebSocket] = set()
clients_lock = asyncio.Lock()
latest_frame: bytes | None = None
relay_task: asyncio.Task[None] | None = None


@app.get("/")
async def health() -> dict[str, str]:
    return {"status": "ready"}


async def register_client(websocket: WebSocket) -> None:
    async with clients_lock:
        connected_clients.add(websocket)


async def unregister_client(websocket: WebSocket) -> None:
    async with clients_lock:
        connected_clients.discard(websocket)


async def broadcast_frame(frame: bytes) -> None:
    global latest_frame

    latest_frame = bytes(frame)

    async with clients_lock:
        clients = list(connected_clients)

    for client in clients:
        try:
            await client.send_bytes(latest_frame)
        except Exception:
            await unregister_client(client)


async def relay_eye_module_stream() -> None:
    while True:
        try:
            async with websockets.connect(
                eye_module_url,
                ping_interval=None,
                close_timeout=1,
                max_size=None,
            ) as socket:
                while True:
                    await socket.send("ping")
                    frame = await socket.recv()
                    if isinstance(frame, str):
                        continue

                    await broadcast_frame(frame)
        except (ConnectionClosed, OSError, asyncio.TimeoutError):
            await asyncio.sleep(1)
        except Exception:
            await asyncio.sleep(1)


@app.on_event("startup")
async def startup() -> None:
    global relay_task
    relay_task = asyncio.create_task(relay_eye_module_stream())


@app.on_event("shutdown")
async def shutdown() -> None:
    global relay_task
    if relay_task is not None:
        relay_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await relay_task
        relay_task = None


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    await register_client(websocket)

    try:
        if latest_frame is not None:
            await websocket.send_bytes(latest_frame)

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await unregister_client(websocket)