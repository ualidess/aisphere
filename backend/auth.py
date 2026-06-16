from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from repositories import UserRepository
from schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from security import create_access_token, get_password_hash, verify_password
from dependencies import get_current_user
from models import User
from services import UserService


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_db),
):
    existing_user = await UserRepository.get_by_email(
        session=session,
        email=payload.email,
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    password_hash = get_password_hash(payload.password)

    user = await UserService.create_user(
        session=session,
        email=payload.email,
        password_hash=password_hash,
    )

    return UserResponse(
        id=user.id,
        email=user.email,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db),
):
    user = await UserRepository.get_by_email(
        session=session,
        email=payload.email,
    )

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(subject=str(user.id))

    return TokenResponse(access_token=access_token)

@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
    )