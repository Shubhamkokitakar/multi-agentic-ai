from fastapi import FastAPI, WebSocket
from starlette.websockets import WebSocketDisconnect

from graph.cricket_graph import graph

app = FastAPI()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):

    await websocket.accept()

    print("CLIENT CONNECTED")

    try:

        while True:

            question = await websocket.receive_text()

            print("\nQUESTION:", question)

            result = await graph.ainvoke(

                {
                    "question": question
                }
            )

            print(result)

            await websocket.send_text(

                result["response"]
            )

    except WebSocketDisconnect:

        print("CLIENT DISCONNECTED")