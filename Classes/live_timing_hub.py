from __future__ import annotations

import asyncio
import json
import os
import subprocess
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
from Modules.paths import get_app_base_dir


EVENT_COLOR_MAP: Dict[str, str] = {
    "passed": "#E6C202",
    "pole": "#9966CC",
    "end": "#545454",
    "swap": "#1E90FF",
    "pitin": "#FF8C00",
    "pitout": "#00C853",
}

# Public tunnel settings (hardcoded for now, as requested).
PUBLIC_TUNNEL_DOMAIN = "alphonso-supersacerdotal-tomboyishly.ngrok-free.dev"
PUBLIC_TUNNEL_AUTHTOKEN = ""


@dataclass
class LiveTimingManager:
    """
    Hub Live Timing con server principale unico:
    - DATA + WEB server (REST + WS + pagina): host:port

    Mantiene API compatibili con il codice esistente:
      - send_session_info(...)
      - send_race_data(...)
      - send_event(...)
    """

    address: str
    port: int
    root_path: Optional[str] = None
    public_enabled: bool = True

    enabled: bool = False

    _clients: Set[WebSocket] = field(default_factory=set)
    _event_clients: Set[WebSocket] = field(default_factory=set)

    _session_data: Optional[Dict[str, Any]] = None
    _drivers_data: List[Dict[str, Any]] = field(default_factory=list)

    app_data: Optional[FastAPI] = None
    _server_data: Optional[uvicorn.Server] = None
    _server_task: Optional[asyncio.Task] = None

    _thread: Optional[threading.Thread] = None
    _loop: Optional[asyncio.AbstractEventLoop] = None
    _ready_evt: threading.Event = field(default_factory=threading.Event)
    _ngrok_proc: Optional[subprocess.Popen[str]] = None
    _ngrok_log_thread: Optional[threading.Thread] = None

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

        future = asyncio.run_coroutine_threadsafe(self._stop_async(), self._loop)
        try:
            future.result(timeout=7)
        except Exception:
            pass
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

        @app.get("/")
        async def index() -> HTMLResponse:
            return HTMLResponse(self._html_page())

        @app.get("/favicon.ico", response_model=None)
        async def favicon() -> Any:
            candidates: List[Path] = []

            if self.root_path:
                candidates.append(Path(self.root_path) / "Resources" / "icons" / "favicon.ico")

            # Fallback robusto: usa Resources dell'app (dev/packaging)
            candidates.append(get_app_base_dir() / "Resources" / "icons" / "favicon.ico")

            p = next((path for path in candidates if path.exists()), None)
            if p is not None:
                return FileResponse(str(p), media_type="image/x-icon")
            return JSONResponse(status_code=404, content={})

        @app.get("/assets/logo", response_model=None)
        async def logo() -> Any:
            candidates: List[Path] = []

            if self.root_path:
                candidates.append(Path(self.root_path) / "Resources" / "logos" / "e-horizon logo quadrato_trs.png")
                candidates.append(Path(self.root_path) / "Resources" / "logos" / "e-horizon logo.webp")

            # Fallback robusto: usa Resources dell'app (dev/packaging)
            candidates.append(get_app_base_dir() / "Resources" / "logos" / "e-horizon logo quadrato_trs.png")
            candidates.append(get_app_base_dir() / "Resources" / "logos" / "e-horizon logo.webp")

            p = next((path for path in candidates if path.exists()), None)
            if p is not None:
                media_type = "image/png" if p.suffix.lower() == ".png" else "image/webp"
                return FileResponse(str(p), media_type=media_type)
            return JSONResponse(status_code=404, content={})

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

    def _html_page(self) -> str:
        return f"""
<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>E-Horizon LiveTiming</title>
<link rel="icon" href="/favicon.ico" sizes="any">
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
.header-right {{
    display:flex;
    align-items:center;
    justify-content:flex-end;
    min-width: 220px;
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

/* Più aria ai tempi settore e alle colonne cronometriche */
th:nth-child(4), td:nth-child(4),
th:nth-child(5), td:nth-child(5),
th:nth-child(6), td:nth-child(6),
th:nth-child(7), td:nth-child(7),
th:nth-child(10), td:nth-child(10),
th:nth-child(11), td:nth-child(11),
th:nth-child(12), td:nth-child(12) {{
    min-width: 92px;
    white-space: nowrap;
    text-align: center;
    font-variant-numeric: tabular-nums;
}}
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
            <div class="header-right">
                <div id="timer" class="timer">--:--:--</div>
            </div>
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
                        <th id="colBestLastA">Best</th>
            <th>Laps</th>
            <th>Status</th>
            <th>Gap</th>
            <th>Int</th>
                        <th id="colBestLastB">Last</th>
          </tr>
        </thead>
        <tbody id="rows"></tbody>
      </table>
    </div>
  </main>

<script>
const host = window.location.host;
const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
const httpProto = window.location.protocol;

const apiBase = `${{httpProto}}//${{host}}`;
const wsBase  = `${{protocol}}://${{host}}`;

const elRows = document.getElementById("rows");
const elTimer = document.getElementById("timer");
const elMeta = document.getElementById("sessionMeta");
const elBestLastA = document.getElementById("colBestLastA");
const elBestLastB = document.getElementById("colBestLastB");

const state = {{ rows: new Map(), isRace: false }};

function detectIsRace(session) {{
    if (!session || typeof session !== 'object') return false;

    const direct = session.is_race ?? session.isRace ?? session.race;
    if (typeof direct === 'boolean') return direct;
    if (typeof direct === 'number') return direct !== 0;
    if (typeof direct === 'string') {{
        const v = direct.trim().toLowerCase();
        if (['1', 'true', 'yes', 'on', 'race', 'gara'].includes(v)) return true;
        if (['0', 'false', 'no', 'off', 'practice', 'qualifying', 'qualifica'].includes(v)) return false;
    }}

    const st = String(session.sessionType ?? '').toLowerCase();
    return st.includes('race') || st.includes('gara');
}}

function syncBestLastHeaders() {{
    if (!elBestLastA || !elBestLastB) return;
    if (state.isRace) {{
        elBestLastA.textContent = 'Last';
        elBestLastB.textContent = 'Best';
    }} else {{
        elBestLastA.textContent = 'Best';
        elBestLastB.textContent = 'Last';
    }}
}}

function render(drivers) {{
  if (!Array.isArray(drivers)) return;

  drivers.sort((a,b) => (a.position || 999) - (b.position || 999));

  elRows.innerHTML = drivers.map(d => `
    <tr class="row" data-key="${{d.number ?? d.driverId ?? d.raceNumber ?? ''}}">
      <td>${{d.position ?? ''}}</td>
      <td>${{d.name ?? ''}}</td>
      <td>${{d.team ?? ''}}</td>
      <td>${{d.sector1 ?? ''}}</td>
      <td>${{d.sector2 ?? ''}}</td>
      <td>${{d.sector3 ?? ''}}</td>
            <td>${{state.isRace ? (d.lastLap ?? '') : (d.fastLap ?? '')}}</td>
      <td>${{d.laps ?? ''}}</td>
      <td><span class="badge">${{d.status ?? ''}}</span></td>
      <td>${{d.gap ?? ''}}</td>
      <td>${{d.interval ?? ''}}</td>
            <td>${{state.isRace ? (d.fastLap ?? '') : (d.lastLap ?? '')}}</td>
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
    if (elTimer) elTimer.textContent = data.sessionTime || '--:--:--';

    state.isRace = detectIsRace(data);
    syncBestLastHeaders();

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

        self._server_data = uvicorn.Server(
            uvicorn.Config(self.app_data, host=self.address, port=self.port, log_level="warning")
        )

        # log reachable URL for data/web endpoints (single port)
        try:
            log(f"[LiveTiming] DATA+WEB server listening at http://{self.address}:{self.port}")
        except Exception:
            pass

        self.enabled = True
        self._server_task = asyncio.create_task(self._server_data.serve())
        self._start_public_tunnel()

    async def _stop_async(self) -> None:
        if self._server_data:
            self._server_data.should_exit = True
            task = self._server_task
            if task and not task.done():
                try:
                    await asyncio.wait_for(task, timeout=5.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass
        self._stop_public_tunnel()

    def _start_public_tunnel(self) -> None:
        if not self.public_enabled:
            return

        if self._ngrok_proc and self._ngrok_proc.poll() is None:
            return

        # Use ngrok start --all to consolidate multiple tunnels in a single agent session.
        # This avoids hitting the 3 simultaneous sessions limit on free tier.
        # Tunnels are defined in ngrok.yml (located in ~/.ngrok2/ngrok.yml)
        # (See: https://ngrok.com/docs/agent/config/)
        cmd = [
            "ngrok",
            "start",
            "--all",
        ]

        env = os.environ.copy()
        if PUBLIC_TUNNEL_AUTHTOKEN:
            env["NGROK_AUTHTOKEN"] = PUBLIC_TUNNEL_AUTHTOKEN

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        try:
            self._ngrok_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                creationflags=creationflags,
            )
            log(f"[LiveTiming] ngrok agent started (configuration: ~/.ngrok2/ngrok.yml)")
            log(f"[LiveTiming] Public URL: https://{PUBLIC_TUNNEL_DOMAIN}")

            self._ngrok_log_thread = threading.Thread(
                target=self._consume_ngrok_logs,
                name="LiveTimingNgrokLogThread",
                daemon=True,
            )
            self._ngrok_log_thread.start()
        except FileNotFoundError:
            log("[LiveTiming] ngrok not found. Install ngrok or disable public_enabled.")
        except Exception as ex:
            log(f"[LiveTiming] Failed to start ngrok: {ex}")

    def _stop_public_tunnel(self) -> None:
        proc = self._ngrok_proc
        self._ngrok_proc = None

        if not proc:
            return

        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

        try:
            log("[LiveTiming] ngrok stopped")
        except Exception:
            pass

    def _consume_ngrok_logs(self) -> None:
        proc = self._ngrok_proc
        if not proc or not proc.stdout:
            return

        try:
            for raw in proc.stdout:
                line = raw.strip()
                if line:
                    log(f"[LiveTiming][ngrok] {line}")
        except Exception:
            pass

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
