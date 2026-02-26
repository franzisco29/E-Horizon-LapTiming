from __future__ import annotations

import asyncio
import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import uvicorn


# --- CSS color palette (your Qt colors) ---
COLOR_MAP = {
    "passed": "#E6C202",   # PASSED_COLOR
    "pole":   "#9966CC",   # POLE_COLOR
    "end":    "#545454",   # END_COLOR
    "swap":   "#1E90FF",   # SWAP_COLOR
    "pitin":  "#FF8C00",   # PIT_IN_COLOR
    "pitout": "#00C853",   # PIT_OUT_COLOR
}


@dataclass
class LiveTimingManager:
    """
    DATA server (port):
      - GET /api/snapshot
      - WS  /ws/timing
      - GET /api/tv
      - WS  /ws/tv
      - WS  /ws/event   (NEW: pass/pit/swap highlight + reorder anim)

    WEB server (port+1):
      - GET /          (HTML)
      - GET /assets/logo.webp (served from settings.root_path/Resources)
    """

    address: str
    port: int
    root_path: Optional[str] = None  # <-- NEW (settings.root_path)

    enabled: bool = False

    _clients: Set[WebSocket] = field(default_factory=set)
    _tv_clients: Set[WebSocket] = field(default_factory=set)
    _event_clients: Set[WebSocket] = field(default_factory=set)

    _session_data: Optional[Dict[str, Any]] = None
    _pilots_data: Optional[List[Dict[str, Any]]] = None

    _tv_session_data: Optional[Dict[str, Any]] = None
    _tv_pilots_data: Optional[List[Dict[str, Any]]] = None

    app_data: Optional[FastAPI] = None
    app_web: Optional[FastAPI] = None

    _server_data: Optional[uvicorn.Server] = None
    _server_web: Optional[uvicorn.Server] = None

    _thread: Optional[threading.Thread] = None
    _loop: Optional[asyncio.AbstractEventLoop] = None
    _ready_evt: threading.Event = field(default_factory=threading.Event)

    # =======================
    # Public lifecycle (Qt-safe)
    # =======================
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._ready_evt.clear()

        def _runner() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            try:
                loop.run_until_complete(self._start_server_async())
                self._ready_evt.set()
                loop.run_forever()
            finally:
                try:
                    pending = asyncio.all_tasks(loop)
                    for t in pending:
                        t.cancel()
                    loop.run_until_complete(asyncio.sleep(0))
                except Exception:
                    pass
                try:
                    loop.close()
                except Exception:
                    pass

        self._thread = threading.Thread(target=_runner, name="LiveTimingServerThread", daemon=True)
        self._thread.start()
        self._ready_evt.wait(timeout=3.0)

    def stop(self) -> None:
        if not self._loop:
            return
        try:
            fut = asyncio.run_coroutine_threadsafe(self._stop_server_async(), self._loop)
            fut.result(timeout=3.0)
        except Exception:
            pass

        try:
            self._loop.call_soon_threadsafe(self._loop.stop)
        except Exception:
            pass

        self._loop = None
        self.enabled = False

    # =======================
    # FastAPI apps
    # =======================
    def build_app_data(self) -> FastAPI:
        app = FastAPI(title="E-Horizon LiveTiming Data")

        @app.get("/api/snapshot")
        async def snapshot():
            return JSONResponse({"session": self._session_data, "drivers": self._pilots_data})

        @app.get("/api/tv")
        async def tv_snapshot():
            return JSONResponse({"session": self._tv_session_data, "drivers": self._tv_pilots_data})

        @app.websocket("/ws/timing")
        async def ws_timing(ws: WebSocket):
            await self._on_connect(ws)
            try:
                while True:
                    await ws.receive_text()
            except WebSocketDisconnect:
                self._on_disconnect(ws)
            except Exception:
                self._on_disconnect(ws)

        @app.websocket("/ws/tv")
        async def ws_tv(ws: WebSocket):
            await self._on_connect_tv(ws)
            try:
                while True:
                    await ws.receive_text()
            except WebSocketDisconnect:
                self._on_disconnect_tv(ws)
            except Exception:
                self._on_disconnect_tv(ws)

        @app.websocket("/ws/event")
        async def ws_event(ws: WebSocket):
            await self._on_connect_event(ws)
            try:
                while True:
                    await ws.receive_text()
            except WebSocketDisconnect:
                self._on_disconnect_event(ws)
            except Exception:
                self._on_disconnect_event(ws)

        @app.get("/favicon.ico")
        async def favicon():
            return JSONResponse(status_code=204, content=None)

        return app

    def build_app_web(self) -> FastAPI:
        app = FastAPI(title="E-Horizon LiveTiming Web")

        @app.get("/")
        async def index():
            try:
                html = self._html_page()
                return HTMLResponse(content=html)
            except Exception as e:
                # fallback: evita il “Content-Length mismatch”
                return HTMLResponse(content=f"<pre>LiveTiming HTML error: {e!r}</pre>", status_code=500)

        @app.get("/assets/logo.webp")
        async def logo():
            p = self._logo_path()
            if p and p.exists():
                return FileResponse(str(p), media_type="image/webp")
            return JSONResponse(status_code=404, content={"detail": "Logo not found"})

        @app.get("/favicon.ico")
        async def favicon():
            return JSONResponse(status_code=204, content=None)

        return app

    def _logo_path(self) -> Optional[Path]:
        if not self.root_path:
            return None
        # root_path/Resources/e-horizon logo.webp
        return Path(self.root_path) / "Resources" / "e-horizon logo.webp"

    # =======================
    # HTML page (port+1)
    # =======================

    def _html_page(self) -> str:
        html = """<!doctype html>
    <html lang="en">
    <head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width,initial-scale=1"/>
    <title>E-Horizon LiveTiming</title>

    <style>
    :root {
    --bg:#070a0f;
    --line:rgba(255,255,255,.15);
    --line2:rgba(255,255,255,.08);
    --txt:rgba(255,255,255,.96);
    --muted:rgba(255,255,255,.75);
    --acc:#3ad6ff;
    }

    *{box-sizing:border-box;font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;}
    body{
    margin:0;
    background:
        radial-gradient(1200px 600px at 20% 0%, rgba(58,214,255,.14), transparent 55%),
        radial-gradient(900px 420px at 85% 25%, rgba(58,214,255,.08), transparent 60%),
        var(--bg);
    color:var(--txt);
    }

    header{
    padding:16px 22px;
    display:flex;
    align-items:center;
    justify-content:space-between;
    }

    .left {
    display:flex;
    align-items:center;
    gap:18px;
    }

    .logo {
    width:60px;
    height:60px;
    border-radius:14px;
    background:rgba(255,255,255,.06);
    display:flex;
    align-items:center;
    justify-content:center;
    overflow:hidden;
    }
    .logo img { width:100%; height:100%; object-fit:contain; }

    .title { font-size:22px; font-weight:900; }
    .meta  { font-size:18px; color:var(--muted); }

    .timer {
    font-size:40px;
    font-weight:900;
    font-variant-numeric: tabular-nums;
    letter-spacing:1px;
    }

    .pill {
    border:1px solid rgba(58,214,255,.35);
    background:rgba(58,214,255,.08);
    padding:10px 18px;
    border-radius:999px;
    font-size:18px;
    }

    main{padding:0 20px 20px;}

    .card{
    border:1px solid var(--line);
    border-radius:16px;
    overflow:hidden;
    }

    .table-wrap{
    overflow:auto;
    max-height:calc(100vh - 160px);
    }

    table{
    width:100%;
    min-width:1400px;
    border-collapse:separate;
    border-spacing:0;
    font-size:20px;   /* FONT 20PX */
    table-layout:fixed;
    }

    thead th{
    position:sticky;
    top:0;
    z-index:5;
    padding:16px 12px;
    background:rgba(0,0,0,.65);
    border-bottom:1px solid var(--line);
    text-align:left;
    font-weight:900;
    }

    tbody td{
    padding:16px 12px;
    border-bottom:1px solid var(--line2);
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
    }

    tbody tr:nth-child(odd){background:rgba(255,255,255,.03);}
    tbody tr:nth-child(even){background:rgba(0,0,0,.12);}

    .right{text-align:right;}
    .pos{font-weight:900;}
    .muted{color:var(--muted);}

    /* ===== VB WIDTHS =====
    _vb_col_widths = [50,200,200,100,100,100,125,50,100,100,100,150,125]
    */
    th.col-pos,    td.col-pos    { width:50px; }
    th.col-name,   td.col-name   { width:200px; }
    th.col-team,   td.col-team   { width:200px; }
    th.col-s,      td.col-s      { width:100px; }
    th.col-last,   td.col-last   { width:125px; }
    th.col-laps,   td.col-laps   { width:50px; }
    th.col-status, td.col-status { width:100px; }
    th.col-gap,    td.col-gap    { width:100px; }
    th.col-int,    td.col-int    { width:100px; }
    th.col-best,   td.col-best   { width:150px; }
    th.col-total,  td.col-total  { width:125px; }

    /* Sticky first two columns */
    th.col-pos, td.col-pos {
    position:sticky;
    left:0;
    background:rgba(0,0,0,.65);
    z-index:6;
    }

    th.col-name, td.col-name {
    position:sticky;
    left:50px;
    background:rgba(0,0,0,.65);
    z-index:6;
    }
    </style>
    </head>

    <body>

    <header>
    <div class="left">
        <div class="logo">
        <img src="/assets/logo.webp" alt="logo"/>
        </div>
        <div>
        <div class="title">E-Horizon LiveTiming</div>
        <div class="meta" id="sessionMeta">Waiting for data…</div>
        </div>
    </div>

    <div style="display:flex; align-items:center; gap:18px;">
        <div class="timer" id="timer">--:--:--</div>
        <div class="pill" id="conn">Connecting…</div>
    </div>
    </header>

    <main>
    <div class="card">
        <div class="table-wrap">
        <table>
            <thead>
            <tr>
                <th class="col-pos">#</th>
                <th class="col-name">Driver</th>
                <th class="col-team">Team</th>
                <th class="col-s right">S1</th>
                <th class="col-s right">S2</th>
                <th class="col-s right">S3</th>
                <th class="col-last right">Last</th>
                <th class="col-laps right">Laps</th>
                <th class="col-status">Status</th>
                <th class="col-gap right">Gap</th>
                <th class="col-int right">Int</th>
                <th class="col-best right">Best</th>
                <th class="col-total right">Total</th>
            </tr>
            </thead>
            <tbody id="rows"></tbody>
        </table>
        </div>
    </div>
    </main>

    <script>
    const DATA_PORT = __DATA_PORT__;
    const host = window.location.hostname || 'localhost';
    const apiBase = `http://${host}:${DATA_PORT}`;
    const wsBase  = `ws://${host}:${DATA_PORT}`;

    const elRows  = document.getElementById('rows');
    const elTimer = document.getElementById('timer');
    const elMeta  = document.getElementById('sessionMeta');
    const elConn  = document.getElementById('conn');

    function updateSession(sess){
    if(!sess) return;

    elTimer.textContent = sess.sessionTime ?? '--:--:--';

    // pit può arrivare stringa (es "Open") o bool
    let pit = '';
    if (typeof sess.pitOpen === 'string') pit = sess.pitOpen;
    else if (typeof sess.pitOpen === 'boolean') pit = sess.pitOpen ? 'Open' : 'Closed';

    elMeta.textContent = `${sess.sessionType} • Status: ${sess.sessionStatus} • Pit Lane: ${pit}`;
    }

    function renderPilots(p){
    elRows.innerHTML = (p || []).map(d => `
        <tr>
        <td class="col-pos pos">${d.position ?? ''}</td>
        <td class="col-name">${d.name ?? ''}</td>
        <td class="col-team muted">${d.team ?? ''}</td>
        <td class="col-s right">${d.sector1 ?? ''}</td>
        <td class="col-s right">${d.sector2 ?? ''}</td>
        <td class="col-s right">${d.sector3 ?? ''}</td>
        <td class="col-last right">${d.lastLap ?? ''}</td>
        <td class="col-laps right">${d.laps ?? ''}</td>
        <td class="col-status">${d.status ?? ''}</td>
        <td class="col-gap right">${d.gap ?? ''}</td>
        <td class="col-int right">${d.interval ?? ''}</td>
        <td class="col-best right">${d.fastLap ?? ''}</td>
        <td class="col-total right">${d.timeOnTrack ?? ''}</td>
        </tr>
    `).join('');
    }

    async function boot(){
    try{
        const res = await fetch(`${apiBase}/api/snapshot`, { cache: 'no-store' });
        const snap = await res.json();
        updateSession(snap.session);
        renderPilots(snap.pilots || []);
    }catch(e){}

    const ws = new WebSocket(`${wsBase}/ws/timing`);
    ws.onopen  = () => elConn.textContent = "Connected";
    ws.onclose = () => elConn.textContent = "Disconnected";

    ws.onmessage = ev => {
        const msg = JSON.parse(ev.data);
        if(msg.type === "snapshot"){
        updateSession(msg.data.session);
        renderPilots(msg.data.pilots);
        }
        if(msg.type === "session") updateSession(msg.data);
        if(msg.type === "pilots")  renderPilots(msg.data);
    };
    }

    boot();
    </script>

    </body>
    </html>
    """
        return html.replace("__DATA_PORT__", str(self.port))

    # =======================
    # Async internal (server thread)
    # =======================
    async def _start_server_async(self) -> None:
        self.app_data = self.build_app_data()
        cfg_data = uvicorn.Config(
            self.app_data,
            host=self.address,
            port=self.port,
            log_level="warning",
            reload=False,
            loop="asyncio",
        )
        self._server_data = uvicorn.Server(cfg_data)

        self.app_web = self.build_app_web()
        cfg_web = uvicorn.Config(
            self.app_web,
            host=self.address,
            port=self.port + 1,
            log_level="warning",
            reload=False,
            loop="asyncio",
        )
        self._server_web = uvicorn.Server(cfg_web)

        self.enabled = True

        asyncio.create_task(self._server_data.serve())
        asyncio.create_task(self._server_web.serve())

        print(f"✅ LiveTiming DATA  http://{self.address}:{self.port}", flush=True)
        print(f"✅ LiveTiming WEB   http://{self.address}:{self.port + 1}", flush=True)

    async def _stop_server_async(self) -> None:
        if self._server_data is not None:
            self._server_data.should_exit = True
        if self._server_web is not None:
            self._server_web.should_exit = True
        self.enabled = False
        print("🛑 LiveTiming Server stopped.", flush=True)

    # =======================
    # WS connect/disconnect
    # =======================
    async def _on_connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)
        await self._safe_send(ws, {"type": "snapshot", "data": {"session": self._session_data, "pilots": self._pilots_data}})

    async def _on_connect_tv(self, ws: WebSocket) -> None:
        await ws.accept()
        self._tv_clients.add(ws)
        await self._safe_send(ws, {"type": "snapshot", "data": {"session": self._tv_session_data, "pilots": self._tv_pilots_data}})

    async def _on_connect_event(self, ws: WebSocket) -> None:
        await ws.accept()
        self._event_clients.add(ws)

    def _on_disconnect(self, ws: WebSocket) -> None:
        self._clients.discard(ws)

    def _on_disconnect_tv(self, ws: WebSocket) -> None:
        self._tv_clients.discard(ws)

    def _on_disconnect_event(self, ws: WebSocket) -> None:
        self._event_clients.discard(ws)

    async def _safe_send(self, ws: WebSocket, payload: Dict[str, Any]) -> bool:
        try:
            await ws.send_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
            return True
        except Exception:
            return False

    async def _broadcast_async(self, payload: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        dead: List[WebSocket] = []
        msg = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        for ws in list(self._clients):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._on_disconnect(ws)

    async def _broadcast_tv_async(self, payload: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        dead: List[WebSocket] = []
        msg = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        for ws in list(self._tv_clients):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._on_disconnect_tv(ws)

    async def _broadcast_event_async(self, payload: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        dead: List[WebSocket] = []
        msg = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        for ws in list(self._event_clients):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._on_disconnect_event(ws)

    # =======================
    # Thread-safe API for Qt GUI
    # =======================
    def send_session_info(self, race_man: Any) -> None:
        if not self.enabled or not self._loop:
            return

        if hasattr(race_man, "session_to_live_dict"):
            data = race_man.session_to_live_dict()
        else:
            data = json.loads(race_man.session_to_live())

        self._session_data = data
        self._tv_session_data = data

        asyncio.run_coroutine_threadsafe(self._broadcast_async({"type": "session", "data": data}), self._loop)
        asyncio.run_coroutine_threadsafe(self._broadcast_tv_async({"type": "session", "data": data}), self._loop)

    def send_race_data(self, drivers: List[Any]) -> None:
        if not self.enabled or not self._loop:
            return

        pilots: List[Dict[str, Any]] = []
        for d in drivers:
            if hasattr(d, "to_live_dict"):
                pilots.append(d.to_live_dict())
            else:
                pilots.append(json.loads(d.to_live()))

        self._pilots_data = pilots
        self._tv_pilots_data = pilots

        asyncio.run_coroutine_threadsafe(self._broadcast_async({"type": "pilots", "data": pilots}), self._loop)
        asyncio.run_coroutine_threadsafe(self._broadcast_tv_async({"type": "pilots", "data": pilots}), self._loop)

    def send_event(self, key: int | str, kind: str) -> None:
        """
        key: driver number (preferred) or driverId
        kind: passed|pole|swap|pitin|pitout|end
        """
        if not self.enabled or not self._loop:
            return
        kind = (kind or "passed").lower()
        if kind not in ("passed", "pole", "swap", "pitin", "pitout", "end"):
            kind = "passed"

        payload = {"type": "event", "data": {"key": str(key), "kind": kind}}
        asyncio.run_coroutine_threadsafe(self._broadcast_event_async(payload), self._loop)