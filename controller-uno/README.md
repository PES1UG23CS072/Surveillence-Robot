# Controller UNO

Upload [controller_uno.ino](controller_uno.ino) to your Arduino UNO.

## Serial Protocol

Send one line per command at `115200` baud:

- `forward`
- `back`
- `left`
- `right`
- `stop`

Any unknown command is treated as `stop` for safety.

## L298N Pin Mapping Used In Code

- `ENA` -> UNO D5 (PWM)
- `IN1` -> UNO D8
- `IN2` -> UNO D9
- `IN3` -> UNO D10
- `IN4` -> UNO D11
- `ENB` -> UNO D6 (PWM)
