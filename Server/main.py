# main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

# Allow frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    
    await websocket.accept()
    print("Client Connected")

    try:
        while True:
            
            # Receive question from UI
            question = await websocket.receive_text()

            # Print in backend terminal
            print(f"Question from UI: {question}")

            # Optional response back to UI
            await websocket.send_text(f"Received: {question}")

    except WebSocketDisconnect:
        print("Client Disconnected")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)