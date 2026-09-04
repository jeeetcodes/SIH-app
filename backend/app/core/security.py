import hashlib
import hmac
import base64
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.core.config import settings

ALGORITHM = "HS256"
PBKDF2_ITERATIONS = 120_000


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"{salt.hex()}${derived.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        salt_hex, digest_hex = hashed_password.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (ValueError, TypeError):
        return False
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return hmac.compare_digest(derived, expected)


def create_token(subject: str, expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    header = _base64url_encode(
        json.dumps({"alg": ALGORITHM, "typ": "JWT"}, separators=(",", ":")).encode("utf-8")
    )
    body = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header}.{body}".encode("ascii")
    signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    return f"{header}.{body}.{_base64url_encode(signature)}"


def create_access_token(subject: str) -> str:
    return create_token(
        subject,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "access",
    )


def create_refresh_token(subject: str) -> str:
    return create_token(
        subject,
        timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
        "refresh",
    )


def decode_token(token: str, expected_type: Optional[str] = None) -> Optional[dict[str, Any]]:
    try:
        header, body, signature = token.split(".")
        signing_input = f"{header}.{body}".encode("ascii")
        expected_signature = hmac.new(
            settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256
        ).digest()
        if not hmac.compare_digest(expected_signature, _base64url_decode(signature)):
            return None
        decoded_header = json.loads(_base64url_decode(header))
        if decoded_header.get("alg") != ALGORITHM:
            return None
        payload = json.loads(_base64url_decode(body))
        if not isinstance(payload, dict) or int(payload.get("exp", 0)) <= int(datetime.now(timezone.utc).timestamp()):
            return None
    except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if expected_type and payload.get("type") != expected_type:
        return None
    return payload
