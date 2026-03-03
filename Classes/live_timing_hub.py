from __future__ import annotations

import asyncio
import json
import threading
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from Modules.log_utils import log


EVENT_COLOR_MAP: Dict[str, str] = {
    "passed": "#E6C202",
    "pole": "#9966CC",
    "end": "#545454",
    "swap": "#1E90FF",
    "pitin": "#FF8C00",
    "pitout": "#00C853",
}


@dataclass
class LiveTimingManager:
    """
    Hub Live Timing con due webserver:
    - DATA server (REST + WS): host:port
    - WEB server (pagina):      host:port+1

    Mantiene API compatibili con il codice esistente:
      - send_session_info(...)
      - send_race_data(...)
      - send_event(...)
    """

    address: str
    port: int
    root_path: Optional[str] = None

    enabled: bool = False

    _clients: Set[WebSocket] = field(default_factory=set)
    _event_clients: Set[WebSocket] = field(default_factory=set)

    _session_data: Optional[Dict[str, Any]] = None
    _drivers_data: List[Dict[str, Any]] = field(default_factory=list)

    app_data: Optional[FastAPI] = None
    app_web: Optional[FastAPI] = None

    _server_data: Optional[uvicorn.Server] = None
    _server_web: Optional[uvicorn.Server] = None

    _thread: Optional[threading.Thread] = None
    _loop: Optional[asyncio.AbstractEventLoop] = None
    _ready_evt: threading.Event = field(default_factory=threading.Event)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._ready_evt.clear()

        def _runner() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop

            try:
                loop.run_until_complete(self._start_async())
                self._ready_evt.set()
                loop.run_forever()
            finally:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                loop.close()

        self._thread = threading.Thread(target=_runner, name="LiveTimingServerThread", daemon=True)
        self._thread.start()
        self._ready_evt.wait(timeout=5)

    def stop(self) -> None:
        if not self._loop:
            return

        asyncio.run_coroutine_threadsafe(self._stop_async(), self._loop)
        self._loop.call_soon_threadsafe(self._loop.stop)

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

        self.enabled = False
        self._loop = None

    def build_app_data(self) -> FastAPI:
        app = FastAPI()

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @app.get("/api/snapshot")
        async def snapshot() -> Dict[str, Any]:
            return {
                "session": self._session_data,
                "drivers": self._drivers_data,
            }

        @app.websocket("/ws/timing")
        async def ws_timing(ws: WebSocket) -> None:
            await ws.accept()
            self._clients.add(ws)

            await ws.send_text(
                json.dumps(
                    {
                        "type": "snapshot",
                        "data": {
                            "session": self._session_data,
                            "drivers": self._drivers_data,
                        },
                    }
                )
            )

            try:
                while True:
                    await ws.receive_text()
            except WebSocketDisconnect:
                self._clients.discard(ws)

        @app.websocket("/ws/event")
        async def ws_event(ws: WebSocket) -> None:
            await ws.accept()
            self._event_clients.add(ws)

            try:
                while True:
                    await ws.receive_text()
            except WebSocketDisconnect:
                self._event_clients.discard(ws)

        return app

    def build_app_web(self) -> FastAPI:
        app = FastAPI()

        @app.get("/")
        async def index() -> HTMLResponse:
            return HTMLResponse(self._html_page())

        @app.get("/assets/logo.webp", response_model=None)
        async def logo() -> Any:
            if not self.root_path:
                return JSONResponse(status_code=404, content={})

            p = Path(self.root_path) / "Resources" / "logos" / "e-horizon logo.webp"
            if p.exists():
                return FileResponse(str(p), media_type="image/webp")
            return JSONResponse(status_code=404, content={})

        return app

    def _html_page(self) -> str:
        return f"""
<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>E-Horizon LiveTiming</title>
<style>
:root {{
  --bg: #070a0f;
  --panel: #0d1320;
  --line: rgba(255,255,255,.10);
  --text: #ffffff;
  --muted: #9db0cf;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background: radial-gradient(circle at top, #13233f 0%, var(--bg) 40%);
  color: var(--text);
  font-family: system-ui, sans-serif;
}}
.main {{
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}}
.header {{
  display:flex;
  flex-wrap:wrap;
  align-items:center;
  justify-content:space-between;
  gap:12px;
  margin-bottom:16px;
}}
.timer {{ font-size: clamp(24px, 4vw, 42px); font-weight: 700; }}
.meta {{ color: var(--muted); }}
.panel {{
  background: color-mix(in srgb, var(--panel) 92%, black 8%);
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
}}
table {{ width:100%; border-collapse:collapse; }}
th, td {{ padding: 12px; border-bottom: 1px solid var(--line); text-align:left; }}
th {{ color: var(--muted); font-weight: 600; }}
tr.row {{ transition: background-color .35s ease; }}
tr.row:nth-child(even) {{ background: rgba(255,255,255,.02); }}
.badge {{
  font-size: 12px;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 2px 10px;
  color: var(--muted);
}}
.flash-passed {{ background-color:{EVENT_COLOR_MAP['passed']} !important; color:#101010; }}
.flash-pole   {{ background-color:{EVENT_COLOR_MAP['pole']} !important; }}
.flash-end    {{ background-color:{EVENT_COLOR_MAP['end']} !important; }}
.flash-swap   {{ background-color:{EVENT_COLOR_MAP['swap']} !important; }}
.flash-pitin  {{ background-color:{EVENT_COLOR_MAP['pitin']} !important; }}
.flash-pitout {{ background-color:{EVENT_COLOR_MAP['pitout']} !important; color:#101010; }}
</style>
</head>
<body>
  <main class="main">
    <div class="header">
      <div>
        <h1 style="margin:0">E-Horizon Live Timing</h1>
        <div id="sessionMeta" class="meta">In attesa dati sessione...</div>
      </div>
      <div id="timer" class="timer">--:--:--</div>
    </div>

    <div class="panel">
      <table>
        <thead>
          <tr>
            <th>Pos</th>
            <th>Pilota</th>
            <th>Team</th>
            <th>S1</th>
            <th>S2</th>
            <th>S3</th>
            <th>Best</th>
            <th>Laps</th>
            <th>Status</th>
            <th>Gap</th>
            <th>Int</th>
            <th>Last</th>
          </tr>
        </thead>
        <tbody id="rows"></tbody>
      </table>
    </div>
  </main>

<script>
const DATA_PORT = {self.port};
const host = window.location.hostname || 'localhost';
const apiBase = `http://${{host}}:${{DATA_PORT}}`;
const wsBase  = `ws://${{host}}:${{DATA_PORT}}`;

const elRows = document.getElementById("rows");
const elTimer = document.getElementById("timer");
const elMeta = document.getElementById("sessionMeta");

const state = {{ rows: new Map() }};

function render(drivers) {{
  if (!Array.isArray(drivers)) return;

  drivers.sort((a,b) => (a.position || 999) - (b.position || 999));

  elRows.innerHTML = drivers.map(d => `
    <tr class="row" data-key="${{d.number ?? d.driverId ?? d.raceNumber ?? ''}}">
      <td>${{d.position ?? ''}}</td>
      <td>${{d.name ?? ''}}</td>
      <td>${{d.team ?? ''}}</td>
      <td>${{d.s1 ?? ''}}</td>
      <td>${{d.s2 ?? ''}}</td>
      <td>${{d.s3 ?? ''}}</td>
      <td>${{d.best ?? ''}}</td>
      <td>${{d.laps ?? ''}}</td>
      <td><span class="badge">${{d.status ?? ''}}</span></td>
      <td>${{d.gap ?? ''}}</td>
      <td>${{d.interval ?? ''}}</td>
      <td>${{d.lastLap ?? ''}}</td>
    </tr>`).join("");

  state.rows.clear();
  elRows.querySelectorAll("tr").forEach(tr => state.rows.set(String(tr.dataset.key), tr));
}}

function flash(key, kind) {{
  const row = state.rows.get(String(key));
  if (!row || !kind) return;

  const cls = "flash-" + String(kind).toLowerCase();
  row.classList.add(cls);
  setTimeout(() => row.classList.remove(cls), 800);
}}

function updateSession(data) {{
  if (!data || typeof data !== 'object') return;
  elTimer.textContent = data.sessionTime || '--:--:--';

  const type = data.sessionType || 'Session';
  const status = data.sessionStatus || 'N/A';
  const idx = data.index != null ? ` #${{data.index + 1}}` : '';
  elMeta.textContent = `${{type}}${{idx}} - ${{status}}`;
}}

async function boot() {{
  try {{
    const res = await fetch(`${{apiBase}}/api/snapshot`);
    const snap = await res.json();
    updateSession(snap.session);
    render(snap.drivers || []);
  }} catch (_) {{}}

  const ws = new WebSocket(`${{wsBase}}/ws/timing`);
  ws.onmessage = e => {{
    const msg = JSON.parse(e.data);
    if (msg.type === 'snapshot') {{
      updateSession(msg.data.session);
      render(msg.data.drivers || []);
    }}
    if (msg.type === 'drivers') render(msg.data || []);
    if (msg.type === 'session') updateSession(msg.data);
  }};

  const we = new WebSocket(`${{wsBase}}/ws/event`);
  we.onmessage = e => {{
    const msg = JSON.parse(e.data);
    if (msg.type === 'event') flash(msg.data.key, msg.data.kind);
  }};
}}

boot();
</script>
</body>
</html>
"""

    async def _start_async(self) -> None:
        self.app_data = self.build_app_data()
        self.app_web = self.build_app_web()

        self._server_data = uvicorn.Server(
            uvicorn.Config(self.app_data, host=self.address, port=self.port, log_level="warning")
        )
        self._server_web = uvicorn.Server(
            uvicorn.Config(self.app_web, host=self.address, port=self.port + 1, log_level="warning")
        )

        # log reachable URLs for data and web endpoints
        try:
            log(f"[LiveTiming] DATA server listening at http://{self.address}:{self.port}")
            log(f"[LiveTiming] WEB page available at http://{self.address}:{self.port + 1}")
        except Exception:
            pass

        self.enabled = True
        asyncio.create_task(self._server_data.serve())
        asyncio.create_task(self._server_web.serve())

    async def _stop_async(self) -> None:
        if self._server_data:
            self._server_data.should_exit = True
        if self._server_web:
            self._server_web.should_exit = True

    def send_session_info(self, data: Any) -> None:
        self._session_data = self._normalize_session_data(data)
        self._run_in_loop(
            self._broadcast({
                "type": "session",
                "data": self._session_data,
            })
        )

    def send_race_data(self, drivers: Iterable[Any]) -> None:
        self._drivers_data = self._normalize_drivers_data(drivers)
        self._run_in_loop(
            self._broadcast({
                "type": "drivers",
                "data": self._drivers_data,
            })
        )

    def send_event(self, key: int, kind: str) -> None:
        payload = {
            "type": "event",
            "data": {
                "key": key,
                "kind": str(kind).lower(),
            },
        }
        self._run_in_loop(self._broadcast_event(payload))

    def _run_in_loop(self, coro: Any) -> None:
        if not self._loop or not self.enabled:
            return
        asyncio.run_coroutine_threadsafe(coro, self._loop)

    def _normalize_session_data(self, data: Any) -> Dict[str, Any]:
        if isinstance(data, dict):
            return self._json_ready(data)

        if hasattr(data, "session_to_live_dict") and callable(getattr(data, "session_to_live_dict")):
            try:
                return self._json_ready(data.session_to_live_dict())
            except Exception:
                pass

        if hasattr(data, "to_live_dict") and callable(getattr(data, "to_live_dict")):
            try:
                return self._json_ready(data.to_live_dict())
            except Exception:
                pass

        return self._json_ready(data)

    def _normalize_drivers_data(self, drivers: Iterable[Any]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for item in list(drivers or []):
            if isinstance(item, dict):
                out.append(self._json_ready(item))
                continue

            if hasattr(item, "to_live_dict") and callable(getattr(item, "to_live_dict")):
                try:
                    out.append(self._json_ready(item.to_live_dict()))
                    continue
                except Exception:
                    pass

            out.append(self._json_ready(item))
        return out

    def _json_ready(self, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, (date, time)):
            return value.isoformat()
        if isinstance(value, timedelta):
            return str(value)

        if isinstance(value, dict):
            return {str(k): self._json_ready(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._json_ready(v) for v in value]

        if is_dataclass(value):
            return self._json_ready(asdict(value))

        if hasattr(value, "__dict__"):
            return self._json_ready(vars(value))

        return str(value)

    async def _broadcast(self, payload: Dict[str, Any]) -> None:
        msg = json.dumps(payload, ensure_ascii=False)
        for ws in list(self._clients):
            try:
                await ws.send_text(msg)
            except Exception:
                self._clients.discard(ws)

    async def _broadcast_event(self, payload: Dict[str, Any]) -> None:
        msg = json.dumps(payload, ensure_ascii=False)
        for ws in list(self._event_clients):
            try:
                await ws.send_text(msg)
            except Exception:
                self._event_clients.discard(ws)
