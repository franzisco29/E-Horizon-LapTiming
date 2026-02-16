import asyncio
import json

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# =========================
# HUB STATE
# =========================

class LiveTimingHub:
    def __init__(self):
        self.clients = set()
        self.session_data = None
        self.pilots_data = None

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients.add(ws)

        # manda snapshot subito
        await ws.send_text(json.dumps({
            "type": "snapshot",
            "session": self.session_data,
            "pilots": self.pilots_data
        }))

    def disconnect(self, ws: WebSocket):
        self.clients.discard(ws)

    async def broadcast(self, payload: dict):
        dead = []
        for ws in self.clients:
            try:
                await ws.send_text(json.dumps(payload))
            except:
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)

    async def publish_session(self, data):
        self.session_data = data
        await self.broadcast({"type": "session", "data": data})

    async def publish_pilots(self, data):
        self.pilots_data = data
        await self.broadcast({"type": "pilots", "data": data})


# =========================
# APP FASTAPI
# =========================

hub = LiveTimingHub()
app = FastAPI(title="E-Horizon Live Timing Server")


@app.get("/api/snapshot")
async def snapshot():
    return {
        "session": hub.session_data,
        "pilots": hub.pilots_data
    }


@app.websocket("/ws/timing")
async def websocket_endpoint(ws: WebSocket):
    await hub.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        hub.disconnect(ws)


# =========================
# TEST AUTO UPDATE (per test rapido)
# =========================

async def fake_update_loop():
    """
    Simula aggiornamenti automatici ogni 2 secondi
    Così puoi testare subito dal sito
    """
    import random
    import datetime

    while True:
        await asyncio.sleep(2)

        # SESSION
        await hub.publish_session({
            "status": "Racing",
            "time": datetime.datetime.now().strftime("%H:%M:%S")
        })

        # PILOTS
        pilots = [
            {
                "position": 1,
                "name": "Driver A",
                "team": "PFI Racing",
                "lastLap": f"00:{random.randint(10,20)}.{random.randint(100,999)}",
                "laps": random.randint(5,20)
            },
            {
                "position": 2,
                "name": "Driver B",
                "team": "SCUDERIA FPP",
                "lastLap": f"00:{random.randint(10,20)}.{random.randint(100,999)}",
                "laps": random.randint(5,20)
            }
        ]

        await hub.publish_pilots(pilots)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(fake_update_loop())


# =========================
# AVVIO SERVER
# =========================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
