from __future__ import annotations

import asyncio
import json
import os
import threading
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime, time as dt_time, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Set

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

import ngrok

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

# Public tunnel settings.
PUBLIC_TUNNEL_DOMAIN = "alphonso-supersacerdotal-tomboyishly.ngrok-free.dev"
PUBLIC_TUNNEL_AUTHTOKEN = "3AqYa5ynYWEYmf0T5uQ7mKDO2AN_2bBmFGAcFEkaMfGF7sBRj"


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
    _ngrok_listener: Optional[Any] = None

    on_public_online: Optional[Callable[[], None]] = None  # callback per segnalare online

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
            future.result(timeout=10)
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

        import os
        from fastapi.staticfiles import StaticFiles
        static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Resources", "web_templates")
        app.mount("/web_templates", StaticFiles(directory=static_dir), name="web_templates")

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
            candidates.append(get_app_base_dir() / "Resources" / "icons" / "favicon.ico")
            p = next((path for path in candidates if path.exists()), None)
            if p is not None:
                return FileResponse(str(p), media_type="image/x-icon")
            return JSONResponse(status_code=404, content={})

        @app.get("/assets/sponsors", response_model=None)
        async def sponsors() -> Any:
            sponsors_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Resources", "Sponsors")
            try:
                files = [f for f in os.listdir(sponsors_dir) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".svg"))]
            except Exception:
                files = []
            urls = [f"/assets/sponsorfile/{fname}" for fname in files]
            from fastapi import Response
            return Response(
                content=json.dumps(urls),
                media_type="application/json",
                headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}
            )

        @app.get("/assets/sponsorfile/{filename}", response_model=None)
        async def sponsorfile(filename: str) -> Any:
            sponsors_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Resources", "Sponsors")
            path = os.path.join(sponsors_dir, filename)
            from fastapi import Response
            if os.path.exists(path):
                ext = os.path.splitext(filename)[1].lower()
                if ext == ".png":
                    media_type = "image/png"
                elif ext in (".jpg", ".jpeg"):
                    media_type = "image/jpeg"
                elif ext == ".webp":
                    media_type = "image/webp"
                elif ext == ".svg":
                    media_type = "image/svg+xml"
                else:
                    media_type = "application/octet-stream"
                return FileResponse(path, media_type=media_type, headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"})
            return JSONResponse(status_code=404, content={})

        @app.get("/assets/logo", response_model=None)
        async def logo() -> Any:
            candidates: List[Path] = []
            if self.root_path:
                candidates.append(Path(self.root_path) / "Resources" / "logos" / "e-horizon logo quadrato_trs.png")
                candidates.append(Path(self.root_path) / "Resources" / "logos" / "e-horizon logo.webp")
            candidates.append(get_app_base_dir() / "Resources" / "logos" / "e-horizon logo quadrato_trs.png")
            candidates.append(get_app_base_dir() / "Resources" / "logos" / "e-horizon logo.webp")
            p = next((path for path in candidates if path.exists()), None)
            if p is not None:
                media_type = "image/png" if p.suffix.lower() == ".png" else "image/webp"
                return FileResponse(str(p), media_type=media_type, headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"})
            return JSONResponse(status_code=404, content={})

        @app.websocket("/ws/timing")
        async def ws_timing(ws: WebSocket) -> None:
            await ws.accept()
            self._clients.add(ws)
            await ws.send_text(
                json.dumps({
                    "type": "snapshot",
                    "data": {
                        "session": self._session_data,
                        "drivers": self._drivers_data,
                    },
                })
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
        import os
        template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Resources", "web_templates", "liverace.html")
        with open(template_path, encoding="utf-8") as f:
            html = f.read()
        event_css = "\n".join([
            f".flash-{k} {{ background-color:{v} !important;{' color:#101010;' if k in ['passed','pitout'] else ''} }}"
            for k, v in EVENT_COLOR_MAP.items()
        ])
        html = html.replace("/* Gli stili flash-* saranno gestiti dinamicamente in Python */", event_css)
        return html

    async def _start_async(self) -> None:
        self.app_data = self.build_app_data()
        self._server_data = uvicorn.Server(
            uvicorn.Config(self.app_data, host=self.address, port=self.port, log_level="warning")
        )
        try:
            log(f"[LIVE] Server avviato su http://{self.address}:{self.port}")
        except Exception:
            pass
        self.enabled = True
        self._server_task = asyncio.create_task(self._server_data.serve())
        self._start_public_tunnel()

    async def _stop_async(self) -> None:
        # Disconnetti ngrok prima di fermare uvicorn: evita errori
        # "error connecting to upstream" causati da richieste in arrivo
        # mentre il server locale è già spento.
        self._stop_public_tunnel()

        if self._server_data:
            self._server_data.should_exit = True
            task = self._server_task
            if task and not task.done():
                try:
                    await asyncio.wait_for(task, timeout=5.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass

    # ------------------------------------------------------------------
    # ngrok tunnel management — Python SDK
    # ------------------------------------------------------------------

    def _start_public_tunnel(self) -> None:
        if not self.public_enabled:
            return

        if self._ngrok_listener is not None:
            return

        def ngrok_thread() -> None:
            try:
                listener = ngrok.forward(
                    f"localhost:{self.port}",
                    authtoken=PUBLIC_TUNNEL_AUTHTOKEN,
                    domain=PUBLIC_TUNNEL_DOMAIN,
                )
                self._ngrok_listener = listener
                log(f"[LIVE] Tunnel ngrok attivo → {listener.url()}")
                if self.on_public_online:
                    try:
                        self.on_public_online()
                    finally:
                        self.on_public_online = None
            except Exception as ex:
                log(f"[LIVE] Errore avvio tunnel ngrok: {ex}", level="ERROR")

        threading.Thread(target=ngrok_thread, name="NgrokStartThread", daemon=True).start()

    def _stop_public_tunnel(self) -> None:
        listener = self._ngrok_listener
        self._ngrok_listener = None
        if listener is None:
            return
        url = None
        try:
            url = listener.url()
        except Exception:
            pass
        try:
            # disconnect() è sincrono; listener.close() è Awaitable e richiederebbe await.
            # kill() termina completamente la sessione agent (evita retry interni del SDK).
            ngrok.disconnect(url)
            ngrok.kill()
            log("[LIVE] Tunnel ngrok chiuso")
        except Exception as ex:
            log(f"[LIVE] Errore chiusura tunnel ngrok: {ex}", level="WARN")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_session_info(self, data: Any) -> None:
        self._session_data = self._normalize_session_data(data)
        self._run_in_loop(self._broadcast({"type": "session", "data": self._session_data}))

    def send_race_data(self, drivers: Iterable[Any]) -> None:
        self._drivers_data = self._normalize_drivers_data(drivers)
        self._run_in_loop(self._broadcast({"type": "drivers", "data": self._drivers_data}))

    def send_event(self, key: int, kind: str) -> None:
        payload = {"type": "event", "data": {"key": key, "kind": str(kind).lower()}}
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
        if isinstance(value, (date, dt_time)):
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