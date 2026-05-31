from fastapi import FastAPI, WebSocket
from dotenv import load_dotenv
from starlette.websockets import WebSocketDisconnect

from graph.cricket_graph import graph
from langchain_openai import ChatOpenAI
load_dotenv()
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Wire auth router and ensure DB tables exist
from database import models
from database.db import engine
from auth import router as auth_router

models.Base.metadata.create_all(bind=engine)
app.include_router(auth_router)
from neon_vectors import router as neon_router
app.include_router(neon_router)


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