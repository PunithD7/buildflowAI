"""
Security utilities - JWT, password hashing, RBAC
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from enum import Enum

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRole(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"
    GUEST = "guest"


class Permission(str, Enum):
    """System permissions."""
    CREATE_PROJECT = "create_project"
    DELETE_PROJECT = "delete_project"
    VIEW_PROJECT = "view_project"
    EXECUTE_WORKFLOW = "execute_workflow"
    VIEW_OBSERVABILITY = "view_observability"
    MANAGE_USERS = "manage_users"
    CONFIGURE_SECURITY = "configure_security"
    UPLOAD_DOCUMENTS = "upload_documents"
    VIEW_LOGS = "view_logs"
    SIMULATE_DDOS = "simulate_ddos"


ROLE_PERMISSIONS: Dict[UserRole, list[Permission]] = {
    UserRole.ADMIN: list(Permission),
    UserRole.DEVELOPER: [
        Permission.CREATE_PROJECT,
        Permission.VIEW_PROJECT,
        Permission.EXECUTE_WORKFLOW,
        Permission.VIEW_OBSERVABILITY,
        Permission.UPLOAD_DOCUMENTS,
        Permission.VIEW_LOGS,
    ],
    UserRole.VIEWER: [
        Permission.VIEW_PROJECT,
        Permission.VIEW_OBSERVABILITY,
        Permission.VIEW_LOGS,
    ],
    UserRole.GUEST: [
        Permission.VIEW_PROJECT,
    ],
}


def hash_password(password: str) -> str:
    """Hash a plain-text password."""
    return pwd_context.hash(password[:72])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password[:72], hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def check_permission(role: UserRole, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    return permission in ROLE_PERMISSIONS.get(role, [])


def require_permission(role: UserRole, permission: Permission):
    """Raise HTTPException if permission check fails."""
    if not check_permission(role, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {permission.value} requires elevated role",
        )


class EncryptionService:
    """Simple encryption for secrets in TEE-inspired execution."""
    
    def __init__(self):
        try:
            from cryptography.fernet import Fernet
            import base64
            import hashlib
            # Derive a proper 32-byte key from the config key
            key_bytes = hashlib.sha256(settings.ENCRYPTION_KEY.encode()).digest()
            fernet_key = base64.urlsafe_b64encode(key_bytes)
            self._fernet = Fernet(fernet_key)
            self._available = True
        except ImportError:
            logger.warning("cryptography package not available, using base64 encoding")
            self._available = False
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string."""
        if self._available:
            return self._fernet.encrypt(plaintext.encode()).decode()
        import base64
        return base64.b64encode(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a string."""
        if self._available:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        import base64
        return base64.b64decode(ciphertext.encode()).decode()


encryption_service = EncryptionService()
