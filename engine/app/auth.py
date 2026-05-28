from datetime import datetime, timedelta, timezone
import os

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, delete, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from app.database import Base, get_db


load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 14

if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is not configured")

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
router = APIRouter(prefix="/auth", tags=["auth"])
history_router = APIRouter(prefix="/generations", tags=["generations"])


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    login: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    generations: Mapped[list["GenerationHistory"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class GenerationHistory(Base):
    __tablename__ = "generation_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(160))
    shape: Mapped[str] = mapped_column(String(40))
    width_label: Mapped[str] = mapped_column(String(120))
    auto_fields: Mapped[list[str]] = mapped_column(JSONB)
    locked_fields: Mapped[list[str]] = mapped_column(JSONB)
    adjustment_count: Mapped[int] = mapped_column(Integer, default=0)
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped[User] = relationship(back_populates="generations")


class AuthRequest(BaseModel):
    login: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=4, max_length=200)


class ChangePasswordRequest(BaseModel):
    new_password: str = Field(min_length=4, max_length=200)


class UserOut(BaseModel):
    login: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class GenerationCreate(BaseModel):
    title: str
    shape: str
    width_label: str
    auto_fields: list[str] = Field(default_factory=list)
    locked_fields: list[str] = Field(default_factory=list)
    adjustment_count: int = 0
    details: dict = Field(default_factory=dict)


class GenerationOut(GenerationCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class UserProfile(BaseModel):
    login: str
    history: list[GenerationOut]


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_context.verify(password, password_hash)


def create_access_token(user: User) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user.id), "login": user.login, "exp": expires_at}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = int(payload.get("sub", "0"))
    except (JWTError, ValueError):
        raise credentials_error from None

    user = db.get(User, user_id)
    if user is None:
        raise credentials_error

    return user


def serialize_generation(generation: GenerationHistory) -> GenerationOut:
    return GenerationOut(
        id=generation.id,
        created_at=generation.created_at,
        title=generation.title,
        shape=generation.shape,
        width_label=generation.width_label,
        auto_fields=generation.auto_fields or [],
        locked_fields=generation.locked_fields or [],
        adjustment_count=generation.adjustment_count,
        details=generation.details or {},
    )


@router.post("/register", response_model=TokenResponse)
def register(payload: AuthRequest, db: Session = Depends(get_db)):
    login = payload.login.strip()
    if not login:
        raise HTTPException(status_code=400, detail="Login is required")

    existing_user = db.scalar(select(User).where(User.login == login))
    if existing_user:
        raise HTTPException(status_code=409, detail="User already exists")

    user = User(login=login, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenResponse(access_token=create_access_token(user), user=UserOut(login=user.login))


@router.post("/login", response_model=TokenResponse)
def login(payload: AuthRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.login == payload.login.strip()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid login or password")

    return TokenResponse(access_token=create_access_token(user), user=UserOut(login=user.login))


@router.get("/me", response_model=UserProfile)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(GenerationHistory)
        .where(GenerationHistory.user_id == current_user.id)
        .order_by(GenerationHistory.created_at.desc())
        .limit(30)
    ).all()

    return UserProfile(
        login=current_user.login,
        history=[serialize_generation(row) for row in rows],
    )


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"status": "ok"}


@history_router.get("", response_model=list[GenerationOut])
def list_generations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(GenerationHistory)
        .where(GenerationHistory.user_id == current_user.id)
        .order_by(GenerationHistory.created_at.desc())
        .limit(30)
    ).all()
    return [serialize_generation(row) for row in rows]


@history_router.post("", response_model=GenerationOut)
def create_generation(
    payload: GenerationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = GenerationHistory(
        user_id=current_user.id,
        title=payload.title,
        shape=payload.shape,
        width_label=payload.width_label,
        auto_fields=payload.auto_fields,
        locked_fields=payload.locked_fields,
        adjustment_count=payload.adjustment_count,
        details=payload.details,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize_generation(row)


@history_router.delete("")
def clear_generations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = db.execute(
        delete(GenerationHistory).where(GenerationHistory.user_id == current_user.id)
    )
    db.commit()
    return {"status": "ok", "deleted": result.rowcount or 0}


@history_router.delete("/{generation_id}")
def delete_generation(
    generation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = db.execute(
        delete(GenerationHistory).where(
            GenerationHistory.id == generation_id,
            GenerationHistory.user_id == current_user.id,
        )
    )
    db.commit()
    if not result.rowcount:
        raise HTTPException(status_code=404, detail="Generation not found")
    return {"status": "ok"}
