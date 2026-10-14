"""
Modelos ORM de SQLAlchemy para la persistencia en base de datos SQLite.
Define el esquema relacional de alertas, acciones, copias de seguridad y tareas de automatización.
"""
from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Text, Boolean, Integer, Float, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def generate_uuid() -> str:
    """Genera un identificador único en formato cadena."""
    return str(uuid.uuid4())


def get_current_utc() -> datetime:
    """Obtiene la fecha y hora actual en UTC."""
    return datetime.now(timezone.utc)


class AlertModel(Base):
    """
    Modelo de persistencia para alertas de seguridad y métricas del sistema.
    """
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime, default=get_current_utc, nullable=False)
    severity = Column(String(20), nullable=False, default="medium")
    rule_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    evidence = Column(Text, nullable=False, default="{}")  # Almacenado como JSON string
    recommendation = Column(Text, nullable=False, default="")
    status = Column(String(20), nullable=False, default="active")
    source = Column(String(20), nullable=False, default="real")
    created_at = Column(DateTime, default=get_current_utc, nullable=False)
    updated_at = Column(DateTime, default=get_current_utc, onupdate=get_current_utc, nullable=False)

    def to_dict(self) -> dict:
        """Convierte la entidad a un diccionario serializable."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "severity": self.severity,
            "rule_name": self.rule_name,
            "description": self.description,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "status": self.status,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ActionModel(Base):
    """
    Modelo para el seguimiento y auditoría de acciones administrativas controladas.
    """
    __tablename__ = "actions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    action_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    command = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    parameters = Column(Text, nullable=False, default="{}")  # JSON string
    requested_by = Column(String(100), nullable=False, default="operator")
    approved_by = Column(String(100), nullable=True)
    execution_output = Column(Text, nullable=True)
    exit_code = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=get_current_utc, nullable=False)
    executed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        """Convierte la acción a un diccionario."""
        return {
            "id": self.id,
            "action_name": self.action_name,
            "description": self.description,
            "command": self.command,
            "status": self.status,
            "parameters": self.parameters,
            "requested_by": self.requested_by,
            "approved_by": self.approved_by,
            "execution_output": self.execution_output,
            "exit_code": self.exit_code,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class BackupRecordModel(Base):
    """
    Registro histórico de operaciones de backup (por ejemplo, con Restic).
    """
    __tablename__ = "backup_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    snapshot_id = Column(String(64), nullable=True)
    timestamp = Column(DateTime, default=get_current_utc, nullable=False)
    status = Column(String(20), nullable=False, default="success")
    size_bytes = Column(Integer, default=0, nullable=False)
    file_count = Column(Integer, default=0, nullable=False)
    repository = Column(String(255), nullable=False, default="local")
    duration_seconds = Column(Float, default=0.0, nullable=False)
    error_message = Column(Text, nullable=True)
    source = Column(String(20), nullable=False, default="real")

    def to_dict(self) -> dict:
        """Convierte el registro de backup a diccionario."""
        return {
            "id": self.id,
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "status": self.status,
            "size_bytes": self.size_bytes,
            "file_count": self.file_count,
            "repository": self.repository,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
            "source": self.source,
        }


class MetricHistoryModel(Base):
    """Muestras de telemetría persistidas para construir históricos entre reinicios."""
    __tablename__ = "metric_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=get_current_utc, nullable=False, index=True)
    cpu_percent = Column(Float, nullable=False)
    memory_percent = Column(Float, nullable=False)
    disk_percent = Column(Float, nullable=False)
    network_rx_kb = Column(Float, nullable=False)
    network_tx_kb = Column(Float, nullable=False)


class AutomationTaskModel(Base):
    """
    Tareas programadas de mantenimiento y supervisión automática.
    """
    __tablename__ = "automation_tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    cron_expression = Column(String(50), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    last_status = Column(String(20), nullable=True)
    action_name = Column(String(100), nullable=False)
    action_params = Column(Text, nullable=False, default="{}")  # JSON string

    def to_dict(self) -> dict:
        """Convierte la tarea a diccionario."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "cron_expression": self.cron_expression,
            "enabled": self.enabled,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "last_status": self.last_status,
            "action_name": self.action_name,
            "action_params": self.action_params,
        }


class ConfigEntryModel(Base):
    """
    Entradas dinámicas de configuración persistidas en base de datos.
    """
    __tablename__ = "config_entries"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=get_current_utc, onupdate=get_current_utc, nullable=False)

    def to_dict(self) -> dict:
        """Convierte la configuración a diccionario."""
        return {
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UserSessionModel(Base):
    """Sesiones opacas con el token almacenado únicamente como hash."""
    __tablename__ = "user_sessions"

    token_hash = Column(String(64), primary_key=True)
    csrf_hash = Column(String(64), nullable=False)
    username = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=get_current_utc, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)


class AuditLogModel(Base):
    """
    Registro inmutable de auditoría para trazabilidad de eventos críticos.
    """
    __tablename__ = "audit_log"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime, default=get_current_utc, nullable=False)
    action = Column(String(100), nullable=False)
    actor = Column(String(100), nullable=False, default="system")
    details = Column(Text, nullable=False, default="{}")  # JSON string
    ip_address = Column(String(45), nullable=True)

    def to_dict(self) -> dict:
        """Convierte la auditoría a diccionario."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "action": self.action,
            "actor": self.actor,
            "details": self.details,
            "ip_address": self.ip_address,
        }
