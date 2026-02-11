from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta

from fastapi import HTTPException, status

from .config import SECRET_KEY, TOKEN_EXPIRE_HOURS


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or hashlib.sha256(SECRET_KEY.encode()).hexdigest()[:16]
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, _ = stored_hash.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt), stored_hash)


def create_token(payload: dict) -> str:
    exp = (datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)).timestamp()
    body = {**payload, "exp": exp}
    raw = json.dumps(body, separators=(",", ":")).encode()
    b64 = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    sig = hmac.new(SECRET_KEY.encode(), b64.encode(), hashlib.sha256).hexdigest()
    return f"{b64}.{sig}"


def decode_token(token: str) -> dict:
    try:
        b64, sig = token.split(".")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    expected = hmac.new(SECRET_KEY.encode(), b64.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    padded = b64 + "=" * (-len(b64) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
    if datetime.utcnow().timestamp() > payload.get("exp", 0):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    return payload
