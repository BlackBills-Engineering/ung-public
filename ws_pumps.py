# ws_pumps.py
import asyncio, logging
from datetime import datetime, timezone
from typing import Dict, Union, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from models import PumpStatus
from trash import get_frame


router = APIRouter()
TICK = 0.5

# Fix logger configuration
log = logging.getLogger("ws_pumps")
log.setLevel(logging.ERROR)

# кеши
meta: Dict[int, dict] = {}  # price_per_unit / grade
last_live: Dict[int, float] = {}  # последнее валидное LIVE-число
last_tx: Dict[int, dict] = {}  # финальный чек для IDLE


# ───────── price-fix ─────────
def fix_price(ppu: Union[int, float, None]) -> Union[int, float, None]:
    if ppu is None:
        return ppu
    p = int(round(ppu))
    # 4-значные цены Gilbarco возвращает как 5-значные (8150 → 81500)
    if p > 9999 and p % 10 == 0 and 1000 <= p // 10 <= 9999:
        return p // 10
    return p


# ───────── Hub ─────────
class Hub:
    def __init__(self):
        self.clients: list[WebSocket] = []

    async def connect(self, ws):
        await ws.accept()
        self.clients.append(ws)

    def disconnect(self, ws):
        self.clients[:] = [c for c in self.clients if c is not ws]

    async def broadcast(self, payload):
        msg = jsonable_encoder(payload)
        disconnected_clients = []
        
        for ws in self.clients.copy():
            try:
                await ws.send_json(msg)
            except (WebSocketDisconnect, ConnectionResetError, RuntimeError, Exception) as e:
                log.debug(f"WebSocket error during broadcast: {e}")
                disconnected_clients.append(ws)
        
        # Remove disconnected clients
        for ws in disconnected_clients:
            self.disconnect(ws)


hub = Hub()


# ───────── WebSocket ─────────
@router.websocket("/ws/pumps")
async def pumps_socket(ws: WebSocket):
    await hub.connect(ws)
    # pm = ws.app.state.pump_manager  # общий PumpManager

    try:
        while True:
            try:
                frame = {"ts": datetime.now(timezone.utc).isoformat(), "pumps": []}

                # Safely get pump statuses
                pump_statuses = {}
                try:
                    pump_statuses = {}
                except Exception as e:
                    log.error(f"Error getting pump statuses: {e}")
                    await asyncio.sleep(TICK)
                    continue

                for pid, st in pump_statuses.items():
                    try:
                        item = st.dict()

                        # 2️⃣ Если price/grade ещё не знаем — пробуем один раз взять чек (4p)
                        if pid not in meta:
                            try:
                                tx = {}
                                if tx and tx.price_per_unit:
                                    meta[pid] = {
                                        "price_per_unit": fix_price(tx.price_per_unit),
                                        "grade": tx.grade,
                                    }
                            except Exception as e:
                                log.debug("meta read pump %s: %s", pid, e)

                        # ───── DISPENSING ─────
                        if st.status == PumpStatus.DISPENSING:
                            # 1️⃣ Читаем live-число (деньги ИЛИ литры)
                            try:
                                live_val: Optional[float] = pm.get_realtime(pid)
                                if live_val is not None:
                                    last_live[pid] = live_val
                            except Exception as e:
                                log.debug(f"Error getting realtime for pump {pid}: {e}")

                            # Safe price calculation
                            price_per_unit = meta.get(pid, {}).get("price_per_unit")
                            price = (price_per_unit * 10) if price_per_unit else None
                            
                            rt = {
                                "price_per_unit": price,
                                "grade": meta.get(pid, {}).get("grade"),
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "total_amount": None,
                                "volume": None,
                            }

                            if price and price > 0 and pid in last_live:  # Safe division
                                rt["total_amount"] = round(last_live[pid], 2) * 1000
                                rt["volume"] = round(rt["total_amount"] / price, 3)
                            elif pid in last_live:  # пока не знаем цену → treat as volume
                                rt["volume"] = round(last_live[pid], 3)

                            item["realtime"] = rt

                            # новая продажа (live обнулился) → сбрасываем финальный чек
                            if pid in last_live and last_live[pid] == 0:
                                last_tx.pop(pid, None)

                        # ───── COMPLETE ─────
                        elif st.status == PumpStatus.COMPLETE or st.status == PumpStatus.IDLE:
                            try:
                                tx = {}
                                if tx:
                                    txd = tx.dict()
                                    txd["price_per_unit"] = fix_price(txd["price_per_unit"])
                                    item["transaction"] = txd
                                    last_tx[pid] = txd
                                    meta[pid] = {
                                        "price_per_unit": txd["price_per_unit"],
                                        "grade": txd["grade"],
                                    }
                            except Exception as e:
                                log.debug("complete read pump %s: %s", pid, e)

                        frame["pumps"].append(item)
                        
                    except Exception as e:
                        log.error(f"Error processing pump {pid}: {e}")
                        continue
                    
                # ----- FRONTEND TEST ONLY -----
                # await hub.broadcast(frame)
                await hub.broadcast(get_frame())
                
            except Exception as e:
                log.error(f"Error in WebSocket main loop: {e}")
                
            await asyncio.sleep(TICK)

    except WebSocketDisconnect:
        log.info("WebSocket client disconnected")
    except Exception as e:
        log.error(f"Unexpected error in WebSocket: {e}")
    finally:
        hub.disconnect(ws)
