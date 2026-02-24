from __future__ import annotations

import asyncio
import json
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import uvicorn


@dataclass
class LiveTimingManager:
    address: str
    port: int

    enabled: bool = False

    _clients: Set[WebSocket] = field(default_factory=set)
    _session_data: Optional[Dict[str, Any]] = None
    _pilots_data: Optional[List[Dict[str, Any]]] = None

    app: Optional[FastAPI] = None
    _server: Optional[uvicorn.Server] = None

    # --- NEW: thread + loop ---
    _thread: Optional[threading.Thread] = None
    _loop: Optional[asyncio.AbstractEventLoop] = None
    _ready_evt: threading.Event = field(default_factory=threading.Event)
    _stop_evt: threading.Event = field(default_factory=threading.Event)

    # =======================
    # FASTAPI APP
    # =======================
    def build_app(self) -> FastAPI:
        app = FastAPI(title="E-Horizon LiveTiming")

        @app.get("/api/snapshot")
        async def snapshot():
            return JSONResponse({"session": self._session_data, "pilots": self._pilots_data})

        @app.websocket("/ws/timing")
        async def ws_timing(ws: WebSocket):
            await self._on_connect(ws)
            try:
                while True:
                    # broadcaster only: se il client manda qualcosa lo ignoriamo
                    await ws.receive_text()
            except WebSocketDisconnect:
                self._on_disconnect(ws)
            except Exception:
                self._on_disconnect(ws)

        @app.get("/favicon.ico")
        async def favicon():
            return JSONResponse(status_code=204, content=None)

        return app

    # =======================
    # THREAD LIFECYCLE (SYNC)
    # =======================
    def start(self) -> None:
        """
        Avvia server in thread dedicato (Qt-safe).
        """
        if self._thread and self._thread.is_alive():
            return

        self._stop_evt.clear()
        self._ready_evt.clear()

        def _runner():
            # loop asyncio dedicato al thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop

            try:
                loop.run_until_complete(self._start_server_async())
                self._ready_evt.set()
                # resta vivo finché non chiedi stop
                loop.run_forever()
            finally:
                try:
                    pending = asyncio.all_tasks(loop)
                    for t in pending:
                        t.cancel()
                    loop.run_until_complete(asyncio.sleep(0))
                except Exception:
                    pass
                loop.close()

        self._thread = threading.Thread(target=_runner, name="LiveTimingServerThread", daemon=True)
        self._thread.start()

        # aspetta che il server sia pronto (breve)
        self._ready_evt.wait(timeout=3.0)

    def stop(self) -> None:
        """
        Ferma server e loop.
        """
        if not self._loop:
            return

        # spegne uvicorn
        fut = asyncio.run_coroutine_threadsafe(self._stop_server_async(), self._loop)
        try:
            fut.result(timeout=3.0)
        except Exception:
            pass

        # ferma loop
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._loop = None
        self.enabled = False

    # =======================
    # ASYNC INTERNALS (run in server thread)
    # =======================
    async def _start_server_async(self) -> None:
        self.app = self.build_app()
        config = uvicorn.Config(
            self.app,
            host=self.address,
            port=self.port,
            log_level="warning",
            reload=False,
            # importante: lascia asyncio, ma nel thread dedicato
            loop="asyncio",
        )
        self._server = uvicorn.Server(config)
        self.enabled = True

        # avvia serve() in background task e lascia il loop correre
        asyncio.create_task(self._server.serve())
        print(f"✅ LiveTiming Server avviato su http://{self.address}:{self.port}", flush=True)

    async def _stop_server_async(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        self.enabled = False
        print("🛑 LiveTiming Server arrestato.", flush=True)

    # =======================
    # CLIENTS / BROADCAST
    # =======================
    async def _on_connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)

        # snapshot immediato
        await self._safe_send(ws, {
            "type": "snapshot",
            "data": {"session": self._session_data, "pilots": self._pilots_data},
        })

    def _on_disconnect(self, ws: WebSocket) -> None:
        self._clients.discard(ws)

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

    # =======================
    # API "THREAD-SAFE" PER LA GUI (NO await)
    # =======================
    def send_session_info(self, race_man: Any) -> None:
        """
        Versione SYNC: schedula nel loop del server thread.
        """
        if not self.enabled or not self._loop:
            return

        if hasattr(race_man, "session_to_live_dict"):
            data = race_man.session_to_live_dict()
        else:
            data = json.loads(race_man.session_to_live())

        self._session_data = data
        asyncio.run_coroutine_threadsafe(
            self._broadcast_async({"type": "session", "data": data}),
            self._loop
        )

    def send_race_data(self, drivers: List[Any]) -> None:
        """
        Versione SYNC: schedula nel loop del server thread.
        """
        if not self.enabled or not self._loop:
            return

        pilots: List[Dict[str, Any]] = []
        for d in drivers:
            if hasattr(d, "to_live_dict"):
                pilots.append(d.to_live_dict())
            else:
                pilots.append(json.loads(d.to_live()))

        self._pilots_data = pilots
        asyncio.run_coroutine_threadsafe(
            self._broadcast_async({"type": "pilots", "data": pilots}),
            self._loop
        )