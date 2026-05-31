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

            result = await graph.ainvoke(
                {
                    "question": question,
                    "history": conversation_history
                }
            )

            await websocket.send_json(
                {
                    "answer": result.get("response", ""),
                    "follow_ups": result.get("follow_ups", [])
                }
            )

    except WebSocketDisconnect:
        print(f"CLIENT DISCONNECTED: {email}")