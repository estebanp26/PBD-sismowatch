"""
SismoWatch - Módulo de Seguridad y RBAC (Role-Based Access Control)
Autenticación JWT, verificación de hashes bcrypt y dependencias de roles.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt
from sqlalchemy import text

from app.core.config import settings
from app.db.session import get_db

security_bearer = HTTPBearer(auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña en texto plano coincide con el hash bcrypt."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8")[:72],
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """Genera hash bcrypt para almacenar contraseñas."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8")[:72], salt).decode("utf-8")

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Genera token JWT firmado con expiración configurada."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    token: Optional[str] = Query(default=None),
    db = Depends(get_db)
) -> Dict[str, Any]:
    """
    Dependencia FastAPI para validar la presencia y validez del token JWT.
    Acepta el token vía Header Authorization Bearer o como Query Parameter 'token' (para EventSource SSE).
    Sin token o con token inválido retorna HTTP 401 Unauthorized.
    """
    raw_token = credentials.credentials if credentials else (token or request.query_params.get("token"))
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de autenticación no proporcionadas.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_str = raw_token
    try:
        payload = jwt.decode(token_str, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: Optional[str] = payload.get("sub")
        role: Optional[str] = payload.get("role")
        if username is None or role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o malformado.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado o firma criptográfica inválida.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validar que el usuario exista en curated.users
    user_query = text("""
        SELECT id, username, full_name, role, is_active
        FROM curated.users
        WHERE username = :user AND is_active = TRUE;
    """)
    user_row = db.execute(user_query, {"user": username}).fetchone()

    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "id": user_row[0],
        "username": user_row[1],
        "full_name": user_row[2],
        "role": user_row[3],
        "is_active": user_row[4]
    }

def require_viewer_or_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Valida que el usuario tenga rol 'viewer' o 'admin'."""
    if current_user.get("role") not in ("viewer", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido: rol no autorizado."
        )
    return current_user

def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Control de acceso estricto RBAC:
    Rechaza con 403 Forbidden a usuarios con rol 'viewer'.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acción denegada: se requieren privilegios de Administrador para ejecutar esta operación."
        )
    return current_user
