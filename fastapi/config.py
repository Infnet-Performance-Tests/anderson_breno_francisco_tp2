import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "Secure Support Agent Lab"
    app_version: str = "0.3.0"

    # TP3: as credenciais deixaram de ficar em código. Os usuários vivem na tabela
    # `users` do database.db, com senha em hash PBKDF2 (security/passwords.py).

    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_secret_key: str = os.getenv(
        "JWT_SECRET_KEY",
        "local-development-only-secret-change-before-deploying",
    )

    allowed_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    )
    auth_rate_limit: str = "10/minute"


settings = Settings()
