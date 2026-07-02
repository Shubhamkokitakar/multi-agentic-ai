from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

from graph.cricket_graph import graph
from authentication.jwt_validation import verify_token
from utils.request_counter import request_counts
router = APIRouter()

ROLE_LIMITS = {
    "user": 5,
    "admin": 100,
}

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):

    await websocket.accept()

    token = websocket.query_params.get("token")

    user = verify_token(token)

    

    if not user:
        await websocket.close(code=1008)
        return


    email = user["email"]
    role = user["role"]
    conversation_history = []
    request_limit = ROLE_LIMITS.get(role, 3)

    if email not in request_counts:
        request_counts[email] = 0
    try:
        while True:
            if request_counts[email] >= request_limit:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Maximum {request_limit} questions per session reached. Please reconnect to start a new session."
                })
                await websocket.close(code=1008)
                break

            question = await websocket.receive_text()
            request_counts[email] += 1

            await websocket.send_json({
             "type": "stage",
             "stage": "received",
             "message": "Question received"
            })

            final_answer = ""
            final_followups = []

            # -------------------------
            # STREAM EVENTS FROM GRAPH
            # astream_events replaces astream + manual callbacks.
            # version="v2" is required for LangGraph >= 0.2.
            # -------------------------
            async for event in graph.astream_events(
                {
                    "question": question,
                    "history": conversation_history,
                },
                version="v2",
            ):
                kind = event["event"]
                data = event.get("data", {})

                # LLM token streamed from rag_agent
                if kind == "on_custom_event" and event.get("name") == "token":
                    await websocket.send_json(data)

                # Stage updates dispatched from rag_node
                elif kind == "on_custom_event" and event.get("name") == "stage":
                    await websocket.send_json(data)

                # Capture final graph output from each state update
                elif kind == "on_chain_end":
                    output = data.get("output", {})
                    if isinstance(output, dict):
                        if output.get("response"):
                            final_answer = output["response"]
                        if output.get("follow_ups"):
                            final_followups = output["follow_ups"]

            await websocket.send_json({
                "type": "final",
                "answer": final_answer,
                "follow_ups": final_followups,
            })

            conversation_history.extend([
                {"role": "user", "content": question},
                {"role": "assistant", "content": final_answer},
            ])
            conversation_history = conversation_history[-10:]
    except WebSocketDisconnect:
        print(f"CLIENT DISCONNECTED: {email}")

    except Exception as e:
        print("WEBSOCKET ERROR:", str(e))