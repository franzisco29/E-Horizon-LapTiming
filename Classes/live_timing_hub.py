from __future__ import annotations

import asyncio
import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import uvicorn


# =========================
# COLOR MAP (Qt Colors)
# =========================
COLOR_MAP = {
    "passed": "#E6C202",
    "pole":   "#9966CC",
    "end":    "#545454",
    "swap":   "#1E90FF",
    "pitin":  "#FF8C00",
    "pitout": "#00C853",
}


@dataclass
class LiveTimingManager:

    address: str
    port: int
    root_path: Optional[str] = None

    enabled: bool = False

    _clients: Set[WebSocket] = field(default_factory=set)
    _event_clients: Set[WebSocket] = field(default_factory=set)

    _session_data: Optional[Dict[str, Any]] = None
    _drivers_data: Optional[List[Dict[str, Any]]] = None

    app_data: Optional[FastAPI] = None
    app_web: Optional[FastAPI] = None

    _server_data: Optional[uvicorn.Server] = None
    _server_web: Optional[uvicorn.Server] = None

    _thread: Optional[threading.Thread] = None
    _loop: Optional[asyncio.AbstractEventLoop] = None
    _ready_evt: threading.Event = field(default_factory=threading.Event)

    # =====================================================
    # START / STOP
    # =====================================================

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._ready_evt.clear()

        def _runner():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop

            try:
                loop.run_until_complete(self._start_async())
                self._ready_evt.set()
                loop.run_forever()
            finally:
                loop.close()

        self._thread = threading.Thread(
            target=_runner,
            name="LiveTimingServerThread",
            daemon=True
        )
        self._thread.start()
        self._ready_evt.wait(timeout=3)

    def stop(self) -> None:
        if not self._loop:
            return

        asyncio.run_coroutine_threadsafe(
            self._stop_async(),
            self._loop
        )

        self._loop.call_soon_threadsafe(self._loop.stop)
        self.enabled = False
        self._loop = None

    # =====================================================
    # FASTAPI APPS
    # =====================================================

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
        async def snapshot():
            return {
                "session": self._session_data,
                "drivers": self._drivers_data
            }

        @app.websocket("/ws/timing")
        async def ws_timing(ws: WebSocket):
            await ws.accept()
            self._clients.add(ws)

            await ws.send_text(json.dumps({
                "type": "snapshot",
                "data": {
                    "session": self._session_data,
                    "drivers": self._drivers_data
                }
            }))

            try:
                while True:
                    await ws.receive_text()
            except WebSocketDisconnect:
                self._clients.discard(ws)

        @app.websocket("/ws/event")
        async def ws_event(ws: WebSocket):
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
        async def index():
            return HTMLResponse(self._html_page())

        @app.get("/assets/logo.webp")
        async def logo():
            if not self.root_path:
                return JSONResponse(status_code=404, content={})
            p = Path(self.root_path) / "Resources" / "e-horizon logo.webp"
            if p.exists():
                return FileResponse(str(p), media_type="image/webp")
            return JSONResponse(status_code=404, content={})

        return app

    # =====================================================
    # HTML PAGE
    # =====================================================

    def _html_page(self) -> str:
        return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<title>E-Horizon LiveTiming</title>

<style>
body {{
    background:#070a0f;
    color:white;
    font-family:system-ui;
}}

table {{
    width:100%;
    border-collapse:collapse;
}}

th, td {{
    padding:10px;
    border-bottom:1px solid rgba(255,255,255,.1);
}}

.row {{
    transition: background-color 0.3s ease;
}}

.flash-passed  {{ background-color:#E6C202 !important; }}
.flash-pole    {{ background-color:#9966CC !important; }}
.flash-end     {{ background-color:#545454 !important; }}
.flash-swap    {{ background-color:#1E90FF !important; }}
.flash-pitin   {{ background-color:#FF8C00 !important; }}
.flash-pitout  {{ background-color:#00C853 !important; }}

</style>
</head>
<body>

<h2>E-Horizon LiveTiming</h2>
<div id="sessionMeta"></div>
<h1 id="timer">--:--:--</h1>

<table>
<thead>
<tr>
<th>#</th>
<th>Driver</th>
<th>Team</th>
<th>Last</th>
<th>Gap</th>
<th>Int</th>
</tr>
</thead>
<tbody id="rows"></tbody>
</table>

<script>
const DATA_PORT = {self.port};
const host = window.location.hostname || 'localhost';
const apiBase = `http://${{host}}:${{DATA_PORT}}`;
const wsBase  = `ws://${{host}}:${{DATA_PORT}}`;

const elRows = document.getElementById("rows");
const elTimer = document.getElementById("timer");
const elMeta = document.getElementById("sessionMeta");

const state = {{ rows:new Map() }};

function render(drivers){{
    if(!drivers) return;

    drivers.sort((a,b)=>a.position-b.position);

    const html = drivers.map(d=>`
    <tr class="row" data-key="${{d.number}}">
        <td>${{d.position}}</td>
        <td>${{d.name}}</td>
        <td>${{d.team}}</td>
        <td>${{d.lastLap}}</td>
        <td>${{d.gap}}</td>
        <td>${{d.interval}}</td>
    </tr>
    `).join("");

    elRows.innerHTML = html;

    state.rows.clear();
    elRows.querySelectorAll("tr").forEach(tr=>{
        state.rows.set(tr.dataset.key, tr);
    });
}}

function flash(key, kind){{
    const row = state.rows.get(String(key));
    if(!row) return;

    const cls = "flash-" + kind.toLowerCase();
    row.classList.add(cls);
    setTimeout(()=>row.classList.remove(cls), 800);
}}

async function boot(){{
    const res = await fetch(`${{apiBase}}/api/snapshot`);
    const snap = await res.json();

    if(snap.session){{
        elTimer.textContent = snap.session.sessionTime;
        elMeta.textContent = snap.session.sessionType + " - " + snap.session.sessionStatus;
    }}

    render(snap.drivers || []);

    const ws = new WebSocket(`${{wsBase}}/ws/timing`);
    ws.onmessage = e=>{
        const msg = JSON.parse(e.data);
        if(msg.type==="snapshot")
            render(msg.data.drivers);
        if(msg.type==="drivers")
            render(msg.data);
    };

    const we = new WebSocket(`${{wsBase}}/ws/event`);
    we.onmessage = e=>{
        const msg = JSON.parse(e.data);
        if(msg.type==="event")
            flash(msg.data.key, msg.data.kind);
    };
}}

boot();
</script>

</body>
</html>
"""

    # =====================================================
    # ASYNC INTERNAL
    # =====================================================

    async def _start_async(self):
        self.app_data = self.build_app_data()
        self.app_web = self.build_app_web()

        self._server_data = uvicorn.Server(
            uvicorn.Config(self.app_data, host=self.address, port=self.port, log_level="warning")
        )

        self._server_web = uvicorn.Server(
            uvicorn.Config(self.app_web, host=self.address, port=self.port + 1, log_level="warning")
        )

        self.enabled = True

        asyncio.create_task(self._server_data.serve())
        asyncio.create_task(self._server_web.serve())

    async def _stop_async(self):
        if self._server_data:
            self._server_data.should_exit = True
        if self._server_web:
            self._server_web.should_exit = True

    # =====================================================
    # API PER QT
    # =====================================================

    def send_session_info(self, data: Dict[str, Any]) -> None:
        self._session_data = data

        asyncio.run_coroutine_threadsafe(
            self._broadcast({
                "type": "session",
                "data": data
            }),
            self._loop
        )

    def send_race_data(self, drivers: List[Dict[str, Any]]) -> None:
        self._drivers_data = drivers

        asyncio.run_coroutine_threadsafe(
            self._broadcast({
                "type": "drivers",
                "data": drivers
            }),
            self._loop
        )

    def send_event(self, key: int, kind: str) -> None:
        payload = {
            "type": "event",
            "data": {
                "key": key,
                "kind": kind
            }
        }

        asyncio.run_coroutine_threadsafe(
            self._broadcast_event(payload),
            self._loop
        )

    async def _broadcast(self, payload):
        msg = json.dumps(payload)
        for ws in list(self._clients):
            try:
                await ws.send_text(msg)
            except:
                self._clients.discard(ws)

    async def _broadcast_event(self, payload):
        msg = json.dumps(payload)
        for ws in list(self._event_clients):
            try:
                await ws.send_text(msg)
            except:
                self._event_clients.discard(ws)