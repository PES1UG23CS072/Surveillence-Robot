# eye_module_pi

Single-client websocket service that listens on `ws://127.0.0.1:3010/ws`.

Behavior:

- accepts only one websocket client at a time
- waits for the text message `ping`
- captures a frame from the Raspberry Pi camera module
- encodes the frame as JPEG bytes
- sends the bytes back over the websocket

Run:

```bash
sudo apt update
sudo apt install -y python3-picamera2 libcamera0 libcamera-apps

# recreate venv so it can see apt-installed picamera2
python3 -m venv --system-site-packages ../venv
source ../venv/bin/activate

pip install -r requirements.txt
python3 main.py
```

Notes:

- `picamera2` should come from Raspberry Pi OS packages, not `pip install picamera2`.
- If camera access fails, confirm camera is enabled and test with `libcamera-hello`.
