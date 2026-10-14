from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from backend.config import get_settings
from backend.database import SessionLocal
from backend.models.database_models import AuditLogModel, ConfigEntryModel, UserSessionModel

SESSION_COOKIE = "factorio_session"
CSRF_COOKIE = "factorio_csrf"
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1


@dataclass(frozen=True)
class SessionIdentity:
    username: str
    csrf_hash: str


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _audit(action: str, username: str, details: dict[str, Any]) -> None:
    with SessionLocal() as db:
        db.add(
            AuditLogModel(
                action=action,
                actor=username,
                details=json.dumps(details, ensure_ascii=False),
            )
        )
        db.commit()


def admin_is_configured() -> bool:
    with SessionLocal() as db:
        return db.query(ConfigEntryModel).filter_by(key="auth_admin").first() is not None


def setup_admin(setup_token: str, username: str, password: str) -> None:
    configured_token = get_settings().AUTH_SETUP_TOKEN
    if not configured_token or not hmac.compare_digest(setup_token, configured_token):
        raise HTTPException(status_code=403, detail="Token de configuración incorrecto.")
    if admin_is_configured():
        raise HTTPException(status_code=409, detail="La cuenta administradora ya está configurada.")
    if not username or len(username) > 100 or not username.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(status_code=422, detail="El nombre de usuario no tiene un formato válido.")
    if len(password) < 12 or len(password) > 1024:
        raise HTTPException(status_code=422, detail="La contraseña debe tener entre 12 y 1024 caracteres.")

    salt = secrets.token_bytes(16)
    password_hash = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=64,
    )
    record = {
        "username": username,
        "salt": salt.hex(),
        "password_hash": password_hash.hex(),
    }
    with SessionLocal() as db:
        db.add(
            ConfigEntryModel(
                key="auth_admin",
                value=json.dumps(record),
                description="Credencial hash de la cuenta administradora",
            )
        )
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail="La cuenta administradora ya está configurada.") from exc
    _audit("admin_setup", username, {})


def _admin_record() -> dict[str, str] | None:
    with SessionLocal() as db:
        row = db.query(ConfigEntryModel).filter_by(key="auth_admin").first()
        if row is None:
            return None
        try:
            record = json.loads(row.value)
        except json.JSONDecodeError as exc:
            raise RuntimeError("La credencial administradora almacenada está dañada.") from exc
    if not all(isinstance(record.get(key), str) for key in ("username", "salt", "password_hash")):
        raise RuntimeError("La credencial administradora almacenada tiene un formato inválido.")
    return record


def verify_password(username: str, password: str) -> bool:
    record = _admin_record()
    if record is None:
        return False
    salt = bytes.fromhex(record["salt"])
    candidate = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=64,
    ).hex()
    return hmac.compare_digest(username, record["username"]) and hmac.compare_digest(
        candidate, record["password_hash"]
    )


def create_session(username: str) -> tuple[str, str, datetime]:
    settings = get_settings()
    token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.SESSION_TTL_HOURS)
    with SessionLocal() as db:
        db.add(
            UserSessionModel(
                token_hash=_hash(token),
                csrf_hash=_hash(csrf_token),
                username=username,
                expires_at=expires_at,
            )
        )
        db.commit()
    _audit("login", username, {})
    return token, csrf_token, expires_at


def get_session(token: str | None) -> SessionIdentity | None:
    if not token:
        return None
    with SessionLocal() as db:
        row = db.query(UserSessionModel).filter_by(token_hash=_hash(token)).first()
        if row is None:
            return None
        expires_at = row.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            db.delete(row)
            db.commit()
            return None
        return SessionIdentity(username=row.username, csrf_hash=row.csrf_hash)


def verify_csrf(session: SessionIdentity, csrf_token: str | None) -> bool:
    return bool(csrf_token and hmac.compare_digest(session.csrf_hash, _hash(csrf_token)))


def revoke_session(token: str | None) -> None:
    if not token:
        return
    with SessionLocal() as db:
        session = db.query(UserSessionModel).filter_by(token_hash=_hash(token)).first()
        if session is None:
            return
        username = session.username
        db.delete(session)
        db.commit()
    _audit("logout", username, {})
