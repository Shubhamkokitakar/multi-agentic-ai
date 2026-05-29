# Cricket RAG Chatbot

A chatbot that answers cricket-related questions and provides live match data and updates.

## System Architecture

```mermaid
graph TD

    A["WebSocket Client"] <-->|JSON| B["FastAPI Server"]

    B --> C["LangGraph Workflow"]

    C --> D1["Rewrite Agent"]
    D1 --> D2["Router Agent"]

    D2 -->|General Cricket Query| E1["Generic Agent"]
    D2 -->|Historical / Knowledge Query| E2["RAG Agent"]
    D2 -->|Live Match Query| E3["Live Agent"]

    E1 --> F["Follow-up Agent"]
    E2 --> F
    E3 --> F

    E2 --> G1["Chroma Vector DB"]
    E3 --> G2["CricAPI"]

    E1 --> H["OpenAI GPT-4.1-mini"]
    E2 --> H
    E3 --> H
    F --> H

    B --> I["Session Memory"]
    I --> I1["Conversation History"]

    style D1 fill:#e1f5fe
    style D2 fill:#fff3e0
    style E1 fill:#f3e5f5
    style E2 fill:#e8f5e9
    style E3 fill:#fce4ec
    style F fill:#ede7f6
```

## Features

* Real-time cricket match updates
* Cricket knowledge Q&A
* RAG-based retrieval using vector database
* Live cricket API integration
* Conversational memory support
* Multi-agent workflow using LangGraph
* WebSocket-based streaming responses

## Tech Stack

* FastAPI
* LangGraph
* LangChain
* LangSmith
* OpenAI GPT-4.1-mini
* ChromaDB
* WebSockets
* CricAPI

```
```
