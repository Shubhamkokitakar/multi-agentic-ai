from fastapi import FastAPI, WebSocket
from starlette.websockets import WebSocketDisconnect

from graph.cricket_graph import graph

app = FastAPI()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):

    await websocket.accept()
    conversation_history = []


    print("CLIENT CONNECTED")

    try:

        while True:

            question = await websocket.receive_text()
            conversation_history.append({"role": "user", "content": question})

            print("\nQUESTION:", question)

            result = await graph.ainvoke(

                {
                    "question": question,
                    "history": conversation_history

                }
            )

            conversation_history.append({"role": "assistant", "content": result.get("response", "")})
            print("RESPONSE:", result)
            await websocket.send_json({
                "answer": result.get("response", ""),
                "follow_ups": result.get("follow_ups", "")
            })
            print(result)

    except WebSocketDisconnect:

        print("CLIENT DISCONNECTED")