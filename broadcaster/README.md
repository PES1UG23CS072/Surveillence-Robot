# broadcaster

FastAPI websocket relay that listens on `ws://127.0.0.1:8030/ws`.

Behavior:

- connects to the eye module on startup
- sends `ping` to request a frame
- receives JPEG bytes
- copies the frame and broadcasts it to every connected websocket client
- immediately requests the next frame

Run:

```bash
pip install -r requirements.txt
python main.py
```