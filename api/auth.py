"""
Authentication Service for Emergency Ambulance Demand & Dispatch System
Provides JWT-based credential verification, token issuance, and dispatcher session validation.
"""

import os
import time
from typing import Dict, Any, Optional, List
import jwt
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Header, Depends, status

# ---------------------------------------------------------------------------
# Security & Configuration
# ---------------------------------------------------------------------------
JWT_SECRET = os.getenv("JWT_SECRET", "montgomery-county-ems-cad-dispatch-secret-2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_SECONDS = 86400  # 24 hours

# Pre-authorized dispatch personnel credentials
AUTHORIZED_USERS: Dict[str, Dict[str, Any]] = {
    "dispatcher_admin": {
        "password": "emergency2026!",
        "username": "dispatcher_admin",
        "full_name": "Capt. Alex Vance",
        "role": "Chief Dispatch Supervisor",
        "dispatcher_id": "CAD-911-01",
        "unit": "Montgomery County Emergency Operations Center",
        "permissions": ["read", "dispatch", "triage", "admin", "allocate", "routing"],
    },
    "paramedic_user": {
        "password": "medic123",
        "username": "paramedic_user",
        "full_name": "Lt. Sarah Jenkins",
        "role": "Field Triage Paramedic",
        "dispatcher_id": "MED-402",
        "unit": "Medic 308 - Lower Merion ALS",
        "permissions": ["read", "triage", "routing"],
    },
}

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str = Field(..., description="Dispatcher username or Call Sign", min_length=1, examples=["dispatcher_admin"])
    password: str = Field(..., description="Dispatcher account password", min_length=1, examples=["emergency2026!"])


class UserProfile(BaseModel):
    username: str
    full_name: str
    role: str
    dispatcher_id: str
    unit: str
    permissions: List[str]


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = JWT_EXPIRATION_SECONDS
    user: UserProfile


class AuthVerifyResponse(BaseModel):
    valid: bool
    user: UserProfile


# ---------------------------------------------------------------------------
# Token Utilities
# ---------------------------------------------------------------------------
def create_access_token(user_data: Dict[str, Any]) -> str:
    """Generates a signed JWT access token with 24h validity."""
    now = int(time.time())
    payload = {
        "sub": user_data["username"],
        "name": user_data["full_name"],
        "role": user_data["role"],
        "dispatcher_id": user_data["dispatcher_id"],
        "unit": user_data["unit"],
        "permissions": user_data["permissions"],
        "iat": now,
        "exp": now + JWT_EXPIRATION_SECONDS,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a JWT token. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token signature.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(authorization: Optional[str] = Header(None)) -> UserProfile:
    """FastAPI dependency to extract and verify the bearer token."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    payload = decode_access_token(token)
    username = payload.get("sub")
    if not username or username not in AUTHORIZED_USERS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorized dispatcher not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_info = AUTHORIZED_USERS[username]
    return UserProfile(
        username=user_info["username"],
        full_name=user_info["full_name"],
        role=user_info["role"],
        dispatcher_id=user_info["dispatcher_id"],
        unit=user_info["unit"],
        permissions=user_info["permissions"],
    )


# ---------------------------------------------------------------------------
# Router Definition
# ---------------------------------------------------------------------------
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Dispatcher Sign In",
    description="Authenticates dispatch personnel and returns a signed 24h JWT access token."
)
def login(credentials: LoginRequest):
    user_record = AUTHORIZED_USERS.get(credentials.username.strip())
    if not user_record or user_record["password"] != credentials.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid dispatcher credentials. Please verify your username and password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user_record)
    user_profile = UserProfile(
        username=user_record["username"],
        full_name=user_record["full_name"],
        role=user_record["role"],
        dispatcher_id=user_record["dispatcher_id"],
        unit=user_record["unit"],
        permissions=user_record["permissions"],
    )

    return LoginResponse(
        access_token=token,
        token_type="Bearer",
        expires_in=JWT_EXPIRATION_SECONDS,
        user=user_profile,
    )


@auth_router.get(
    "/me",
    response_model=AuthVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current Dispatcher Session Profile"
)
def get_me(current_user: UserProfile = Depends(get_current_user)):
    return AuthVerifyResponse(valid=True, user=current_user)


@auth_router.get(
    "/verify",
    response_model=AuthVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify Access Token"
)
def verify_session(current_user: UserProfile = Depends(get_current_user)):
    return AuthVerifyResponse(valid=True, user=current_user)
