import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from app.config import settings

# JWT configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt directly."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt or pbkdf2 hash."""
    if not hashed_password or not plain_password:
        return False
    # Check for pbkdf2_sha256 hash
    if hashed_password.startswith("pbkdf2_sha256$"):
        try:
            algorithm, rounds, encoded_salt, encoded_digest = hashed_password.split("$")
            if algorithm != "pbkdf2_sha256":
                return False
            salt = base64.urlsafe_b64decode(encoded_salt.encode("ascii"))
            expected = base64.urlsafe_b64decode(encoded_digest.encode("ascii"))
            actual = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, int(rounds))
            return hmac.compare_digest(actual, expected)
        except (ValueError, TypeError, Exception):
            return False
    # Check for bcrypt hash
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token valid for 30 minutes."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        try:
            from app.auth import SECRET
            return jwt.decode(token, SECRET, algorithms=["HS256"])
        except Exception:
            raise

