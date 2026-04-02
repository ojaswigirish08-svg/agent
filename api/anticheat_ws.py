import json
from fastapi import WebSocket, WebSocketDisconnect
from orchestrator.orchestrator import Orchestrator

orchestrator_ref: Orchestrator = None


def init_anticheat_ws(orch: Orchestrator):
    global orchestrator_ref
    orchestrator_ref = orch


async def anticheat_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()

    state = orchestrator_ref.get_session(session_id)
    if not state:
        await websocket.close()
        return

    try:
        while True:
            raw = await websocket.receive_text()
            message = json.loads(raw)

            signal_type = message.get("type", "")
            signal_data = {
                "destination": message.get("destination", ""),
                "text_length": message.get("text_length", 0),
                "duration_ms": message.get("duration_ms", 0),
                "context": message.get("context", {})
            }

            if signal_type in [
                "tab_switch", "window_blur",
                "paste", "screen_share"
            ]:
                orchestrator_ref.process_anticheat_signal(
                    signal_type=signal_type,
                    signal_data=signal_data,
                    state=state
                )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        import traceback
        traceback.print_exc()