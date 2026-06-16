import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


JWT_SECRET = os.getenv("JWT_SECRET", "change_me_super_secret")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": subject,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
        )
        subject = payload.get("sub")

        if subject is None:
            return None

        return str(subject)

    except JWTError:
        return None