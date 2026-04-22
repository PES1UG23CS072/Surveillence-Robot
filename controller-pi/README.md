# Controller Pi

WebSocket to serial bridge for movement commands.

## Commands

Accepted websocket text messages:

- `forward`
- `back`
- `left`
- `right`
- `stop`

## Run

```bash
cd controller-pi
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python main.py
```

The server binds to `ws://0.0.0.0:8020`.

It prefers serial port `/dev/ttyUSB0` and falls back to Arduino-like devices found under `/dev/ttyUSB*` or `/dev/ttyACM*`.
