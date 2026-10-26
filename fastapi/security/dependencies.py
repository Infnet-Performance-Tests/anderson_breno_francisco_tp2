from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

import crud
from database import get_session
from models.tables import User
from security.jwt import jwt_service

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/token",
    scheme_name="OAuth2PasswordBearer",
    description=(
        "JWT obtido em `POST /auth/token`. Envie no header "
        "`Authorization: Bearer <token>`. O token expira em 30 minutos."
    ),
)

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[Session, Depends(get_session)],
) -> User:
    subject = jwt_service.decode_subject(token)
    if subject is None:
        raise _CREDENTIALS_ERROR

    # O token só vale enquanto o usuário existir e estiver ativo no banco.
    user = crud.get_user_by_username(session, subject)
    if user is None or not user.is_active:
        raise _CREDENTIALS_ERROR
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
