from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base
import datetime
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB
try:
    from pgvector.sqlalchemy import Vector
except Exception:
    Vector = None

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    # attribute named `meta` to avoid colliding with SQLAlchemy's `metadata`
    meta = Column('metadata', JSONB, nullable=True)
    # Vector type requires pgvector; dimension set to 1536 (adjust if needed)
    if Vector is not None:
        embedding = Column(Vector(1536), nullable=False)
    else:
        embedding = Column(Text, nullable=False)
