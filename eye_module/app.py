from __future__ import annotations

import asyncio

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect


app = FastAPI(title="Eye Module")

camera: cv2.VideoCapture | None = None
active_websocket: WebSocket | None = None
connection_lock = asyncio.Lock()
camera_lock = asyncio.Lock()


@app.on_event("startup")
async def startup() -> None:
    global camera
    camera = cv2.VideoCapture(0)


@app.on_event("shutdown")
async def shutdown() -> None:
    global camera
    if camera is not None:
        camera.release()
        camera = None


@app.get("/")
async def health() -> dict[str, str]:
    return {"status": "ready"}


def build_placeholder_frame(message: str) -> bytes:
    canvas = np.zeros((720, 1280, 3), dtype=np.uint8)
    canvas[:] = (18, 24, 38)
    cv2.rectangle(canvas, (48, 48), (1232, 672), (77, 102, 164), 3)
    cv2.putText(
        canvas,
        "Eye Module",
        (84, 144),
        cv2.FONT_HERSHEY_SIMPLEX,
        2.0,
        (240, 245, 255),
        4,
        cv2.LINE_AA,
    )
    cv2.putText(
        canvas,
        message,
        (84, 228),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (196, 211, 255),
        2,
        cv2.LINE_AA,
    )
    success, encoded = cv2.imencode(".jpg", canvas, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not success:
        raise RuntimeError("Failed to encode placeholder frame")
    return encoded.tobytes()


def capture_frame_sync() -> bytes:
    if camera is None or not camera.isOpened():
        return build_placeholder_frame("camera unavailable")

    success, frame = camera.read()
    if not success or frame is None:
        return build_placeholder_frame("camera frame unavailable")

    success, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not success:
        return build_placeholder_frame("jpeg encoding failed")

    return encoded.tobytes()


async def capture_frame() -> bytes:
    async with camera_lock:
        return await asyncio.to_thread(capture_frame_sync)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    global active_websocket

    await websocket.accept()
    async with connection_lock:
        if active_websocket is not None:
            await websocket.close(code=1013)
            return
        active_websocket = websocket

    try:
        while True:
            message = await websocket.receive_text()
            if message.strip().lower() != "ping":
                continue

            frame = await capture_frame()
            await websocket.send_bytes(frame)
    except WebSocketDisconnect:
        pass
    finally:
        async with connection_lock:
            if active_websocket is websocket:
                active_websocket = None