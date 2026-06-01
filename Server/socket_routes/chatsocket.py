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

            sent_stages = set()
            final_answer = ""
            final_followups = []

            event_count = 0

            async for event in graph.astream(
                {
                    "question": question,
                    "history": conversation_history
                },
                stream_mode="values"
            ):

                event_count += 1
                print(f"EVENT #{event_count}: {event}")

                # ----------------------------
                # ROUTING STAGE
                # ----------------------------
                if event.get("route") and "route" not in sent_stages:
                    await websocket.send_json({
                        "type": "stage",
                        "message": "Understanding your question..."
                    })
                    sent_stages.add("route")

                # ----------------------------
                # RETRIEVAL STAGE
                # ----------------------------
                if event.get("retrieved_docs") and "retrieval" not in sent_stages:
                    await websocket.send_json({
                        "type": "stage",
                        "message": "Looking for relevant information..."
                    })
                    sent_stages.add("retrieval")

                # ----------------------------
                # GENERATION STAGE
                # ----------------------------
                if event.get("response") and "generation" not in sent_stages:
                    await websocket.send_json({
                        "type": "stage",
                        "message": "Generating answer..."
                    })
                    sent_stages.add("generation")

                # ----------------------------
                # CAPTURE FINAL OUTPUT
                # ----------------------------
                if event.get("response"):
                    final_answer = event["response"]

                if event.get("follow_ups"):
                    final_followups = event["follow_ups"]

            print(f"TOTAL EVENTS RECEIVED: {event_count}")

            await websocket.send_json({
                "type": "final",
                "answer": final_answer,
                "follow_ups": final_followups
            })

            conversation_history.append({
                "question": question,
                "answer": final_answer
            })

    except WebSocketDisconnect:
        print(f"CLIENT DISCONNECTED: {email}")