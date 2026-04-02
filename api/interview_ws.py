import json
import base64
from fastapi import WebSocket, WebSocketDisconnect
from orchestrator.orchestrator import Orchestrator

orchestrator_ref: Orchestrator = None


def init_ws(orch: Orchestrator):
    global orchestrator_ref
    orchestrator_ref = orch


async def interview_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()

    state = orchestrator_ref.get_session(session_id)
    if not state:
        await websocket.send_json({
            "type": "error",
            "message": "Session not found"
        })
        await websocket.close()
        return

    try:
        # Send opening message
        opening_text, opening_audio = await orchestrator_ref.get_opening(state)
        await websocket.send_json({
            "type": "agent_turn",
            "text": opening_text,
            "audio": base64.b64encode(opening_audio).decode("utf-8"),
            "phase": state.phase,
            "interview_ended": False
        })

        while True:
            raw = await websocket.receive_text()
            message = json.loads(raw)

            candidate_text = ""

            if message["type"] == "audio":
                audio_bytes = base64.b64decode(message["data"])
                result = await orchestrator_ref.stt.transcribe_with_confidence(
                    audio_bytes
                )
                candidate_text = result.get("text", "").strip()

                if not candidate_text:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Could not transcribe audio. Please try again."
                    })
                    continue

            elif message["type"] == "text":
                candidate_text = message["data"].strip()

            if not candidate_text:
                continue

            turn_result = await orchestrator_ref.process_turn(
                candidate_text=candidate_text,
                state=state
            )

            response_data = {
                "type": "agent_turn",
                "text": turn_result["response_text"],
                "audio": base64.b64encode(turn_result["audio"]).decode("utf-8"),
                "candidate_transcript": candidate_text,
                "phase": turn_result["phase"],
                "interview_ended": turn_result["interview_ended"]
            }

            await websocket.send_json(response_data)

            if turn_result["interview_ended"]:
                reports = turn_result.get("reports")
                if reports:
                    await websocket.send_json({
                        "type": "evaluation",
                        "mode": state.mode,
                        "overall_score": reports["overall_score"],
                        "grade": reports["grade"],
                        "technical_score": reports["technical_score"],
                        "behavioral_score": reports["behavioral_score"],
                        "integrity_score": reports["integrity_score"],
                        "recruiter_report": reports["recruiter_report"],
                        "mock_report": reports["mock_report"],
                        "integrity_report": reports["integrity_report"]
                    })
                break

    except WebSocketDisconnect:
        print(f"Client disconnected: {session_id}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except Exception:
            pass