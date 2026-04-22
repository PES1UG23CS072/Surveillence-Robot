import { type PointerEvent, useEffect, useRef, useState } from 'react';

const websocketUrl = 'ws://10.0.0.5:8030/ws';
const controlWebsocketUrl = 'ws://localhost:8020';
type Direction = 'forward' | 'back' | 'left' | 'right';

export default function App() {
  const [status, setStatus] = useState<'connecting' | 'live' | 'reconnecting'>('connecting');
  const [controlStatus, setControlStatus] = useState<'connecting' | 'live' | 'reconnecting'>(
    'connecting',
  );
  const [frameUrl, setFrameUrl] = useState<string | null>(null);
  const [frameCount, setFrameCount] = useState(0);
  const objectUrlRef = useRef<string | null>(null);
  const controlSocketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimer: number | undefined;
    let disposed = false;

    const connect = () => {
      setStatus((current: 'connecting' | 'live' | 'reconnecting') =>
        current === 'connecting' ? current : 'reconnecting',
      );
      socket = new WebSocket(websocketUrl);
      socket.binaryType = 'blob';

      socket.onopen = () => {
        if (!disposed) {
          setStatus('live');
        }
      };

      socket.onmessage = (event) => {
        const payload = event.data instanceof Blob ? event.data : new Blob([event.data]);
        const nextUrl = URL.createObjectURL(payload);

        if (objectUrlRef.current) {
          URL.revokeObjectURL(objectUrlRef.current);
        }

        objectUrlRef.current = nextUrl;
        setFrameUrl(nextUrl);
        setFrameCount((count: number) => count + 1);
      };

      socket.onclose = () => {
        if (disposed) {
          return;
        }

        setStatus('reconnecting');
        reconnectTimer = window.setTimeout(connect, 1000);
      };

      socket.onerror = () => {
        socket?.close();
      };
    };

    connect();

    return () => {
      disposed = true;
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer);
      }
      socket?.close();
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
      }
    };
  }, []);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimer: number | undefined;
    let disposed = false;

    const connect = () => {
      setControlStatus((current: 'connecting' | 'live' | 'reconnecting') =>
        current === 'connecting' ? current : 'reconnecting',
      );
      socket = new WebSocket(controlWebsocketUrl);
      controlSocketRef.current = socket;

      socket.onopen = () => {
        if (!disposed) {
          setControlStatus('live');
        }
      };

      socket.onclose = () => {
        if (disposed) {
          return;
        }
        setControlStatus('reconnecting');
        reconnectTimer = window.setTimeout(connect, 1000);
      };

      socket.onerror = () => {
        socket?.close();
      };
    };

    connect();

    return () => {
      disposed = true;
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer);
      }
      socket?.close();
      controlSocketRef.current = null;
    };
  }, []);

  const sendControl = (direction: Direction | 'stop') => {
    const socket = controlSocketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return;
    }
    socket.send(direction);
  };

  const handlePress = (event: PointerEvent<HTMLButtonElement>, direction: Direction) => {
    event.currentTarget.setPointerCapture(event.pointerId);
    sendControl(direction);
  };

  const handleRelease = () => {
    sendControl('stop');
  };

  const statusLabel =
    status === 'live' ? 'Live' : status === 'connecting' ? 'Connecting' : 'Reconnecting';
  const controlStatusLabel =
    controlStatus === 'live'
      ? 'Live'
      : controlStatus === 'connecting'
        ? 'Connecting'
        : 'Reconnecting';

  const controls = [
    {
      key: 'forward',
      label: 'Forward',
      arrow: '↑',
      classes: 'col-start-2 row-start-1',
    },
    {
      key: 'left',
      label: 'Left',
      arrow: '←',
      classes: 'col-start-1 row-start-2',
    },
    {
      key: 'right',
      label: 'Right',
      arrow: '→',
      classes: 'col-start-3 row-start-2',
    },
    {
      key: 'back',
      label: 'Back',
      arrow: '↓',
      classes: 'col-start-2 row-start-3',
    },
  ] as const;

  return (
    <main className="min-h-screen overflow-hidden bg-[#050816] text-slate-100">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(64,133,255,0.28),_transparent_40%),radial-gradient(circle_at_bottom_right,_rgba(255,255,255,0.08),_transparent_28%),linear-gradient(160deg,_#050816,_#0a1020_45%,_#0d172e)]" />
      <div className="relative mx-auto flex min-h-screen w-full max-w-6xl flex-col justify-center px-4 py-8 sm:px-8 lg:px-12">
        <div className="mb-8 flex items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.38em] text-cyan-200/80">Surveillence Robot</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white sm:text-5xl">
              Live camera relay
            </h1>
          </div>
          <div className="rounded-full border border-cyan-300/20 bg-white/5 px-4 py-2 text-sm text-cyan-100 shadow-[0_0_40px_rgba(80,180,255,0.12)] backdrop-blur">
            {statusLabel}
          </div>
        </div>

        <section className="grid gap-6 lg:grid-cols-[1.35fr_0.65fr]">
          <div className="rounded-[2rem] border border-white/10 bg-white/5 p-4 shadow-2xl shadow-black/30 backdrop-blur-xl">
            <div className="flex items-center justify-between px-2 pb-4 text-sm text-slate-300">
              <span>Broadcast feed</span>
              <span>{frameCount} frames</span>
            </div>
            <div className="relative overflow-hidden rounded-[1.5rem] border border-white/10 bg-[#07111f]">
              {frameUrl ? (
                <img
                  src={frameUrl}
                  alt="Live broadcast from the eye module"
                  className="aspect-video w-full object-contain"
                />
              ) : (
                <div className="flex aspect-video items-center justify-center p-10 text-center text-slate-400">
                  Waiting for the first frame from the broadcaster.
                </div>
              )}
            </div>
          </div>

          <aside className="rounded-[2rem] border border-white/10 bg-white/5 p-6 shadow-2xl shadow-black/30 backdrop-blur-xl">
            <div className="space-y-3">
              <p className="text-sm uppercase tracking-[0.32em] text-cyan-200/80">Connection</p>
              <p className="text-2xl font-medium text-white">{websocketUrl}</p>
              <p className="text-sm leading-6 text-slate-300">
                The frontend stays attached to the broadcaster, which keeps requesting fresh JPEG
                frames from the eye module and rebroadcasting them in sequence.
              </p>
            </div>

            <div className="mt-8 grid gap-4 text-sm text-slate-300">
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <p className="text-slate-400">Frontend socket</p>
                <p className="mt-1 text-white">ws://localhost:8030/ws</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <p className="text-slate-400">Control socket</p>
                <p className="mt-1 text-white">{controlWebsocketUrl}</p>
                <p className="mt-1 text-xs text-cyan-100/80">{controlStatusLabel}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <p className="text-slate-400">Eye module socket</p>
                <p className="mt-1 text-white">ws://localhost:3010/ws</p>
              </div>
            </div>

            <div className="mt-8">
              <p className="mb-3 text-sm uppercase tracking-[0.32em] text-cyan-200/80">Drive control</p>
              <div className="mx-auto grid w-full max-w-[14rem] grid-cols-3 grid-rows-3 gap-2">
                {controls.map((control) => (
                  <button
                    key={control.key}
                    type="button"
                    className={`${control.classes} touch-none select-none rounded-2xl border border-cyan-200/20 bg-cyan-500/10 p-4 text-center text-white transition hover:bg-cyan-400/20 active:scale-[0.98] active:bg-cyan-300/25`}
                    onPointerDown={(event) => handlePress(event, control.key)}
                    onPointerUp={handleRelease}
                    onPointerCancel={handleRelease}
                    onPointerLeave={handleRelease}
                  >
                    <div className="text-2xl leading-none">{control.arrow}</div>
                    <div className="mt-1 text-xs uppercase tracking-[0.2em] text-cyan-100/80">
                      {control.label}
                    </div>
                  </button>
                ))}
              </div>
              <p className="mt-3 text-xs text-slate-400">
                Press and hold to move. Releasing the button sends <span className="text-white">stop</span>.
              </p>
            </div>
          </aside>
        </section>
      </div>
    </main>
  );
}