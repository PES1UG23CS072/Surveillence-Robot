# eye_module

Single-client websocket service that listens on `ws://127.0.0.1:3010/ws`.

Behavior:

- accepts only one websocket client at a time
- waits for the text message `ping`
- captures a frame from the local camera
- encodes the frame as JPEG bytes
- sends the bytes back over the websocket

Run:

```bash
pip install -r requirements.txt
python main.py
```