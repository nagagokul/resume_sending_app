from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_current_user, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas import PreferencesUpdate, TokenResponse, UserCreate, UserLogin, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    existing = await db.execute(select(User).where(User.email == payload.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        preferences={
            "target_roles": [
                "Senior Software Engineer",
                "Software Engineer",
                "Systems Software Engineer",
                "Embedded Software Engineer",
                "Network Software Engineer",
                "Linux Software Engineer",
                "Device Driver Engineer",
                "Platform Software Engineer",
            ],
            "locations": [
                "Bangalore",
                "Hyderabad",
                "Pune",
                "Chennai",
                "Noida",
                "Gurgaon",
                "Gurugram",
                "Mumbai",
                "India",
                "Remote",
            ],
            "seniority": "SENIOR",
        },
    )
    db.add(user)
    await db.flush()
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me", response_model=UserOut)
async def update_me(
    payload: PreferencesUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    if payload.preferences is not None:
        user.preferences = {**(user.preferences or {}), **payload.preferences}
    if payload.scoring_weights is not None:
        user.scoring_weights = payload.scoring_weights
    if payload.full_name is not None:
        user.full_name = payload.full_name
    await db.flush()
    return user
