from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

from graph.cricket_graph import graph
from authentication.jwt_validation import verify_token

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):

    token = websocket.query_params.get("token")
    email = verify_token(token)

    if not email:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    conversation_history = []

    try:
        while True:
            question = await websocket.receive_text()

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

    except WebSocketDisconnect:
        print(f"CLIENT DISCONNECTED: {email}")

    except Exception as e:
        print("WEBSOCKET ERROR:", str(e))