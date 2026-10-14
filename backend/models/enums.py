"""
Enumeraciones para el sistema Factorio Tech Solutions.
Define los estados, niveles de severidad y orígenes de datos válidos.
"""
from enum import Enum


class ResponseStatus(str, Enum):
    """Estado general de la respuesta de la API."""
    OK = "ok"
    ERROR = "error"
    DEGRADED = "degraded"


class DataSource(str, Enum):
    """Origen de los datos proporcionados por la plataforma."""
    REAL = "real"
    DEMO = "demo"
    MIXED = "mixed"
    UNAVAILABLE = "unavailable"


class AlertSeverity(str, Enum):
    """Niveles de severidad de las alertas del sistema."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(str, Enum):
    """Estado del ciclo de vida de una alerta."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class ActionStatus(str, Enum):
    """Estado de ejecución de una acción administrativa."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"
    EXPIRED = "expired"


class AllowedActionName(str, Enum):
    """Lista blanca de acciones permitidas en el sistema para evitar ejecución arbitraria."""
    CHECK_DISK = "check_disk"
    CHECK_SERVICES = "check_services"
    RESTART_NGINX = "restart_nginx"
    CLEAR_TEMP = "clear_temp"
    UPDATE_PACKAGES = "update_packages"
    RUN_BACKUP = "run_backup"
    CHECK_FIREWALL = "check_firewall"


class AIProvider(str, Enum):
    """Proveedores de inteligencia artificial admitidos."""
    OPENAI = "openai"
    OLLAMA = "ollama"
    NONE = "none"


class BackupStatus(str, Enum):
    """Estado de una copia de seguridad."""
    SUCCESS = "success"
    FAILED = "failed"
    RUNNING = "running"
    PENDING = "pending"


class ServiceState(str, Enum):
    """Estado de un servicio del sistema monitoreado."""
    RUNNING = "running"
    STOPPED = "stopped"
    UNKNOWN = "unknown"
    NOT_INSTALLED = "not_installed"
