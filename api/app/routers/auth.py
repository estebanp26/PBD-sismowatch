"""
SismoWatch - Router de Autenticación (/auth)
Inicio de sesión público y generación de tokens JWT con roles 'viewer' y 'admin'.
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_password, create_access_token
from app.db.session import get_db
from app.schemas.earthquake import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Autenticación"])

@router.post("/login", response_model=TokenResponse, summary="Inicio de sesión y obtención de JWT")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Autentica al usuario contra la base de datos y genera un token JWT firmado.
    Roles disponibles: 'viewer' (consultas) y 'admin' (control total).
    """
    user_query = text("""
        SELECT id, username, hashed_password, full_name, role, is_active
        FROM curated.users
        WHERE username = :username;
    """)
    user_row = db.execute(user_query, {"username": request.username.strip()}).fetchone()

    if not user_row or not verify_password(request.password, user_row[2]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nombre de usuario o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user_row[5]:  # is_active
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La cuenta de usuario se encuentra deshabilitada.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role = user_row[4]
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_row[1], "role": role, "name": user_row[3]},
        expires_delta=access_token_expires
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        role=role,
        username=user_row[1],
        full_name=user_row[3]
    )
