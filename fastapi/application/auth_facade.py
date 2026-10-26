from sqlmodel import Session

import crud
from security.jwt import jwt_service
from security.passwords import hash_password, verify_password

# Hash usado quando o usuário não existe: a verificação roda do mesmo jeito, então o
# tempo de resposta não revela quais usernames estão cadastrados.
_DUMMY_HASH = hash_password("dummy-password-for-constant-time-check")


class AuthFacade:
    """Public application boundary for the authentication use case."""

    def authenticate(self, session: Session, username: str, password: str) -> str | None:
        user = crud.get_user_by_username(session, username)
        password_ok = verify_password(password, user.hashed_password if user else _DUMMY_HASH)

        if user is None or not user.is_active or not password_ok:
            return None

        return jwt_service.create_access_token(subject=user.username)


auth_facade = AuthFacade()
