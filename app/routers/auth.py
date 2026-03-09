from typing import Annotated, Optional

from fastapi import APIRouter, Body, Depends, Header

from app.models import User
from app.schemas import (
    AuthTokenResponse,
    LogoutRequest,
    TokenRefreshRequest,
    UserLoginRequest,
    UserOut,
    UserRegisterRequest,
)
from app.services.auth_service import (
    get_current_user,
    login_user,
    logout_token,
    refresh_access_token,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalLogoutPayload = Annotated[Optional[LogoutRequest], Body()]


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserRegisterRequest):
    user = register_user(username=payload.username, password=payload.password)
    return UserOut(id=user.id if user.id is not None else 0, username=user.username)


@router.post("/login", response_model=AuthTokenResponse)
def login(payload: UserLoginRequest):
    access, refresh, username = login_user(username=payload.username, password=payload.password)
    expires_in = int((access.expires_at - access.created_at).total_seconds())
    return AuthTokenResponse(
        access_token=access.token,
        refresh_token=refresh.token,
        username=username,
        expires_in=expires_in,
    )


@router.post("/refresh", response_model=AuthTokenResponse)
def refresh(payload: TokenRefreshRequest):
    access, username = refresh_access_token(payload.refresh_token)
    expires_in = int((access.expires_at - access.created_at).total_seconds())
    return AuthTokenResponse(
        access_token=access.token,
        refresh_token=payload.refresh_token,
        username=username,
        expires_in=expires_in,
    )


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return UserOut(id=user.id if user.id is not None else 0, username=user.username)


@router.post("/logout")
def logout(
    payload: OptionalLogoutPayload = None,
    authorization: str = Header(default=""),
):
    access_token = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    refresh_token = payload.refresh_token if payload else ""
    logout_token(access_token=access_token, refresh_token=refresh_token or "")
    return {"ok": True}
