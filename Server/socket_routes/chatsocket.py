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
            # TOKEN STREAM
            # -------------------------
            async def send_token(token: str):
                await websocket.send_json({
                    "type": "token",
                    "value": token
                })

            # -------------------------
            # STAGE STREAM
            # -------------------------
            async def send_stage(payload: dict):
                await websocket.send_json(payload)

            # -------------------------
            # RUN GRAPH
            # -------------------------
            async for state in graph.astream(
                {
                    "question": question,
                    "history": conversation_history,
                    "token_callback": send_token,
                    "stage_callback": send_stage
                },
                stream_mode="values"
            ):

                print("STATE:", state)

                if state.get("response"):
                    final_answer = state["response"]

                if state.get("follow_ups"):
                    final_followups = state["follow_ups"]

            await websocket.send_json({
                "type": "final",
                "answer": final_answer,
                "follow_ups": final_followups
            })

            conversation_history.extend([
                {"role": "user", "content": question},
                {"role": "assistant", "content": final_answer}
            ])

    except WebSocketDisconnect:
        print(f"CLIENT DISCONNECTED: {email}")

    except Exception as e:
        print("WEBSOCKET ERROR:", str(e))