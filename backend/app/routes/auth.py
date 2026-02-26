from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.auth import get_password_hash, verify_password, create_access_token
from app.models.models import User, Tourist
from app.schemas import UserCreate, UserLogin, Token, TouristCreate

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger("tourist_safety.auth")


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    try:
        if db.query(User).filter(User.username == user_data.username).first():
            raise HTTPException(status_code=400, detail="Username already registered")
        if db.query(User).filter(User.email == user_data.email).first():
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed = get_password_hash(user_data.password)
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed,
            role=user_data.role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Auto-create tourist profile
        if user.role == "tourist":
            tourist = Tourist(user_id=user.id, name=user_data.username)
            db.add(tourist)
            db.commit()

        token = create_access_token({"sub": user.username, "role": user.role})
        return Token(access_token=token, token_type="bearer", role=user.role, user_id=user.id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Database error: {str(e)}"
        )


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.username == credentials.username).first()
        if not user or not verify_password(credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )
        token = create_access_token({"sub": user.username, "role": user.role})
        return Token(access_token=token, token_type="bearer", role=user.role, user_id=user.id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Database error: {str(e)}"
        )
