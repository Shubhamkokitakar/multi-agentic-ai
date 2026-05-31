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
    # use email as the primary identifier
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

