from __future__ import annotations

import asyncio

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from picamera2 import Picamera2


app = FastAPI(title="Eye Module Pi")

camera: Picamera2 | None = None
active_websocket: WebSocket | None = None
connection_lock = asyncio.Lock()
camera_lock = asyncio.Lock()


@app.on_event("startup")
async def startup() -> None:
    global camera
    camera = Picamera2()
    config = camera.create_video_configuration(main={"size": (1280, 720), "format": "RGB888"})
    camera.configure(config)
    camera.start()


@app.on_event("shutdown")
async def shutdown() -> None:
    global camera
    if camera is not None:
        camera.stop()
        camera.close()
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
    if camera is None:
        return build_placeholder_frame("camera unavailable")

    try:
        frame = camera.capture_array()
    except Exception:
        return build_placeholder_frame("camera frame unavailable")

    if frame is None:
        return build_placeholder_frame("camera frame unavailable")

    # Picamera2 gives RGB888 in this configuration; convert to BGR for OpenCV encoding.
    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    success, encoded = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
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
