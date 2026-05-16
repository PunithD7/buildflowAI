"""
Authentication endpoints
"""
import time
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    UserRole
)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# In-memory user store (replace with Supabase in production)
_users_db: dict = {
    "demo@buildflow.ai": {
        "id": "user-demo-001",
        "email": "demo@buildflow.ai",
        "name": "Demo User",
        "hashed_password": hash_password("demo123"),
        "role": UserRole.DEVELOPER,
        "created_at": time.time(),
    }
}


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: Optional[UserRole] = UserRole.DEVELOPER


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Dependency to get current authenticated user."""
    payload = decode_token(token)
    user_id = payload.get("sub")
    
    # Find user
    for user in _users_db.values():
        if user["id"] == user_id:
            return user
    
    raise HTTPException(status_code=401, detail="User not found")


@router.post("/register", status_code=201)
async def register(request: RegisterRequest):
    """Register a new user."""
    if request.email in _users_db:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    import uuid
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "email": request.email,
        "name": request.name,
        "hashed_password": hash_password(request.password),
        "role": request.role,
        "created_at": time.time(),
    }
    _users_db[request.email] = user
    
    return {"message": "User registered successfully", "user_id": user_id}


@router.post("/login", response_model=LoginResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user and return JWT tokens."""
    user = _users_db.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = {"sub": user["id"], "email": user["email"], "role": user["role"]}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
        }
    )


@router.post("/demo-login", response_model=LoginResponse)
async def demo_login():
    """Quick demo login without credentials."""
    user = _users_db["demo@buildflow.ai"]
    token_data = {"sub": user["id"], "email": user["email"], "role": user["role"]}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
        }
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user profile."""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        role=current_user["role"],
    )
