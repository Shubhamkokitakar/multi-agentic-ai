# Cricket RAG Chatbot

A chatbot that answers cricket-related questions and provides live match data and updates.

## System Architecture

```mermaid
graph LR
    A["WebSocket Client"] <-->|JSON| B["FastAPI Server<br/>main.py"]
    
    B -->|graph.ainvoke| C["LangGraph<br/>cricket_graph.py"]
    
    C --> D["Graph Nodes"]
    D --> D1["Rewrite Node<br/>query_refiner.py"]
    D --> D2["Router Node"]
    D --> D3["RAG Node"]
    D --> D4["Live Node"]
    D --> D5["Follow-up Node"]
    
    D3 --> E1["Vector Store<br/>Chroma DB"]
    D4 --> E2["Cricket API<br/>cricapi.com"]
    D5 --> E3["OpenAI LLM<br/>gpt-4.1-mini"]
    D1 --> E3
    D3 --> E3
    D4 --> E3
    
    B --> F["Session State"]
    F --> F1["conversation_history"]
    
    style B fill:#bbdefb
    style C fill:#c8e6c9
    style D1 fill:#e1f5ff
    style D2 fill:#fff3e0
    style D3 fill:#e8f5e9
    style D4 fill:#f3e5f5
    style D5 fill:#fce4ec
    style E1 fill:#ffccbc
    style E2 fill:#ffccbc
    style E3 fill:#ffccbc
