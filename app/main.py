from __future__ import annotations

import json
import logging
import os
import platform
import secrets
import socket
import subprocess
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import psutil
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import desc
from starlette.responses import Response

from backend.config import get_settings
from backend.database import SessionLocal, init_db
from backend.demo.demo_data import DemoDataProvider
from backend.models.database_models import (
    ActionModel,
    AlertModel,
    AuditLogModel,
    BackupRecordModel,
    ConfigEntryModel,
)
from backend.services.metrics_service import metrics_service
from backend.services.security_service import security_service
from backend.services.integrations import analyze_with_provider, list_restic_backups, query_loki
from backend.services.action_executor import execute_action
from app.auth import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    admin_is_configured,
    create_session,
    get_session,
    revoke_session,
    setup_admin,
    verify_csrf,
    verify_password,
)

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"
@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Factorio Tech Solutions",
    version="1.0.0",
    description="Panel de gestión, hardening, seguridad y observabilidad para servidores Linux.",
    lifespan=lifespan,
    docs_url="/docs" if get_settings().DEBUG else None,
    redoc_url="/redoc" if get_settings().DEBUG else None,
    openapi_url="/openapi.json" if get_settings().DEBUG else None,
)

_LOGIN_ATTEMPTS: dict[str, list[float]] = {}
_LOGIN_WINDOW_SECONDS = 600
_LOGIN_MAX_ATTEMPTS = 8


@app.middleware("http")
async def protect_api(request: Request, call_next):
    path = request.url.path
    if not path.startswith("/api/") or path in {
        "/api/health",
        "/api/auth/status",
        "/api/auth/setup",
        "/api/auth/login",
    }:
        return await call_next(request)

    session = get_session(request.cookies.get(SESSION_COOKIE))
    if session is None:
        return JSONResponse(status_code=401, content={"detail": "Autenticación requerida."})

    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        csrf_cookie = request.cookies.get(CSRF_COOKIE)
        csrf_header = request.headers.get("x-csrf-token")
        if (
            csrf_cookie is None
            or csrf_header is None
            or not secrets.compare_digest(csrf_cookie, csrf_header)
            or not verify_csrf(session, csrf_header)
        ):
            return JSONResponse(status_code=403, content={"detail": "Validación CSRF fallida."})

    request.state.username = session.username
    return await call_next(request)


def _login_attempt_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _check_login_limit(key: str) -> bool:
    now = time.monotonic()
    attempts = [attempt for attempt in _LOGIN_ATTEMPTS.get(key, []) if now - attempt < _LOGIN_WINDOW_SECONDS]
    _LOGIN_ATTEMPTS[key] = attempts
    return len(attempts) < _LOGIN_MAX_ATTEMPTS


def _record_login_attempt(key: str) -> None:
    _LOGIN_ATTEMPTS.setdefault(key, []).append(time.monotonic())


class SetupRequest(BaseModel):
    setup_token: str = Field(min_length=1, max_length=512)
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=12, max_length=1024)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=1024)


@app.get("/api/auth/status")
def auth_status(request: Request) -> dict[str, Any]:
    session = get_session(request.cookies.get(SESSION_COOKIE))
    return {
        "configured": admin_is_configured(),
        "authenticated": session is not None,
        "username": session.username if session else None,
    }


@app.post("/api/auth/setup", status_code=201)
def auth_setup(payload: SetupRequest) -> dict[str, str]:
    setup_admin(payload.setup_token, payload.username, payload.password)
    return {"status": "configured", "message": "Cuenta administradora creada. Inicia sesión."}


@app.post("/api/auth/login")
def auth_login(payload: LoginRequest, request: Request, response: Response) -> dict[str, str]:
    attempt_key = _login_attempt_key(request)
    if not _check_login_limit(attempt_key):
        raise HTTPException(status_code=429, detail="Demasiados intentos. Espera unos minutos.")
    if not admin_is_configured():
        raise HTTPException(status_code=409, detail="Configura primero la cuenta administradora.")
    if not verify_password(payload.username, payload.password):
        _record_login_attempt(attempt_key)
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")

    _LOGIN_ATTEMPTS.pop(attempt_key, None)
    token, csrf_token, expires_at = create_session(payload.username)
    max_age = int((expires_at - datetime.now(timezone.utc)).total_seconds())
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=max_age,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="strict",
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="strict",
        path="/",
    )
    return {"status": "authenticated", "username": payload.username}


@app.post("/api/auth/logout")
def auth_logout(request: Request, response: Response) -> dict[str, str]:
    revoke_session(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="strict")
    response.delete_cookie(CSRF_COOKIE, path="/", httponly=False, samesite="strict")
    return {"status": "logged_out"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _db_rows(model: Any, limit: int = 100) -> list[Any]:
    sort_column = model.timestamp if hasattr(model, "timestamp") else model.created_at
    with SessionLocal() as db:
        return db.query(model).order_by(desc(sort_column)).limit(limit).all()


def _get_ui_settings() -> dict[str, Any]:
    defaults = {
        "general": {
            "app_name": get_settings().APP_NAME,
            "demo_mode": get_settings().DEMO_MODE,
            "refresh_interval": 30,
        },
        "monitoring": {
            "netdata_url": get_settings().NETDATA_URL,
            "metrics_interval": 5,
            "history_retention_hours": 24,
        },
        "security": {"fail2ban_maxretry": 5, "fail2ban_bantime": 86400},
        "ai": {
            "provider": get_settings().AI_PROVIDER,
            "model": get_settings().AI_MODEL,
            "base_url": get_settings().AI_BASE_URL,
        },
        "backups": {
            "restic_repo_path": get_settings().RESTIC_REPOSITORY,
            "retention_daily": 7,
            "retention_weekly": 4,
            "retention_monthly": 6,
        },
        "notifications": {
            "telegram_enabled": bool(get_settings().TELEGRAM_BOT_TOKEN),
            "telegram_chat_id": "",
            "notify_on_critical": True,
            "notify_on_high": True,
            "notify_on_backup_failure": True,
        },
        "logs": {"retention_days": 30, "sources": []},
    }
    with SessionLocal() as db:
        row = db.query(ConfigEntryModel).filter_by(key="ui_settings").first()
        if row is None:
            return defaults
        try:
            saved = json.loads(row.value)
        except json.JSONDecodeError:
            logger.error("La configuración ui_settings guardada no contiene JSON válido")
            return defaults

    if not isinstance(saved, dict):
        logger.error("La configuración ui_settings guardada debe ser un objeto JSON")
        return defaults
    for section, values in saved.items():
        if section in defaults and isinstance(values, dict):
            defaults[section].update(
                {key: value for key, value in values.items() if key in defaults[section]}
            )
    return defaults


class SettingsUpdate(BaseModel):
    section: str = Field(min_length=1, max_length=40)
    values: dict[str, Any]


@app.get("/api/health")
@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "app": get_settings().APP_NAME,
        "version": app.version,
        "demo_mode": get_settings().DEMO_MODE,
        "timestamp": _now(),
    }


@app.get("/api/system/status")
def system_status() -> dict[str, Any]:
    settings = get_settings()
    if settings.DEMO_MODE:
        metrics = DemoDataProvider.get_system_metrics()
        security = DemoDataProvider.get_security_status()
        backup = DemoDataProvider.get_backup_summary()
        alerts = DemoDataProvider.get_alerts()
        return {
            "demo_mode": True,
            "status": "running",
            "server": {
                "hostname": "factorio-demo",
                "os": "Linux (datos sintéticos)",
                "uptime": "10 días",
                "cpu_percent": metrics["cpu"]["percent"],
                "memory_percent": metrics["memory"]["percent"],
                "disk_percent": metrics["disk"]["percent"],
                "active_alerts": sum(alert["status"] == "active" for alert in alerts),
            },
            "security": {
                "overall_score": security["overall_score"],
                "firewall": security["firewall"]["status"],
                "fail2ban": security["fail2ban"]["running"],
                "ssh_hardened": security["ssh"]["security_score"] >= 80,
            },
            "backup": {
                "last_backup": backup["last_backup_time"],
                "status": backup["last_status"],
                "encrypted": True,
                "repository": backup["repository"],
            },
            "timestamp": _now(),
        }

    metrics = metrics_service.get_metrics()
    security = _as_dict(security_service.get_security_status())
    with SessionLocal() as db:
        active_alerts = db.query(AlertModel).filter_by(status="active").count()
        latest_backup = db.query(BackupRecordModel).order_by(desc(BackupRecordModel.timestamp)).first()
    uptime = metrics.uptime_seconds
    return {
        "demo_mode": False,
        "status": "running",
        "server": {
            "hostname": socket.gethostname(),
            "os": f"{platform.system()} {platform.release()}",
            "uptime": f"{int(uptime // 86400)} días",
            "cpu_percent": metrics.cpu.total_percent,
            "memory_percent": metrics.memory.percent,
            "disk_percent": metrics.disk.root_usage_percent,
            "active_alerts": active_alerts,
        },
        "security": {
            "overall_score": security["overall_score"],
            "firewall": security["firewall"]["status"],
            "fail2ban": security["fail2ban"]["running"],
            "ssh_hardened": security["ssh"]["security_score"] >= 80,
        },
        "backup": {
            "last_backup": latest_backup.timestamp.isoformat() if latest_backup else None,
            "status": latest_backup.status if latest_backup else "unknown",
            "encrypted": None,
            "repository": get_settings().RESTIC_REPOSITORY or None,
        },
        "timestamp": _now(),
    }


@app.get("/api/dashboard")
def dashboard() -> dict[str, Any]:
    if get_settings().DEMO_MODE:
        demo = DemoDataProvider.get_dashboard_summary()
        quick = demo["quick_stats"]
        metrics = demo["system_metrics"]
        backups = demo["backup_summary"]
        services = [
            {
                "name": service["display_name"],
                "status": "running" if service["state"] == "running" else "warning",
                "port": "Interno",
                "uptime": f"{int(service['uptime_seconds'] / 3600)}h",
            }
            for service in demo["services"]
        ]
        return {
            "demo_mode": True,
            "server": {
                "hostname": "factorio-demo",
                "os": "Linux",
                "uptime": "10 días",
                "cpu_percent": quick["cpu_percent"],
                "memory_percent": quick["memory_percent"],
                "disk_percent": quick["disk_percent"],
                "active_alerts": quick["active_alerts_count"],
                "last_backup_time": backups["last_backup_time"],
            },
            "services": services,
            "recent_alerts": demo["recent_alerts"],
            "security_score": quick["security_score"],
            "metrics": metrics,
        }

    status = system_status()
    alerts = _db_rows(AlertModel, 6)
    services = _real_service_status()
    return {
        "demo_mode": False,
        "server": status["server"],
        "services": services,
        "recent_alerts": [_alert_to_dict(alert) for alert in alerts],
        "security_score": status["security"]["overall_score"],
        "metrics": _as_dict(metrics_service.get_metrics()),
    }


def _real_service_status() -> list[dict[str, str]]:
    security = security_service.get_security_status()
    return [
        {"name": "UFW", "status": "running" if security.firewall.status.lower() == "active" else "warning", "port": "Firewall", "uptime": security.firewall.status},
        {"name": "Fail2ban", "status": "running" if security.fail2ban.running else "warning", "port": "Protección de acceso", "uptime": "Estado consultado"},
        {"name": "SSH", "status": "running", "port": str(security.ssh.listening_port), "uptime": "Configuración auditada"},
    ]


@app.get("/api/security")
def security() -> dict[str, Any]:
    if get_settings().DEMO_MODE:
        source = DemoDataProvider.get_security_status()
        checks = source["ssh"]["audit_items"]
        checklist = [
            {
                "id": item["parameter"],
                "label": item["description"],
                "status": "ok" if item["compliant"] else "warning",
                "description": f'{item["parameter"]}: {item["current_value"]}',
            }
            for item in checks
        ]
        events = [
            {
                "severity": "high",
                "timestamp": attempt["timestamp"],
                "type": attempt["service"],
                "source_ip": attempt["ip"],
                "country": "DEMO",
                "action": attempt["action"],
            }
            for attempt in source["recent_blocked_attempts"]
        ]
        return {
            "demo_mode": True,
            "services": [
                {"name": "UFW", "status": "active", "config_summary": "Entrada bloqueada", "last_event": "Datos sintéticos"},
                {"name": "Fail2ban", "status": "active", "config_summary": f'{source["fail2ban"]["jail_count"]} jaulas activas', "last_event": "Datos sintéticos", "banned_ips_count": sum(j["currently_banned"] for j in source["fail2ban"]["jails"])},
                {"name": "SSH", "status": "active", "config_summary": f'Puerto {source["ssh"]["listening_port"]}', "last_event": "Auditoría sintética"},
            ],
            "hardening_checklist": checklist,
            "tls_certificate": None,
            "failed_logins_7d": [],
            "events": events,
            "overall_score": source["overall_score"],
            "alerts": DemoDataProvider.get_alerts()[:5],
        }

    status = _as_dict(security_service.get_security_status())
    checklist = [
        {
            "id": item["parameter"],
            "label": item["description"],
            "status": "ok" if item["compliant"] else "warning",
            "description": f'{item["parameter"]}: {item["current_value"]} (recomendado: {item["recommended_value"]})',
        }
        for item in status["ssh"]["audit_items"]
    ]
    services = [
        {
            "name": "UFW",
            "status": "active" if status["firewall"]["status"].lower() == "active" else "warning",
            "config_summary": f'Default incoming: {status["firewall"]["default_incoming"]}',
            "last_event": "Estado consultado en el host",
        },
        {
            "name": "Fail2ban",
            "status": "active" if status["fail2ban"]["running"] else "warning",
            "config_summary": f'{status["fail2ban"]["jail_count"]} jaulas configuradas',
            "last_event": "Estado consultado en el host",
            "banned_ips_count": sum(jail["currently_banned"] for jail in status["fail2ban"]["jails"]),
        },
        {
            "name": "SSH",
            "status": "active" if status["ssh"]["security_score"] >= 70 else "warning",
            "config_summary": f'Puerto {status["ssh"]["listening_port"]}',
            "last_event": "Configuración auditada",
        },
    ]
    events = [
        {
            "severity": "high",
            "timestamp": attempt["timestamp"],
            "type": attempt.get("jail", "Fail2ban"),
            "source_ip": attempt["ip"],
            "country": "—",
            "action": "Bloqueada",
        }
        for attempt in status["recent_blocked_attempts"]
    ]
    return {
        "demo_mode": False,
        "services": services,
        "hardening_checklist": checklist,
        "tls_certificate": None,
        "failed_logins_7d": [],
        "events": events,
        "overall_score": status["overall_score"],
        "alerts": [],
    }


@app.get("/api/monitoring")
def monitoring(
    range: str = Query(default="1h", pattern="^(1h|6h|24h|7d)$"),
) -> dict[str, Any]:
    if get_settings().DEMO_MODE:
        current = DemoDataProvider.get_system_metrics()
        history = DemoDataProvider.get_metrics_history(range)
        partitions = [
            {
                "mount": part["mount"],
                "total_gb": part["total_gb"],
                "used_gb": part["used_gb"],
                "percent": part["percent"],
            }
            for part in current["disk"]["partitions"]
        ]
        return {
            "demo_mode": True,
            "disk_partitions": partitions,
            "cpu_usage": [
                {"time": point["timestamp"], "value": point["cpu_percent"]}
                for point in history
            ],
            "memory_usage": [
                {"time": point["timestamp"], "percent": point["memory_percent"]}
                for point in history
            ],
            "network_io": [
                {
                    "time": point["timestamp"],
                    "in_mbps": round(point["network_rx_kb"] * 8 / 1024, 3),
                    "out_mbps": round(point["network_tx_kb"] * 8 / 1024, 3),
                }
                for point in history
            ],
            "processes": [],
            "netdata_url": None,
        }

    current = metrics_service.get_metrics()
    history = metrics_service.get_history(range)
    points = history.points[-60:]
    disk_partitions = [
        {
            "mount": partition.mountpoint,
            "total_gb": round(partition.total_bytes / 1024**3, 2),
            "used_gb": round(partition.used_bytes / 1024**3, 2),
            "percent": partition.percent,
        }
        for partition in current.disk.partitions
    ]
    processes = []
    for process in psutil.process_iter(["pid", "name", "username", "status", "memory_percent"]):
        try:
            processes.append(
                {
                    "pid": process.info["pid"],
                    "name": process.info["name"] or "unknown",
                    "user": process.info["username"] or "unknown",
                    "cpu_percent": process.cpu_percent(interval=None),
                    "memory_percent": round(process.info["memory_percent"] or 0.0, 2),
                    "status": process.info["status"] or "unknown",
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    processes.sort(key=lambda process: process["cpu_percent"], reverse=True)
    return {
        "demo_mode": False,
        "disk_partitions": disk_partitions,
        "cpu_usage": [{"time": point.timestamp.isoformat(), "value": point.cpu_percent} for point in points],
        "memory_usage": [{"time": point.timestamp.isoformat(), "percent": point.memory_percent} for point in points],
        "network_io": [
            {
                "time": point.timestamp.isoformat(),
                "in_mbps": round(point.network_rx_kb * 8 / 1024, 3),
                "out_mbps": round(point.network_tx_kb * 8 / 1024, 3),
            }
            for point in points
        ],
        "processes": processes[:10],
        "netdata_url": get_settings().NETDATA_URL or None,
    }


def _alert_to_dict(alert: AlertModel) -> dict[str, Any]:
    try:
        evidence = json.loads(alert.evidence)
    except json.JSONDecodeError:
        evidence = {}
    return {
        "id": alert.id,
        "timestamp": alert.timestamp.isoformat(),
        "severity": alert.severity,
        "rule_name": alert.rule_name,
        "description": alert.description,
        "evidence": evidence,
        "recommendation": alert.recommendation,
        "status": alert.status,
        "source": alert.source,
    }


@app.get("/api/logs")
def logs(
    service: str | None = None,
    level: str | None = None,
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    if get_settings().DEMO_MODE:
        demo_logs = DemoDataProvider.get_logs(
            service=service,
            level=level,
            search=search,
            limit=limit,
        )
        entries = [
            {
                **entry,
                "severity": entry["level"],
                "host": "factorio-demo",
            }
            for entry in demo_logs
        ]
    else:
        entries, stats = query_loki(service, level, search, limit)
        return {"demo_mode": False, "entries": entries, "stats": stats}

    stats = {
        "total": len(entries),
        "critical": sum(entry["severity"] == "critical" for entry in entries),
        "error": sum(entry["severity"] == "error" for entry in entries),
        "warning": sum(entry["severity"] == "warning" for entry in entries),
        "info": sum(entry["severity"] == "info" for entry in entries),
    }
    return {"demo_mode": get_settings().DEMO_MODE, "entries": entries, "stats": stats}


@app.get("/api/backups")
def backups() -> dict[str, Any]:
    if get_settings().DEMO_MODE:
        demo = DemoDataProvider.get_backup_summary()
        return {
            "demo_mode": True,
            "repository": {
                "size": f'{demo["total_size_bytes"] / 1024**3:.1f} GB',
                "total_snapshots": demo["total_snapshots"],
            },
            "integrity": {"status": "demo", "verified": False},
            "history": [
                {
                    "id": item["snapshot_id"] or item["id"],
                    "date": item["timestamp"],
                    "type": "Incremental",
                    "size": f'{item["size_bytes"] / 1024**2:.1f} MB',
                    "duration": f'{item["duration_seconds"]:.1f}s',
                    "status": item["status"],
                }
                for item in demo["snapshots"]
            ],
            "restore_procedure": [],
        }

    return list_restic_backups()


@app.get("/api/automation")
def automation() -> dict[str, Any]:
    if get_settings().DEMO_MODE:
        pending = DemoDataProvider.get_pending_actions()
        tasks = DemoDataProvider.get_automation_tasks()
        pending_actions = [
            {
                "id": item["id"],
                "title": item["action_name"].replace("_", " ").title(),
                "description": item["description"],
                "cause": "Dato sintético de demostración",
                "impact": "La acción no se ejecutará en modo demostración.",
                "steps": [item["command"]],
                "created_at": item["created_at"],
            }
            for item in pending
            if item["status"] == "pending"
        ]
        scheduled_tasks = [
            {
                "id": task["id"],
                "name": task["name"],
                "cron": task["cron_expression"],
                "cron_human": task["description"],
                "last_run": task["last_run"],
                "next_run": task["next_run"],
                "status": "active" if task["enabled"] else "paused",
            }
            for task in tasks
        ]
        history = [
            {
                "id": item["id"],
                "title": item["action_name"].replace("_", " ").title(),
                "status": item["status"],
                "executed_at": item["executed_at"],
                "triggered_by": item["requested_by"],
            }
            for item in pending
            if item["status"] != "pending"
        ]
        return {
            "demo_mode": True,
            "pending_actions": pending_actions,
            "scheduled_tasks": scheduled_tasks,
            "action_history": history,
        }

    with SessionLocal() as db:
        tasks = db.query(ActionModel).filter_by(status="pending").order_by(desc(ActionModel.created_at)).all()
        actions = db.query(ActionModel).order_by(desc(ActionModel.created_at)).limit(100).all()
    return {
        "demo_mode": False,
        "pending_actions": [
            {
                "id": action.id,
                "title": action.action_name,
                "description": action.description,
                "cause": "Pendiente de revisión",
                "impact": "La ejecución requiere un executor seguro configurado.",
                "steps": [],
                "created_at": action.created_at.isoformat(),
            }
            for action in tasks
        ],
        "scheduled_tasks": [],
        "action_history": [
            {
                "id": action.id,
                "title": action.action_name,
                "status": action.status,
                "executed_at": action.executed_at.isoformat() if action.executed_at else None,
                "triggered_by": action.requested_by,
            }
            for action in actions
            if action.status != "pending"
        ],
    }


@app.get("/api/settings")
def settings() -> dict[str, Any]:
    config = _get_ui_settings()
    config["config_source"] = ".env (operativa) + SQLite (preferencias)"
    config["demo_mode"] = get_settings().DEMO_MODE
    return config


@app.post("/api/settings")
def save_settings(payload: SettingsUpdate) -> dict[str, Any]:
    if payload.section not in {
        "general", "monitoring", "security", "ai", "backups", "notifications", "logs"
    }:
        raise HTTPException(status_code=422, detail="Sección de configuración no válida.")

    allowed_fields = {
        "general": {"app_name", "refresh_interval"},
        "monitoring": {"netdata_url", "metrics_interval", "history_retention_hours"},
        "security": {"fail2ban_maxretry", "fail2ban_bantime"},
        "ai": {"provider", "model", "base_url"},
        "backups": {"restic_repo_path", "retention_daily", "retention_weekly", "retention_monthly"},
        "notifications": {
            "telegram_enabled",
            "telegram_chat_id",
            "notify_on_critical",
            "notify_on_high",
            "notify_on_backup_failure",
        },
        "logs": {"retention_days"},
    }
    if not set(payload.values).issubset(allowed_fields[payload.section]):
        raise HTTPException(status_code=422, detail="La sección contiene parámetros no permitidos.")

    integer_bounds = {
        "refresh_interval": (5, 300),
        "metrics_interval": (1, 60),
        "history_retention_hours": (1, 168),
        "fail2ban_maxretry": (1, 20),
        "fail2ban_bantime": (60, 604800),
        "retention_daily": (1, 90),
        "retention_weekly": (1, 52),
        "retention_monthly": (1, 120),
        "retention_days": (1, 365),
    }
    boolean_fields = {
        "telegram_enabled",
        "notify_on_critical",
        "notify_on_high",
        "notify_on_backup_failure",
    }
    url_fields = {"netdata_url", "base_url"}
    validated_values = {}
    for key, value in payload.values.items():
        if key in integer_bounds:
            minimum, maximum = integer_bounds[key]
            if type(value) is not int or not minimum <= value <= maximum:
                raise HTTPException(
                    status_code=422,
                    detail=f"El valor de {key} debe ser un entero entre {minimum} y {maximum}.",
                )
        elif key in boolean_fields:
            if type(value) is not bool:
                raise HTTPException(status_code=422, detail=f"El valor de {key} debe ser booleano.")
        elif key in url_fields:
            if not isinstance(value, str) or len(value) > 2048:
                raise HTTPException(status_code=422, detail=f"El valor de {key} no es una URL válida.")
            if value:
                try:
                    parsed = urlsplit(value)
                except ValueError as exc:
                    raise HTTPException(status_code=422, detail=f"El valor de {key} no es una URL válida.") from exc
                if (
                    parsed.scheme not in {"http", "https"}
                    or not parsed.hostname
                    or parsed.username is not None
                    or parsed.password is not None
                ):
                    raise HTTPException(status_code=422, detail=f"El valor de {key} no es una URL HTTP(S) válida.")
        elif key == "provider":
            if not isinstance(value, str) or value not in {"none", "ollama", "openai"}:
                raise HTTPException(status_code=422, detail="El proveedor de IA no es válido.")
        elif key == "telegram_chat_id":
            if (
                not isinstance(value, str)
                or len(value) > 32
                or (value and not value.removeprefix("-").isdigit())
            ):
                raise HTTPException(status_code=422, detail="El identificador de chat de Telegram no es válido.")
        else:
            max_length = 100 if key == "app_name" else 200 if key == "model" else 1024
            if not isinstance(value, str) or not value.strip() or len(value) > max_length:
                raise HTTPException(status_code=422, detail=f"El valor de {key} no es válido.")
            value = value.strip()
        validated_values[key] = value

    current = _get_ui_settings()
    current[payload.section].update(validated_values)
    with SessionLocal() as db:
        row = db.query(ConfigEntryModel).filter_by(key="ui_settings").first()
        serialized = json.dumps(current, ensure_ascii=False)
        if row is None:
            row = ConfigEntryModel(key="ui_settings", value=serialized, description="Preferencias de la interfaz")
            db.add(row)
        else:
            row.value = serialized
        db.commit()
    return {"success": True, "message": "Preferencias de la interfaz guardadas.", "section": payload.section}


@app.get("/api/ai/status")
def ai_status() -> dict[str, Any]:
    settings = get_settings()
    configured = settings.AI_PROVIDER.lower() in {"ollama", "openai"} and (
        settings.AI_PROVIDER.lower() != "openai" or bool(settings.AI_API_KEY)
    )
    return {
        "demo_mode": settings.DEMO_MODE,
        "provider": "Motor de reglas (demo)" if settings.DEMO_MODE else settings.AI_PROVIDER,
        "model": settings.AI_MODEL,
        "endpoint": settings.AI_BASE_URL if settings.AI_PROVIDER != "none" else None,
        "status": "demo" if settings.DEMO_MODE else ("configured" if configured else "disabled"),
        "last_sync": _now(),
    }


class AIRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)


@app.post("/api/ai/analyze")
@app.post("/api/ai/chat")
def ai_analyze(payload: AIRequest) -> dict[str, Any]:
    if not get_settings().DEMO_MODE:
        return analyze_with_provider(payload.query)
    result = DemoDataProvider.get_ai_analysis(
        task_type="analyze_events",
        context={},
        user_prompt=payload.query,
    )
    return {
        "query": payload.query,
        "provider": "Motor de reglas (demo)",
        "confidence": round(result["confidence_score"] * 100),
        "analysis": result.get("summary", ""),
        "evidence": [],
        "recommendations": result.get("recommended_actions", []),
    }


@app.post("/api/automation/actions/{action_id}/{decision}")
def decide_action(action_id: str, decision: str, request: Request) -> dict[str, Any]:
    if decision not in {"approve", "reject"}:
        raise HTTPException(status_code=404, detail="Decisión no encontrada.")
    if not get_settings().DEMO_MODE:
        with SessionLocal() as db:
            action = db.query(ActionModel).filter_by(id=action_id).first()
            if action is None:
                raise HTTPException(status_code=404, detail="Acción no encontrada.")
            if action.status != "pending":
                raise HTTPException(status_code=409, detail="La acción ya no está pendiente.")
            if action.expires_at:
                expiry = action.expires_at
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                if expiry <= datetime.now(timezone.utc):
                    action.status = "expired"
                    db.commit()
                    raise HTTPException(status_code=409, detail="La acción ha caducado.")

            if decision == "reject":
                action.status = "rejected"
                action.approved_by = request.state.username
                action.executed_at = datetime.now(timezone.utc)
                db.add(
                    AuditLogModel(
                        action="administrative_action_rejected",
                        actor=request.state.username,
                        details=json.dumps({"action_id": action.id, "action_name": action.action_name}),
                    )
                )
                db.commit()
                return {
                    "success": True,
                    "action_id": action.id,
                    "status": "rejected",
                    "message": "Acción rechazada y auditada; no se ejecutó ningún comando.",
                }

            allowed_actions = {
                "check_disk",
                "check_services",
                "check_firewall",
                "restart_nginx",
                "run_backup",
            }
            if action.action_name not in allowed_actions:
                raise HTTPException(
                    status_code=501,
                    detail="Esta acción no está habilitada en el executor restringido.",
                )
            action.approved_by = request.state.username
            try:
                output, exit_code = execute_action(action.action_name)
                action.execution_output = output[:10000]
                action.exit_code = exit_code
                action.executed_at = datetime.now(timezone.utc)
                action.status = "executed" if exit_code == 0 else "failed"
                if action.action_name == "run_backup" and exit_code == 0:
                    summary = json.loads(output)
                    db.add(
                        BackupRecordModel(
                            snapshot_id=summary.get("snapshot_id"),
                            status="success",
                            size_bytes=summary.get("data_added", 0),
                            file_count=summary.get("files_new", 0),
                            repository=get_settings().RESTIC_REPOSITORY,
                            duration_seconds=summary.get("duration_seconds", 0),
                            source="real",
                        )
                    )
            except HTTPException as exc:
                action.status = "failed"
                action.execution_output = str(exc.detail)[:10000]
                action.exit_code = 1
                action.executed_at = datetime.now(timezone.utc)
                db.add(
                    AuditLogModel(
                        action="administrative_action_execution_failed",
                        actor=request.state.username,
                        details=json.dumps(
                            {"action_id": action.id, "action_name": action.action_name, "exit_code": 1}
                        ),
                    )
                )
                db.commit()
                raise
            except (RuntimeError, NotImplementedError, OSError, subprocess.TimeoutExpired) as exc:
                logger.warning("Acción %s no ejecutada: %s", action.action_name, exc)
                action.status = "failed"
                action.execution_output = str(exc)[:10000]
                action.exit_code = 1
                action.executed_at = datetime.now(timezone.utc)
                db.add(
                    AuditLogModel(
                        action="administrative_action_execution_failed",
                        actor=request.state.username,
                        details=json.dumps(
                            {"action_id": action.id, "action_name": action.action_name, "exit_code": 1}
                        ),
                    )
                )
                db.commit()
                raise HTTPException(status_code=503, detail=str(exc)) from exc
            db.add(
                AuditLogModel(
                    action=(
                        "administrative_action_executed"
                        if action.status == "executed"
                        else "administrative_action_execution_failed"
                    ),
                    actor=request.state.username,
                    details=json.dumps(
                        {
                            "action_id": action.id,
                            "action_name": action.action_name,
                            "exit_code": action.exit_code,
                        }
                    ),
                )
            )
            db.commit()
            success = action.status == "executed"
            return {
                "success": success,
                "action_id": action.id,
                "status": action.status,
                "message": "Acción ejecutada." if success else "La acción falló; revisa el resultado auditado.",
            }
    return {
        "success": True,
        "action_id": action_id,
        "status": f"simulated_{decision}",
        "message": "Decisión simulada; no se ejecutó ningún comando.",
    }


@app.get("/")
def root() -> FileResponse:
    index = FRONTEND_DIR / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=404, detail="Frontend no encontrado.")
    return FileResponse(index)


for static_dir_name in ("assets", "css", "js", "img"):
    static_dir = FRONTEND_DIR / static_dir_name
    if static_dir.is_dir():
        app.mount(
            f"/{static_dir_name}",
            StaticFiles(directory=str(static_dir)),
            name=static_dir_name,
        )


@app.get("/{path_name:path}")
def frontend_files(path_name: str) -> FileResponse:
    if path_name.startswith("api/"):
        raise HTTPException(status_code=404, detail="Endpoint no encontrado.")
    root_dir = FRONTEND_DIR.resolve()
    candidate = (root_dir / path_name).resolve()
    if candidate != root_dir and root_dir not in candidate.parents:
        raise HTTPException(status_code=404, detail="Recurso no encontrado.")
    if candidate.is_file():
        return FileResponse(candidate)
    index = root_dir / "index.html"
    if index.is_file():
        return FileResponse(index)
    raise HTTPException(status_code=404, detail="Frontend no encontrado.")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8000")))
