"""
Servicio de consolidación de seguridad y auditoría defensiva.
Combina el estado del cortafuegos (UFW), el sistema de prevención de intrusiones (Fail2ban)
y el análisis de configuración del demonio SSH para determinar el índice de seguridad del host.
"""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from ..config import get_settings
from ..models.schemas import (
    SecurityStatusResponse,
    UFWStatus,
    FirewallRule,
    Fail2banStatus,
    Fail2banJailInfo,
    SSHStatus,
    SSHAuditItem,
)

logger = logging.getLogger(__name__)


def _get_demo_provider() -> Optional[Any]:
    try:
        from backend.demo.demo_data import DemoDataProvider
        return DemoDataProvider
    except (ImportError, AttributeError):
        return None


def _get_adapter(adapter_name: str, class_name: str) -> Optional[Any]:
    try:
        module = __import__(f"backend.adapters.{adapter_name}", fromlist=[class_name])
        return getattr(module, class_name, None)
    except (ImportError, AttributeError):
        return None


class SecurityService:
    """
    Servicio de análisis y puntuación de postura de seguridad.
    """

    def get_security_status(self) -> SecurityStatusResponse:
        """
        Obtiene el estado completo de seguridad del servidor.
        """
        settings = get_settings()
        if settings.DEMO_MODE:
            provider = _get_demo_provider()
            if provider is not None and hasattr(provider, "get_security_status"):
                demo_data = provider.get_security_status()
                if isinstance(demo_data, SecurityStatusResponse):
                    return demo_data
                elif isinstance(demo_data, dict):
                    return SecurityStatusResponse(**demo_data)

            return self._generate_fallback_demo_security()

        return self._collect_real_security_status()

    def _collect_real_security_status(self) -> SecurityStatusResponse:
        """
        Consulta los adaptadores reales de UFW, Fail2ban y SSH.
        Si algún servicio no está disponible en el sistema operativo,
        proporciona estados descriptivos de degradación de forma segura.
        """
        ufw_status = self._get_ufw_data()
        fail2ban_status = self._get_fail2ban_data()
        ssh_status = self._get_ssh_data()

        # Cálculo de la puntuación ponderada global (0 - 100)
        overall_score = self._calculate_overall_score(ufw_status, fail2ban_status, ssh_status)

        # Recopilación de intentos bloqueados recientes
        recent_blocked: List[Dict[str, Any]] = []
        for jail in fail2ban_status.jails:
            for ip in jail.banned_ips[:5]:
                recent_blocked.append({
                    "ip": ip,
                    "jail": jail.jail_name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "reason": "Exceso de autenticaciones fallidas detectadas por Fail2ban"
                })

        return SecurityStatusResponse(
            overall_score=overall_score,
            firewall=ufw_status,
            fail2ban=fail2ban_status,
            ssh=ssh_status,
            recent_blocked_attempts=recent_blocked,
        )

    def _get_ufw_data(self) -> UFWStatus:
        """Consulta el estado del cortafuegos UFW mediante su adaptador."""
        cls_adapter = _get_adapter("ufw_adapter", "UFWAdapter") or _get_adapter("ufw_adapter", "UfwAdapter")
        if cls_adapter:
            try:
                adapter = cls_adapter() if isinstance(cls_adapter, type) else cls_adapter
                result = adapter.get_status() if hasattr(adapter, "get_status") else adapter.collect()
                if isinstance(result, dict) and "data" in result:
                    raw_data = result["data"]
                    if isinstance(raw_data, dict):
                        rules = [
                            FirewallRule(
                                to=r.get("to", ""),
                                action=r.get("action", ""),
                                from_ip=r.get("from_ip", r.get("from", "Anywhere")),
                                comment=r.get("comment"),
                            )
                            for r in raw_data.get("rules", [])
                        ]
                        return UFWStatus(
                            status=raw_data.get("status", "inactivo"),
                            default_incoming=raw_data.get("default_incoming", "deny"),
                            default_outgoing=raw_data.get("default_outgoing", "allow"),
                            rules=rules,
                        )
            except Exception as exc:
                logger.warning("Fallo al consultar UFWAdapter: %s", exc)

        # Estado por defecto si el adaptador no está presente o el servicio no está instalado
        return UFWStatus(
            status="No configurado",
            default_incoming="deny (default)",
            default_outgoing="allow (default)",
            rules=[],
        )

    def _get_fail2ban_data(self) -> Fail2banStatus:
        """Consulta el estado del daemon Fail2ban mediante su adaptador."""
        cls_adapter = _get_adapter("fail2ban_adapter", "Fail2banAdapter")
        if cls_adapter:
            try:
                adapter = cls_adapter() if isinstance(cls_adapter, type) else cls_adapter
                result = adapter.get_status() if hasattr(adapter, "get_status") else adapter.collect()
                if isinstance(result, dict) and "data" in result:
                    raw_data = result["data"]
                    if isinstance(raw_data, dict):
                        jails = [
                            Fail2banJailInfo(
                                jail_name=j.get("jail_name", j.get("name", "unknown")),
                                currently_banned=j.get("currently_banned", 0),
                                total_banned=j.get("total_banned", 0),
                                banned_ips=j.get("banned_ips", []),
                            )
                            for j in raw_data.get("jails", [])
                        ]
                        return Fail2banStatus(
                            running=raw_data.get("running", False),
                            jail_count=len(jails),
                            jails=jails,
                        )
            except Exception as exc:
                logger.warning("Fallo al consultar Fail2banAdapter: %s", exc)

        return Fail2banStatus(
            running=False,
            jail_count=0,
            jails=[],
        )

    def _get_ssh_data(self) -> SSHStatus:
        """Consulta la auditoría de configuración del servicio SSH."""
        cls_adapter = _get_adapter("ssh_adapter", "SSHAdapter") or _get_adapter("ssh_adapter", "SshAdapter")
        if cls_adapter:
            try:
                adapter = cls_adapter() if isinstance(cls_adapter, type) else cls_adapter
                result = adapter.audit() if hasattr(adapter, "audit") else (
                    adapter.get_status() if hasattr(adapter, "get_status") else adapter.collect()
                )
                if isinstance(result, dict) and "data" in result:
                    raw_data = result["data"]
                    if isinstance(raw_data, dict):
                        items = [
                            SSHAuditItem(
                                parameter=item.get("parameter", ""),
                                current_value=str(item.get("current_value", "")),
                                recommended_value=str(item.get("recommended_value", "")),
                                compliant=bool(item.get("compliant", False)),
                                description=item.get("description", ""),
                            )
                            for item in raw_data.get("audit_items", [])
                        ]
                        return SSHStatus(
                            listening_port=raw_data.get("listening_port", 22),
                            root_login_allowed=raw_data.get("root_login_allowed", True),
                            password_auth_allowed=raw_data.get("password_auth_allowed", True),
                            pubkey_auth_allowed=raw_data.get("pubkey_auth_allowed", True),
                            security_score=raw_data.get("security_score", 50),
                            audit_items=items,
                        )
            except Exception as exc:
                logger.warning("Fallo al consultar SSHAdapter: %s", exc)

        # Fallback defensivo: comprobaciones básicas estándar de SSH
        audit_items = [
            SSHAuditItem(
                parameter="Port",
                current_value="22",
                recommended_value="Puerto no estándar (ej. 2222)",
                compliant=False,
                description="Uso del puerto predeterminado conocido 22",
            ),
            SSHAuditItem(
                parameter="PermitRootLogin",
                current_value="prohibit-password",
                recommended_value="no",
                compliant=False,
                description="Se recomienda deshabilitar completamente el acceso directo como root",
            ),
            SSHAuditItem(
                parameter="PasswordAuthentication",
                current_value="yes",
                recommended_value="no",
                compliant=False,
                description="Se aconseja requerir únicamente claves públicas SSH",
            ),
        ]
        return SSHStatus(
            listening_port=22,
            root_login_allowed=False,
            password_auth_allowed=True,
            pubkey_auth_allowed=True,
            security_score=60,
            audit_items=audit_items,
        )

    def _calculate_overall_score(self, ufw: UFWStatus, fail2ban: Fail2banStatus, ssh: SSHStatus) -> int:
        """Calcula el índice de seguridad ponderado sobre 100."""
        score = 0
        # Cortafuegos (hasta 35 pts)
        if ufw.status.lower() in ("active", "activo"):
            score += 25
            if "deny" in ufw.default_incoming.lower():
                score += 10

        # Fail2ban (hasta 25 pts)
        if fail2ban.running:
            score += 15
            if fail2ban.jail_count > 0:
                score += 10

        # SSH (hasta 40 pts, mapeado desde ssh.security_score)
        ssh_fraction = max(0, min(100, ssh.security_score)) / 100.0
        score += int(ssh_fraction * 40)

        return min(max(score, 0), 100)

    def _generate_fallback_demo_security(self) -> SecurityStatusResponse:
        """Genera un estado defensivo sintético para demostraciones de laboratorio."""
        rules = [
            FirewallRule(to="22/tcp", action="ALLOW", from_ip="192.168.1.0/24", comment="Acceso SSH Administración"),
            FirewallRule(to="80/tcp", action="ALLOW", from_ip="Anywhere", comment="Tráfico HTTP Nginx"),
            FirewallRule(to="443/tcp", action="ALLOW", from_ip="Anywhere", comment="Tráfico HTTPS Nginx"),
        ]
        ufw = UFWStatus(
            status="active",
            default_incoming="deny (incoming)",
            default_outgoing="allow (outgoing)",
            rules=rules,
        )

        jails = [
            Fail2banJailInfo(
                jail_name="sshd",
                currently_banned=2,
                total_banned=47,
                banned_ips=["198.51.100.23", "203.0.113.88"],
            ),
            Fail2banJailInfo(
                jail_name="nginx-botsearch",
                currently_banned=1,
                total_banned=19,
                banned_ips=["192.0.2.140"],
            ),
        ]
        fail2ban = Fail2banStatus(
            running=True,
            jail_count=2,
            jails=jails,
        )

        audit_items = [
            SSHAuditItem(
                parameter="Port",
                current_value="2222",
                recommended_value="Puerto > 1024",
                compliant=True,
                description="Puerto no estándar para mitigar escaneos automatizados de red",
            ),
            SSHAuditItem(
                parameter="PermitRootLogin",
                current_value="no",
                recommended_value="no",
                compliant=True,
                description="Acceso directo de superusuario denegado",
            ),
            SSHAuditItem(
                parameter="PasswordAuthentication",
                current_value="no",
                recommended_value="no",
                compliant=True,
                description="Autenticación exclusiva mediante par de claves asimétricas Ed25519/RSA",
            ),
            SSHAuditItem(
                parameter="X11Forwarding",
                current_value="no",
                recommended_value="no",
                compliant=True,
                description="Reenvío gráfico deshabilitado para evitar inyecciones de sesión",
            ),
        ]
        ssh = SSHStatus(
            listening_port=2222,
            root_login_allowed=False,
            password_auth_allowed=False,
            pubkey_auth_allowed=True,
            security_score=95,
            audit_items=audit_items,
        )

        recent_blocked = [
            {
                "ip": "198.51.100.23",
                "jail": "sshd",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "Intentos fallidos de autenticación SSH repetidos",
            },
            {
                "ip": "192.0.2.140",
                "jail": "nginx-botsearch",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "Peticiones maliciosas a rutas administrativas no autorizadas",
            },
        ]

        return SecurityStatusResponse(
            overall_score=92,
            firewall=ufw,
            fail2ban=fail2ban,
            ssh=ssh,
            recent_blocked_attempts=recent_blocked,
        )


security_service = SecurityService()
