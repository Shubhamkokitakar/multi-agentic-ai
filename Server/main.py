from http.client import HTTPException

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from exceptions.handlers import generic_exception_handler, http_exception_handler
from database.db import engine
from authentication.models import Base
from authentication.auth import router as auth_router
from socket_routes.chatsocket import router as websocket_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "https://multi-agentic-ai-1.onrender.com",
        "https://multi-agentic-ai.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

Base.metadata.create_all(bind=engine)
print('engine', engine)

app.include_router(auth_router)
app.include_router(websocket_router)
app.add_exception_handler(
    HTTPException,
    http_exception_handler
)

app.add_exception_handler(
    Exception,
    generic_exception_handler
)