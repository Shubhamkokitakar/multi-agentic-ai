from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from database.db import SessionLocal
from database import models
from nodes.embedding_node import Embedder

router = APIRouter()
embedder = Embedder()


class DocIn(BaseModel):
    text: str
    metadata: Optional[dict] = None


class InsertDocsRequest(BaseModel):
    documents: List[DocIn]


class SearchRequest(BaseModel):
    query: str
    n_results: int = 3


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/api/neon/documents")
def insert_documents(req: InsertDocsRequest, db: Session = Depends(get_db)):
    texts = [d.text for d in req.documents]
    embeddings = embedder.embed_batch(texts)
    docs = []
    for d, emb in zip(req.documents, embeddings):
        doc = models.Document(text=d.text, meta=d.metadata, embedding=emb)
        db.add(doc)
        docs.append(doc)
    db.commit()
    for doc in docs:
        db.refresh(doc)
    return {"inserted": len(docs)}


@router.post("/api/neon/search")
def search(req: SearchRequest, db: Session = Depends(get_db)):
    q_emb = embedder.embed_batch([req.query])[0]
    # Use pgvector distance operator '<->' when available
    try:
        q = db.query(models.Document).order_by(models.Document.embedding.op("<->")(q_emb)).limit(req.n_results)
        results = q.all()
    except Exception:
        raise HTTPException(status_code=500, detail="Postgres pgvector query failed. Ensure pgvector is installed and `DATABASE_URL` points to Postgres/Neon.")
    out = []
    for r in results:
        out.append({"id": r.id, "text": r.text, "metadata": r.meta})
    return {"results": out}
