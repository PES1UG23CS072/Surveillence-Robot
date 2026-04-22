from __future__ import annotations

import asyncio
from io import BytesIO

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from PIL import Image, ImageDraw
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
    image = Image.new("RGB", (1280, 720), (18, 24, 38))
    draw = ImageDraw.Draw(image)
    draw.rectangle((48, 48, 1232, 672), outline=(77, 102, 164), width=3)
    draw.text((84, 144), "Eye Module", fill=(240, 245, 255))
    draw.text((84, 228), message, fill=(196, 211, 255))

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def capture_frame_sync() -> bytes:
    if camera is None:
        return build_placeholder_frame("camera unavailable")

    try:
        frame = camera.capture_array()
    except Exception:
        return build_placeholder_frame("camera frame unavailable")

    if frame is None:
        return build_placeholder_frame("camera frame unavailable")

    try:
        image = Image.fromarray(frame)
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=90)
    except Exception:
        return build_placeholder_frame("jpeg encoding failed")

    return buffer.getvalue()


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
