from __future__ import annotations

import ipaddress
import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urljoin

import httpx
from fastapi import HTTPException

from backend.config import get_settings

logger = logging.getLogger(__name__)
_PEM_BLOCK = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
    re.DOTALL,
)
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_TOKEN = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{12,}|[A-Fa-f0-9]{32,})\b")
_ASSIGNED_SECRET = re.compile(
    r"(?i)\b(password|passwd|secret|api[_-]?key|token)\s*[:=]\s*([^\s,;]+)"
)
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_IP_CANDIDATE = re.compile(r"(?<![\w:])(?:\d{1,3}\.){3}\d{1,3}(?![\w:])|(?<![\w:])[0-9A-Fa-f:]{3,}(?![\w:])")


def sanitize_prompt(text: str) -> str:
    text = _PEM_BLOCK.sub("[PRIVATE_KEY_REDACTED]", text)
    text = _BEARER.sub("Bearer [REDACTED]", text)
    text = _ASSIGNED_SECRET.sub(lambda match: f"{match.group(1)}=[REDACTED]", text)
    text = _TOKEN.sub("[TOKEN_REDACTED]", text)
    text = _EMAIL.sub("[EMAIL_REDACTED]", text)

    def redact_ip(match: re.Match[str]) -> str:
        candidate = match.group(0)
        try:
            ipaddress.ip_address(candidate)
        except ValueError:
            return candidate
        return "[IP_REDACTED]"

    return _IP_CANDIDATE.sub(redact_ip, text)


def query_loki(
    service: str | None,
    level: str | None,
    search: str | None,
    limit: int,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    settings = get_settings()
    base_url = settings.LOKI_URL.rstrip("/") + "/"
    selector = '{job=~".+"}'
    params: dict[str, str | int] = {
        "query": f"{selector} |= {json.dumps(search)}" if search else selector,
        "limit": limit,
        "direction": "backward",
        "start": str(int((datetime.now(timezone.utc) - timedelta(hours=24)).timestamp() * 1_000_000_000)),
        "end": str(int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)),
    }
    try:
        response = httpx.get(
            urljoin(base_url, "loki/api/v1/query_range"),
            params=params,
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Consulta a Loki fallida: %s", exc)
        raise HTTPException(status_code=503, detail="El servicio de logs Loki no está disponible.") from exc
    if not isinstance(payload, dict) or payload.get("status") != "success":
        raise HTTPException(status_code=502, detail="Loki devolvió una respuesta no válida.")

    data = payload.get("data")
    streams = data.get("result") if isinstance(data, dict) else None
    if not isinstance(streams, list):
        raise HTTPException(status_code=502, detail="Loki devolvió un formato de registros no válido.")

    entries = []
    for stream in streams:
        if not isinstance(stream, dict):
            raise HTTPException(status_code=502, detail="Loki devolvió un formato de registros no válido.")
        labels = stream.get("stream", {})
        values = stream.get("values", [])
        if not isinstance(labels, dict) or not isinstance(values, list):
            raise HTTPException(status_code=502, detail="Loki devolvió un formato de registros no válido.")
        service_name = labels.get("service") or labels.get("job") or "unknown"
        for value in values:
            if not isinstance(value, list) or len(value) != 2:
                raise HTTPException(status_code=502, detail="Loki devolvió un registro con formato no válido.")
            timestamp, raw_message = value
            message = str(raw_message)
            found_level = (labels.get("level") or _detect_level(message)).lower()
            if service and service.lower() not in service_name.lower():
                continue
            if level and level.lower() != found_level:
                continue
            try:
                parsed_time = datetime.fromtimestamp(int(timestamp) / 1_000_000_000, timezone.utc)
            except (TypeError, ValueError, OSError):
                parsed_time = datetime.now(timezone.utc)
            entries.append(
                {
                    "timestamp": parsed_time.isoformat(),
                    "service": service_name,
                    "level": found_level,
                    "severity": found_level,
                    "message": message,
                    "raw": message,
                    "host": labels.get("host", ""),
                }
            )
    entries.sort(key=lambda entry: entry["timestamp"], reverse=True)
    entries = entries[:limit]
    stats = {
        "total": len(entries),
        "critical": sum(entry["severity"] == "critical" for entry in entries),
        "error": sum(entry["severity"] == "error" for entry in entries),
        "warning": sum(entry["severity"] == "warning" for entry in entries),
        "info": sum(entry["severity"] == "info" for entry in entries),
    }
    return entries, stats


def _detect_level(message: str) -> str:
    match = re.search(r"\b(critical|crit|fatal|error|err|warning|warn|info|debug)\b", message, re.I)
    if not match:
        return "info"
    value = match.group(1).lower()
    if value in {"crit", "fatal"}:
        return "critical"
    if value in {"err"}:
        return "error"
    if value == "warn":
        return "warning"
    return value


def _restic_env() -> tuple[str, dict[str, str]]:
    settings = get_settings()
    executable = shutil.which("restic")
    if not settings.RESTIC_REPOSITORY or not settings.RESTIC_PASSWORD or executable is None:
        raise HTTPException(
            status_code=503,
            detail="Restic requiere ejecutable instalado, RESTIC_REPOSITORY y RESTIC_PASSWORD configurados.",
        )
    env = {
        **os.environ,
        "RESTIC_REPOSITORY": settings.RESTIC_REPOSITORY,
        "RESTIC_PASSWORD": settings.RESTIC_PASSWORD,
    }
    return executable, env


def list_restic_backups() -> dict[str, Any]:
    executable, env = _restic_env()
    settings = get_settings()
    started = time.monotonic()
    try:
        snapshots_result = subprocess.run(
            [executable, "snapshots", "--json"],
            check=True,
            capture_output=True,
            text=True,
            timeout=settings.RESTIC_TIMEOUT_SECONDS,
            env=env,
            stdin=subprocess.DEVNULL,
        )
        snapshots = json.loads(snapshots_result.stdout or "[]")
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="La consulta de snapshots Restic superó el tiempo límite.") from exc
    except (subprocess.CalledProcessError, ValueError) as exc:
        logger.error("Restic snapshots falló (código: %s)", getattr(exc, "returncode", "invalid-json"))
        raise HTTPException(status_code=503, detail="No se pudo consultar el repositorio Restic configurado.") from exc

    if not isinstance(snapshots, list) or not all(isinstance(snapshot, dict) for snapshot in snapshots):
        raise HTTPException(status_code=502, detail="Restic devolvió un formato de snapshots no válido.")
    stats: dict[str, Any] = {}
    if snapshots:
        try:
            stats_result = subprocess.run(
                [executable, "stats", "--mode", "raw-data", "--json"],
                check=True,
                capture_output=True,
                text=True,
                timeout=settings.RESTIC_TIMEOUT_SECONDS,
                env=env,
                stdin=subprocess.DEVNULL,
            )
            stats = json.loads(stats_result.stdout or "{}")
            if not isinstance(stats, dict):
                raise HTTPException(status_code=502, detail="Restic devolvió estadísticas con formato no válido.")
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(status_code=504, detail="La consulta de estadísticas Restic superó el tiempo límite.") from exc
        except (subprocess.CalledProcessError, ValueError) as exc:
            logger.error("Restic stats falló (código: %s)", getattr(exc, "returncode", "invalid-json"))
            raise HTTPException(status_code=503, detail="No se pudieron consultar las estadísticas Restic.") from exc

    history = []
    for snapshot in snapshots:
        snapshot_id = snapshot.get("short_id") or snapshot.get("id", "unknown")
        history.append(
            {
                "id": snapshot_id,
                "date": snapshot.get("time"),
                "type": "Snapshot",
                "size": "—",
                "duration": "—",
                "status": "success",
            }
        )
    return {
        "demo_mode": False,
        "repository": {
            "size": _format_bytes(stats.get("total_size")),
            "total_snapshots": len(snapshots),
            "path": settings.RESTIC_REPOSITORY,
        },
        "integrity": {"status": "not_checked", "verified": False},
        "history": history,
        "restore_procedure": [],
        "query_duration_seconds": round(time.monotonic() - started, 3),
    }


def run_restic_backup() -> tuple[str, int]:
    executable, env = _restic_env()
    settings = get_settings()
    try:
        paths = json.loads(settings.RESTIC_BACKUP_PATHS or "[]")
    except json.JSONDecodeError as exc:
        raise RuntimeError("RESTIC_BACKUP_PATHS debe ser una lista JSON de rutas absolutas.") from exc
    if not isinstance(paths, list) or not paths or not all(isinstance(path, str) for path in paths):
        raise RuntimeError("Configura RESTIC_BACKUP_PATHS con una lista JSON no vacía de rutas.")
    resolved_paths = []
    for path in paths:
        candidate = Path(path)
        if not candidate.is_absolute() or not candidate.exists():
            raise RuntimeError("Cada ruta de RESTIC_BACKUP_PATHS debe existir y ser absoluta.")
        resolved_paths.append(str(candidate.resolve()))

    started = time.monotonic()
    try:
        result = subprocess.run(
            [executable, "backup", "--json", "--", *resolved_paths],
            check=False,
            capture_output=True,
            text=True,
            timeout=settings.RESTIC_TIMEOUT_SECONDS,
            env=env,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("La copia Restic superó el tiempo límite configurado.") from exc
    if result.returncode != 0:
        logger.error("Restic backup falló con código %s.", result.returncode)
        return (result.stderr or "Restic backup falló.")[-10000:], result.returncode

    summary = {}
    for line in result.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("message_type") == "summary":
            summary = event
    if not summary or not summary.get("snapshot_id"):
        raise RuntimeError("Restic terminó sin devolver un resumen de snapshot válido.")
    summary["duration_seconds"] = round(time.monotonic() - started, 3)
    return json.dumps(summary, ensure_ascii=False), 0


def _format_bytes(size: int | float | None) -> str:
    if size is None:
        return "No disponible"
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return "No disponible"


def analyze_with_provider(prompt: str) -> dict[str, Any]:
    settings = get_settings()
    provider = settings.AI_PROVIDER.lower()
    if provider not in {"ollama", "openai"}:
        raise HTTPException(status_code=503, detail="No hay proveedor de IA habilitado.")
    sanitized_prompt = sanitize_prompt(prompt)
    try:
        if provider == "ollama":
            endpoint = settings.AI_BASE_URL.rstrip("/")
            if not endpoint.endswith("/api/chat"):
                endpoint += "/api/chat"
            response = httpx.post(
                endpoint,
                json={
                    "model": settings.AI_MODEL,
                    "messages": [{"role": "user", "content": sanitized_prompt}],
                    "stream": False,
                },
                timeout=60,
            )
            response.raise_for_status()
            answer = response.json()["message"]["content"]
        else:
            if not settings.AI_API_KEY:
                raise HTTPException(status_code=503, detail="AI_API_KEY no está configurada.")
            endpoint = settings.AI_BASE_URL.rstrip("/") + "/chat/completions"
            response = httpx.post(
                endpoint,
                headers={"Authorization": f"Bearer {settings.AI_API_KEY}"},
                json={
                    "model": settings.AI_MODEL,
                    "messages": [{"role": "user", "content": sanitized_prompt}],
                    "temperature": 0.2,
                },
                timeout=60,
            )
            response.raise_for_status()
            answer = response.json()["choices"][0]["message"]["content"]
    except HTTPException:
        raise
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
        logger.error("Falló la llamada al proveedor IA %s: %s", provider, exc)
        raise HTTPException(status_code=502, detail="El proveedor de IA no devolvió una respuesta válida.") from exc
    return {
        "query": sanitized_prompt,
        "provider": provider,
        "confidence": 0,
        "analysis": str(answer),
        "evidence": [],
        "recommendations": [],
    }
