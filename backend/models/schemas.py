"""
Esquemas Pydantic para validación y serialización de peticiones y respuestas de la API.
Garantiza contratos de interfaz consistentes y fuertemente tipados.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field
from .enums import (
    ResponseStatus,
    DataSource,
    AlertSeverity,
    AlertStatus,
    ActionStatus,
    AllowedActionName,
    AIProvider,
    BackupStatus,
    ServiceState,
)

T = TypeVar("T")


def get_current_utc() -> datetime:
    """Función de utilidad para obtener la fecha y hora UTC por defecto."""
    return datetime.now(timezone.utc)


class ApiResponse(BaseModel, Generic[T]):
    """
    Formato estándar para todas las respuestas de la API de Factorio Tech Solutions.
    """
    status: ResponseStatus = Field(default=ResponseStatus.OK, description="Estado general de la operación")
    data: T = Field(description="Cuerpo principal con los datos solicitados")
    source: DataSource = Field(default=DataSource.REAL, description="Origen de los datos: real, demo o mixed")
    timestamp: datetime = Field(default_factory=get_current_utc, description="Marca temporal en formato ISO 8601")
    demo_mode: bool = Field(default=False, description="Indica si el modo demostración está activo")


# --- Adaptadores y Resultados Genéricos ---

class AdapterResult(BaseModel):
    """Estructura normalizada devuelta por todos los adaptadores del sistema."""
    available: bool = Field(description="Indica si el servicio o recurso está disponible en el servidor")
    source: DataSource = Field(description="Fuente del dato: real, demo o unavailable")
    data: Dict[str, Any] = Field(default_factory=dict, description="Información estructurada extraída")
    error: Optional[str] = Field(default=None, description="Mensaje de error si la recolección falló")
    last_updated: datetime = Field(default_factory=get_current_utc, description="Última actualización de la métrica")


# --- Métricas del Sistema ---

class CPUMetrics(BaseModel):
    """Métricas de uso y carga del procesador."""
    total_percent: float
    per_cpu_percent: List[float]
    cores_logical: int
    cores_physical: int
    load_avg: List[float]


class MemoryMetrics(BaseModel):
    """Métricas de consumo de memoria RAM y SWAP."""
    total_bytes: int
    available_bytes: int
    used_bytes: int
    percent: float
    swap_total_bytes: int
    swap_used_bytes: int
    swap_percent: float


class DiskPartitionMetrics(BaseModel):
    """Métricas por partición o punto de montaje."""
    mountpoint: str
    filesystem: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    percent: float


class DiskMetrics(BaseModel):
    """Resumen de almacenamiento de disco."""
    root_usage_percent: float
    total_bytes: int
    used_bytes: int
    free_bytes: int
    partitions: List[DiskPartitionMetrics] = Field(default_factory=list)


class NetworkMetrics(BaseModel):
    """Estadísticas acumuladas de tráfico de red."""
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    errors_in: int = 0
    errors_out: int = 0


class SystemMetrics(BaseModel):
    """Snapshot completo de telemetría del sistema operativo."""
    uptime_seconds: float
    cpu: CPUMetrics
    memory: MemoryMetrics
    disk: DiskMetrics
    network: NetworkMetrics


class MetricHistoryPoint(BaseModel):
    """Punto histórico de series temporales de métricas."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_rx_kb: float
    network_tx_kb: float


class MetricsHistoryResponse(BaseModel):
    """Respuesta del historial de métricas para gráficos."""
    range: str
    points: List[MetricHistoryPoint]


# --- Seguridad ---

class FirewallRule(BaseModel):
    """Regla individual del cortafuegos UFW."""
    to: str
    action: str
    from_ip: str
    comment: Optional[str] = None


class UFWStatus(BaseModel):
    """Estado y reglas de UFW."""
    status: str
    default_incoming: str
    default_outgoing: str
    rules: List[FirewallRule] = Field(default_factory=list)


class Fail2banJailInfo(BaseModel):
    """Información de una jaula de Fail2ban."""
    jail_name: str
    currently_banned: int
    total_banned: int
    banned_ips: List[str] = Field(default_factory=list)


class Fail2banStatus(BaseModel):
    """Estado del servicio Fail2ban."""
    running: bool
    jail_count: int
    jails: List[Fail2banJailInfo] = Field(default_factory=list)


class SSHAuditItem(BaseModel):
    """Comprobación individual de configuración de seguridad SSH."""
    parameter: str
    current_value: str
    recommended_value: str
    compliant: bool
    description: str


class SSHStatus(BaseModel):
    """Auditoría de seguridad del servicio SSH."""
    listening_port: int
    root_login_allowed: bool
    password_auth_allowed: bool
    pubkey_auth_allowed: bool
    security_score: int
    audit_items: List[SSHAuditItem] = Field(default_factory=list)


class SecurityStatusResponse(BaseModel):
    """Visión consolidada de seguridad del host."""
    overall_score: int = Field(ge=0, le=100, description="Puntuación de seguridad entre 0 y 100")
    firewall: UFWStatus
    fail2ban: Fail2banStatus
    ssh: SSHStatus
    recent_blocked_attempts: List[Dict[str, Any]] = Field(default_factory=list)


# --- Alertas ---

class AlertCreate(BaseModel):
    """Esquema para reportar una nueva alerta."""
    severity: AlertSeverity
    rule_name: str
    description: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    recommendation: str = ""


class AlertResponse(BaseModel):
    """Representación de una alerta en la API."""
    id: str
    timestamp: datetime
    severity: AlertSeverity
    rule_name: str
    description: str
    evidence: Dict[str, Any]
    recommendation: str
    status: AlertStatus
    source: DataSource
    created_at: datetime
    updated_at: datetime


class AlertStatusUpdate(BaseModel):
    """Actualización del estado de una alerta."""
    status: AlertStatus


# --- Acciones Administrativas ---

class AllowedActionInfo(BaseModel):
    """Descripción de una acción administrativa disponible en la lista blanca."""
    name: AllowedActionName
    description: str
    category: str
    safe_command: str
    requires_approval: bool = True


class ActionRequestCreate(BaseModel):
    """Petición para solicitar la ejecución de una acción."""
    action_name: AllowedActionName
    parameters: Dict[str, Any] = Field(default_factory=dict)
    reason: Optional[str] = None


class ActionResponse(BaseModel):
    """Detalle de una acción registrada."""
    id: str
    action_name: AllowedActionName
    description: str
    command: str
    status: ActionStatus
    parameters: Dict[str, Any]
    requested_by: str
    approved_by: Optional[str] = None
    execution_output: Optional[str] = None
    exit_code: Optional[int] = None
    created_at: datetime
    executed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class ActionApprovalDecision(BaseModel):
    """Decisión de aprobación o rechazo de una acción."""
    operator: str = "security_lead"
    comment: Optional[str] = None


# --- Copias de Seguridad ---

class BackupRecordResponse(BaseModel):
    """Registro de un snapshot de copia de seguridad."""
    id: str
    snapshot_id: Optional[str]
    timestamp: datetime
    status: BackupStatus
    size_bytes: int
    file_count: int
    repository: str
    duration_seconds: float
    error_message: Optional[str] = None
    source: DataSource


class BackupSummaryResponse(BaseModel):
    """Resumen del subsistema de backups."""
    configured: bool
    repository: str
    total_snapshots: int
    last_backup_time: Optional[datetime] = None
    last_status: Optional[BackupStatus] = None
    total_size_bytes: int = 0
    snapshots: List[BackupRecordResponse] = Field(default_factory=list)


# --- Servicios ---

class ServiceInfo(BaseModel):
    """Estado de un servicio monitoreado."""
    name: str
    display_name: str
    state: ServiceState
    pid: Optional[int] = None
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    uptime_seconds: float = 0.0
    description: str


# --- Tareas de Automatización ---

class AutomationTaskCreate(BaseModel):
    """Creación de una nueva tarea automatizada."""
    name: str
    description: str
    cron_expression: str
    action_name: AllowedActionName
    action_params: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class AutomationTaskResponse(BaseModel):
    """Detalles de una tarea automatizada."""
    id: str
    name: str
    description: str
    cron_expression: str
    enabled: bool
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    last_status: Optional[str] = None
    action_name: str
    action_params: Dict[str, Any]


# --- Inteligencia Artificial ---

class AIAnalysisRequest(BaseModel):
    """Petición de análisis asistido por IA."""
    task_type: str = Field(
        default="analyze_events",
        description="Tipo de análisis: analyze_events, explain_anomaly, recommend_action, summarize_logs"
    )
    context_data: Dict[str, Any] = Field(description="Datos a analizar (métricas, alertas o eventos de log)")
    user_prompt: Optional[str] = Field(default=None, description="Instrucciones adicionales del usuario")


class AIAnalysisResponse(BaseModel):
    """Resultado del análisis cognitivo o de reglas expertas."""
    provider_used: str
    summary: str
    root_cause_analysis: Optional[str] = None
    recommended_actions: List[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.95)
    model_name: Optional[str] = None


# --- Logs ---

class LogEntry(BaseModel):
    """Línea o registro estructurado de log."""
    timestamp: datetime
    service: str
    level: str
    message: str
    raw: str


class LogsResponse(BaseModel):
    """Conjunto de logs recuperados con paginación."""
    total_returned: int
    source_channel: str
    entries: List[LogEntry]


# --- Configuración Dinámica ---

class ConfigItem(BaseModel):
    """Parámetro de configuración."""
    key: str
    value: str
    description: Optional[str] = None
    updated_at: Optional[datetime] = None


class ConfigUpdateRequest(BaseModel):
    """Actualización de múltiples parámetros."""
    entries: Dict[str, str]


# --- Dashboard Consolidado ---

class QuickStats(BaseModel):
    """Resumen ejecutivo para widgets del panel de control."""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    active_alerts_count: int
    security_score: int
    services_running_count: int
    services_total_count: int
    last_backup_status: str


class DashboardSummaryResponse(BaseModel):
    """Resumen completo del estado del servidor para el Dashboard."""
    quick_stats: QuickStats
    recent_alerts: List[AlertResponse]
    services: List[ServiceInfo]
    system_metrics: SystemMetrics
    security_summary: SecurityStatusResponse
    backup_summary: BackupSummaryResponse
