from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse


@dataclass
class LiveTimingState:
    session: Optional[Dict[str, Any]] = None
    pilots: Optional[List[Dict[str, Any]]] = None


@dataclass
class LiveTimingHub:
    """
    Hub centralizzato:
    - mantiene ultimo stato (snapshot)
    - gestisce client websocket con broadcast
    - può differenziare profili (TV / WEB)
    """
    state: LiveTimingState = field(default_factory=LiveTimingState)
    clients: Set[WebSocket] = field(default_factory=set)

    # frequenze consigliate
    web_min_interval_s: float = 0.25   # 4 Hz
    tv_min_interval_s: float = 0.05    # 20 Hz

    _last_web_push: float = 0.0
    _last_tv_push: float = 0.0

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.clients.add(ws)

        # manda snapshot subito (così la pagina web si popola instant)
        await self._safe_send(ws, {"type": "snapshot", "data": self.get_snapshot()})

    def disconnect(self, ws: WebSocket) -> None:
        self.clients.discard(ws)

    def get_snapshot(self) -> Dict[str, Any]:
        return {
            "session": self.state.session,
            "pilots": self.state.pilots,
        }

    async def publish_session(self, session_data: Dict[str, Any]) -> None:
        self.state.session = session_data
        await self.broadcast({"type": "session", "data": session_data})

    async def publish_pilots(self, pilots_data: List[Dict[str, Any]]) -> None:
        self.state.pilots = pilots_data
        await self.broadcast({"type": "pilots", "data": pilots_data})

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        # invio a tutti i client; se qualcuno cade lo rimuovo
        dead: List[WebSocket] = []
        for ws in list(self.clients):
            ok = await self._safe_send(ws, payload)
            if not ok:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def _safe_send(self, ws: WebSocket, payload: Dict[str, Any]) -> bool:
        try:
            await ws.send_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
            return True
        except Exception:
            return False


def create_app(hub: LiveTimingHub) -> FastAPI:
    app = FastAPI(title="E-Horizon LiveTiming Hub")

    @app.get("/api/snapshot")
    async def snapshot():
        return JSONResponse(hub.get_snapshot())

    @app.websocket("/ws/timing")
    async def ws_timing(ws: WebSocket):
        await hub.connect(ws)
        try:
            while True:
                # server only broadcaster: ignoriamo messaggi client
                await ws.receive_text()
        except WebSocketDisconnect:
            hub.disconnect(ws)
        except Exception:
            hub.disconnect(ws)

    return app
