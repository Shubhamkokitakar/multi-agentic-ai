from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from authentication.models import User
from passlib.context import CryptContext
from jose import jwt
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from database.db import get_db
from authentication.schemas import SignupRequest, LoginRequest, TokenResponse

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY not set in environment")
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter()

@router.post("/api/signup")
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    hashed = pwd_context.hash(payload.password)
    user = User(email=payload.email.lower(), hashed_password=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email}


@router.post("/api/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    print("Login attempt for email:", payload)
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    print("User found:", user)

    if not user or not pwd_context.verify(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    expire = datetime.now(timezone.utc) + timedelta(hours=0, minutes=30)  # Token valid for 30 minutes

    token = jwt.encode(
        {
            "sub": user.email,
            "exp": expire
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }

# add rate limiting