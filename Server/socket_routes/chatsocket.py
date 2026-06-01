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

            retrieval_sent = False
            generation_sent = False

            # -------------------------
            # TOKEN STREAMING CALLBACK
            # -------------------------
            async def send_token(token: str):

                await websocket.send_json({
                    "type": "token",
                    "value": token
                })

            # -------------------------
            # STAGE CALLBACK
            # -------------------------
            async def send_stage(message: str):

                await websocket.send_json({
                    "type": "stage",
                    "message": message
                })

            # -------------------------
            # RUN GRAPH
            # -------------------------
            async for event in graph.astream(
                {
                    "question": question,
                    "history": conversation_history,
                    "token_callback": send_token,
                    "stage_callback": send_stage
                },
                stream_mode="values"
            ):

                print("EVENT:", event)

                # -------------------------
                # Retrieval stage
                # -------------------------
                if (
                    event.get("route") == "rag"
                    and not retrieval_sent
                ):

                    await send_stage(
                        "Looking for relevant information..."
                    )

                    retrieval_sent = True

                # -------------------------
                # Generation stage
                # -------------------------
                if (
                    event.get("retrieved_docs")
                    and not generation_sent
                ):

                    await send_stage(
                        "Generating answer..."
                    )

                    generation_sent = True

                # -------------------------
                # Capture final response
                # -------------------------
                if event.get("response"):
                    final_answer = event["response"]

                if event.get("follow_ups"):
                    final_followups = event["follow_ups"]

            # -------------------------
            # Final message
            # -------------------------
            await websocket.send_json({
                "type": "final",
                "answer": final_answer,
                "follow_ups": final_followups
            })

            # -------------------------
            # Save history
            # -------------------------
            conversation_history.extend([
                {
                    "role": "user",
                    "content": question
                },
                {
                    "role": "assistant",
                    "content": final_answer
                }
            ])

    except WebSocketDisconnect:
        print(f"CLIENT DISCONNECTED: {email}")

    except Exception as e:
        print("WEBSOCKET ERROR:", str(e))