"""
Proveedor de datos de demostración sintéticos para Factorio Tech Solutions.
Genera datos realistas para todas las secciones del panel cuando DEMO_MODE=true.
Todos los timestamps son relativos a datetime.now() para mantener la frescura.
"""
import random
import math
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional


class DemoDataProvider:
    """Genera datos sintéticos realistas para modo demostración."""

    # IPs ficticias para datos de demostración
    _DEMO_IPS = [
        "203.0.113.45", "198.51.100.23", "192.0.2.100",
        "203.0.113.78", "198.51.100.55", "192.0.2.201",
        "203.0.113.12", "198.51.100.88",
    ]
    _SERVICES_LIST = [
        {"name": "nginx", "display_name": "Nginx", "description": "Servidor web y proxy inverso"},
        {"name": "sshd", "display_name": "SSH", "description": "Servidor de acceso remoto seguro"},
        {"name": "ufw", "display_name": "UFW", "description": "Cortafuegos Uncomplicated Firewall"},
        {"name": "fail2ban", "display_name": "Fail2ban", "description": "Protección contra fuerza bruta"},
        {"name": "netdata", "display_name": "Netdata", "description": "Monitorización de rendimiento"},
        {"name": "cron", "display_name": "Cron", "description": "Programador de tareas"},
        {"name": "rsyslog", "display_name": "Rsyslog", "description": "Servicio de registros del sistema"},
    ]

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def get_system_metrics() -> dict:
        """Métricas del sistema con variación natural."""
        now = DemoDataProvider._now()
        base_cpu = 32.0 + random.uniform(-8, 12)
        return {
            "cpu": {
                "percent": round(base_cpu, 1),
                "count": 4,
                "load_avg": [round(base_cpu / 25, 2), round(base_cpu / 28, 2), round(base_cpu / 30, 2)],
            },
            "memory": {
                "total_gb": 8.0,
                "used_gb": round(4.8 + random.uniform(-0.5, 0.8), 2),
                "percent": round(62.0 + random.uniform(-5, 8), 1),
            },
            "disk": {
                "total_gb": 80.0,
                "used_gb": 36.2,
                "percent": 45.3,
                "partitions": [
                    {"mount": "/", "total_gb": 80.0, "used_gb": 36.2, "percent": 45.3},
                    {"mount": "/boot", "total_gb": 0.5, "used_gb": 0.18, "percent": 36.0},
                ],
            },
            "network": {
                "bytes_sent": 1_258_000_000 + random.randint(0, 50_000_000),
                "bytes_recv": 3_847_000_000 + random.randint(0, 100_000_000),
                "packets_sent": 842_000 + random.randint(0, 10_000),
                "packets_recv": 1_523_000 + random.randint(0, 20_000),
            },
            "uptime_seconds": 864_000 + random.randint(0, 86_400),  # ~10 días
            "timestamp": now.isoformat(),
        }

    @staticmethod
    def get_metrics_history(range_str: str = "1h") -> list:
        """Serie temporal de métricas con variación sinusoidal natural."""
        now = DemoDataProvider._now()
        ranges = {"1h": (60, 1), "6h": (72, 5), "24h": (96, 15), "7d": (168, 60)}
        points_count, interval_min = ranges.get(range_str, (60, 1))
        points = []
        for i in range(points_count):
            t = now - timedelta(minutes=(points_count - i) * interval_min)
            hour_factor = math.sin(i / points_count * math.pi * 2) * 10
            points.append({
                "timestamp": t.isoformat(),
                "cpu_percent": round(max(5, min(95, 35 + hour_factor + random.uniform(-5, 5))), 1),
                "memory_percent": round(max(30, min(90, 62 + hour_factor * 0.3 + random.uniform(-2, 2))), 1),
                "disk_percent": 45.3,
                "network_rx_kb": round(max(0, 450 + hour_factor * 20 + random.uniform(-50, 50)), 1),
                "network_tx_kb": round(max(0, 180 + hour_factor * 8 + random.uniform(-20, 20)), 1),
            })
        return points

    @staticmethod
    def get_security_status() -> dict:
        """Estado de seguridad con UFW activo, Fail2ban funcionando, SSH bastionado."""
        now = DemoDataProvider._now()
        return {
            "overall_score": 78,
            "firewall": {
                "status": "active",
                "default_incoming": "deny",
                "default_outgoing": "allow",
                "rules": [
                    {"to": "22/tcp", "action": "LIMIT", "from_ip": "Anywhere", "comment": "SSH rate-limited"},
                    {"to": "80/tcp", "action": "ALLOW", "from_ip": "Anywhere", "comment": "HTTP"},
                    {"to": "443/tcp", "action": "ALLOW", "from_ip": "Anywhere", "comment": "HTTPS"},
                    {"to": "19999/tcp", "action": "ALLOW", "from_ip": "192.168.1.0/24", "comment": "Netdata local"},
                ],
            },
            "fail2ban": {
                "running": True,
                "jail_count": 3,
                "jails": [
                    {"jail_name": "sshd", "currently_banned": 2, "total_banned": 47,
                     "banned_ips": ["203.0.113.45", "198.51.100.23"]},
                    {"jail_name": "nginx-http-auth", "currently_banned": 0, "total_banned": 12, "banned_ips": []},
                    {"jail_name": "nginx-botsearch", "currently_banned": 1, "total_banned": 8,
                     "banned_ips": ["192.0.2.100"]},
                ],
            },
            "ssh": {
                "listening_port": 22,
                "root_login_allowed": False,
                "password_auth_allowed": False,
                "pubkey_auth_allowed": True,
                "security_score": 85,
                "audit_items": [
                    {"parameter": "PermitRootLogin", "current_value": "no", "recommended_value": "no",
                     "compliant": True, "description": "Acceso root deshabilitado"},
                    {"parameter": "PasswordAuthentication", "current_value": "no", "recommended_value": "no",
                     "compliant": True, "description": "Autenticación por contraseña deshabilitada"},
                    {"parameter": "PubkeyAuthentication", "current_value": "yes", "recommended_value": "yes",
                     "compliant": True, "description": "Autenticación por clave pública habilitada"},
                    {"parameter": "Port", "current_value": "22", "recommended_value": "2222",
                     "compliant": False, "description": "Se recomienda cambiar el puerto por defecto"},
                    {"parameter": "MaxAuthTries", "current_value": "6", "recommended_value": "3",
                     "compliant": False, "description": "Reducir intentos máximos de autenticación"},
                ],
            },
            "recent_blocked_attempts": [
                {"timestamp": (now - timedelta(minutes=12)).isoformat(), "ip": "203.0.113.45",
                 "service": "sshd", "action": "banned", "country": "CN"},
                {"timestamp": (now - timedelta(minutes=45)).isoformat(), "ip": "198.51.100.23",
                 "service": "sshd", "action": "banned", "country": "RU"},
                {"timestamp": (now - timedelta(hours=2)).isoformat(), "ip": "192.0.2.100",
                 "service": "nginx-botsearch", "action": "banned", "country": "BR"},
            ],
        }

    @staticmethod
    def get_alerts() -> list:
        """Alertas de demostración con diferentes severidades."""
        now = DemoDataProvider._now()
        return [
            {
                "id": "demo-alert-001", "timestamp": (now - timedelta(minutes=5)).isoformat(),
                "severity": "high", "rule_name": "BruteForceDetector",
                "description": "Detectados 12 intentos fallidos de acceso SSH desde 203.0.113.45 en los últimos 5 minutos",
                "evidence": {"ip": "203.0.113.45", "attempts": 12, "period_minutes": 5, "service": "sshd"},
                "recommendation": "La IP ha sido bloqueada por Fail2ban. Verificar que no es un usuario legítimo.",
                "status": "active", "source": "demo",
                "created_at": (now - timedelta(minutes=5)).isoformat(),
                "updated_at": (now - timedelta(minutes=5)).isoformat(),
            },
            {
                "id": "demo-alert-002", "timestamp": (now - timedelta(minutes=30)).isoformat(),
                "severity": "medium", "rule_name": "HighCPUUsage",
                "description": "Uso de CPU por encima del 90% durante más de 5 minutos",
                "evidence": {"cpu_percent": 93.2, "duration_minutes": 7, "top_process": "python3"},
                "recommendation": "Investigar el proceso python3 que consume recursos excesivos.",
                "status": "acknowledged", "source": "demo",
                "created_at": (now - timedelta(minutes=30)).isoformat(),
                "updated_at": (now - timedelta(minutes=25)).isoformat(),
            },
            {
                "id": "demo-alert-003", "timestamp": (now - timedelta(hours=1)).isoformat(),
                "severity": "low", "rule_name": "DiskSpaceWarning",
                "description": "Uso de disco en /var/log alcanza el 75%",
                "evidence": {"partition": "/var/log", "percent": 75, "available_gb": 2.1},
                "recommendation": "Considerar rotar o archivar los registros antiguos.",
                "status": "active", "source": "demo",
                "created_at": (now - timedelta(hours=1)).isoformat(),
                "updated_at": (now - timedelta(hours=1)).isoformat(),
            },
            {
                "id": "demo-alert-004", "timestamp": (now - timedelta(hours=2)).isoformat(),
                "severity": "critical", "rule_name": "ScanPatternDetector",
                "description": "Detectado patrón de escaneo desde 192.0.2.201: 48 solicitudes 404 en 1 minuto",
                "evidence": {"ip": "192.0.2.201", "count_404": 48, "period_seconds": 60,
                             "paths": ["/admin", "/wp-login.php", "/.env", "/phpmyadmin"]},
                "recommendation": "Bloquear la IP y revisar los registros de acceso de Nginx.",
                "status": "resolved", "source": "demo",
                "created_at": (now - timedelta(hours=2)).isoformat(),
                "updated_at": (now - timedelta(hours=1, minutes=30)).isoformat(),
            },
            {
                "id": "demo-alert-005", "timestamp": (now - timedelta(hours=4)).isoformat(),
                "severity": "info", "rule_name": "BackupCompleted",
                "description": "Copia de seguridad completada correctamente",
                "evidence": {"snapshot_id": "abc12345", "size_mb": 245, "duration_seconds": 34},
                "recommendation": "Ninguna acción requerida. Verificar periódicamente la integridad.",
                "status": "resolved", "source": "demo",
                "created_at": (now - timedelta(hours=4)).isoformat(),
                "updated_at": (now - timedelta(hours=4)).isoformat(),
            },
            {
                "id": "demo-alert-006", "timestamp": (now - timedelta(hours=6)).isoformat(),
                "severity": "medium", "rule_name": "HTTP500Spike",
                "description": "Incremento de errores HTTP 500: 15 errores en los últimos 5 minutos",
                "evidence": {"error_count": 15, "period_minutes": 5, "endpoint": "/api/data"},
                "recommendation": "Revisar los registros de Nginx y el estado del backend.",
                "status": "resolved", "source": "demo",
                "created_at": (now - timedelta(hours=6)).isoformat(),
                "updated_at": (now - timedelta(hours=5)).isoformat(),
            },
            {
                "id": "demo-alert-007", "timestamp": (now - timedelta(hours=12)).isoformat(),
                "severity": "high", "rule_name": "ServiceDown",
                "description": "El servicio Netdata no está en ejecución",
                "evidence": {"service": "netdata", "last_seen": (now - timedelta(hours=12, minutes=5)).isoformat()},
                "recommendation": "Reiniciar Netdata: sudo systemctl restart netdata",
                "status": "resolved", "source": "demo",
                "created_at": (now - timedelta(hours=12)).isoformat(),
                "updated_at": (now - timedelta(hours=11)).isoformat(),
            },
            {
                "id": "demo-alert-008", "timestamp": (now - timedelta(days=1)).isoformat(),
                "severity": "medium", "rule_name": "HighMemoryUsage",
                "description": "Uso de memoria RAM por encima del 95% durante 3 minutos",
                "evidence": {"memory_percent": 96.1, "duration_minutes": 3},
                "recommendation": "Identificar procesos con consumo excesivo de memoria.",
                "status": "resolved", "source": "demo",
                "created_at": (now - timedelta(days=1)).isoformat(),
                "updated_at": (now - timedelta(hours=23)).isoformat(),
            },
        ]

    @staticmethod
    def get_services() -> list:
        """Estado de los servicios monitorizados."""
        services = []
        for svc in DemoDataProvider._SERVICES_LIST:
            state = "running"
            pid = random.randint(1000, 65000)
            cpu = round(random.uniform(0.1, 8.0), 1)
            mem = round(random.uniform(0.2, 5.0), 1)
            uptime = 864_000 + random.randint(0, 86_400)
            services.append({
                "name": svc["name"],
                "display_name": svc["display_name"],
                "state": state,
                "pid": pid,
                "cpu_percent": cpu,
                "memory_percent": mem,
                "uptime_seconds": uptime,
                "description": svc["description"],
            })
        return services

    @staticmethod
    def get_logs(service: Optional[str] = None, level: Optional[str] = None,
                 search: Optional[str] = None, limit: int = 50) -> list:
        """Entradas de registro sintéticas realistas."""
        now = DemoDataProvider._now()
        templates = [
            ("sshd", "warning", "Failed password for invalid user admin from 203.0.113.45 port 54321 ssh2"),
            ("sshd", "info", "Accepted publickey for factorio from 192.168.1.10 port 52341 ssh2"),
            ("sshd", "warning", "Connection closed by authenticating user root 198.51.100.23 port 44521 [preauth]"),
            ("nginx", "error", "2024/10/14 12:00:01 [error] 1234#1234: *5678 open() \"/var/www/html/.env\" failed (2: No such file or directory)"),
            ("nginx", "info", "192.168.1.10 - - \"GET / HTTP/1.1\" 200 612 \"-\" \"Mozilla/5.0\""),
            ("nginx", "warning", "192.0.2.201 - - \"GET /wp-login.php HTTP/1.1\" 404 162 \"-\" \"curl/7.68\""),
            ("nginx", "error", "upstream timed out (110: Connection timed out) while connecting to upstream"),
            ("kernel", "info", "UFW BLOCK IN=eth0 OUT= SRC=203.0.113.78 DST=192.168.1.100 PROTO=TCP DPT=3306"),
            ("kernel", "info", "UFW ALLOW IN=eth0 OUT= SRC=192.168.1.10 DST=192.168.1.100 PROTO=TCP DPT=443"),
            ("fail2ban", "info", "Ban 203.0.113.45 [sshd]"),
            ("fail2ban", "info", "Unban 198.51.100.55 [sshd]"),
            ("systemd", "info", "Started Nginx HTTP Server."),
            ("systemd", "info", "Starting Daily apt upgrade and clean activities..."),
            ("systemd", "warning", "netdata.service: Main process exited, code=exited, status=1/FAILURE"),
            ("cron", "info", "CMD (/usr/local/bin/backup.sh)"),
            ("restic", "info", "snapshot abc12345 saved (245.3 MiB added)"),
            ("audit", "info", "USER_AUTH pid=1234 uid=0 auid=1000 msg='op=PAM:authentication acct=\"factorio\" res=success'"),
            ("kernel", "warning", "TCP: request_sock_TCP: Possible SYN flooding on port 443. Sending cookies."),
        ]

        entries = []
        for i in range(min(limit, 100)):
            tmpl = random.choice(templates)
            svc_name, svc_level, msg = tmpl
            if service and svc_name != service:
                continue
            if level and svc_level != level:
                continue
            if search and search.lower() not in msg.lower():
                continue
            t = now - timedelta(minutes=i * random.randint(1, 15), seconds=random.randint(0, 59))
            entries.append({
                "timestamp": t.isoformat(),
                "service": svc_name,
                "level": svc_level,
                "message": msg,
                "raw": f"{t.strftime('%b %d %H:%M:%S')} factorio-srv {svc_name}: {msg}",
            })
        entries.sort(key=lambda x: x["timestamp"], reverse=True)
        return entries[:limit]

    @staticmethod
    def get_backup_summary() -> dict:
        """Resumen de copias de seguridad con historial realista."""
        now = DemoDataProvider._now()
        snapshots = [
            {
                "id": "demo-bk-001", "snapshot_id": "a1b2c3d4",
                "timestamp": (now - timedelta(hours=4)).isoformat(),
                "status": "success", "size_bytes": 257_000_000, "file_count": 12480,
                "repository": "/backup/restic-repo", "duration_seconds": 34.2,
                "error_message": None, "source": "demo",
            },
            {
                "id": "demo-bk-002", "snapshot_id": "e5f6g7h8",
                "timestamp": (now - timedelta(days=1, hours=4)).isoformat(),
                "status": "success", "size_bytes": 255_800_000, "file_count": 12475,
                "repository": "/backup/restic-repo", "duration_seconds": 32.8,
                "error_message": None, "source": "demo",
            },
            {
                "id": "demo-bk-003", "snapshot_id": "i9j0k1l2",
                "timestamp": (now - timedelta(days=2, hours=4)).isoformat(),
                "status": "success", "size_bytes": 254_200_000, "file_count": 12460,
                "repository": "/backup/restic-repo", "duration_seconds": 31.5,
                "error_message": None, "source": "demo",
            },
            {
                "id": "demo-bk-004", "snapshot_id": "m3n4o5p6",
                "timestamp": (now - timedelta(days=3, hours=4)).isoformat(),
                "status": "success", "size_bytes": 252_100_000, "file_count": 12440,
                "repository": "/backup/restic-repo", "duration_seconds": 30.1,
                "error_message": None, "source": "demo",
            },
            {
                "id": "demo-bk-005", "snapshot_id": None,
                "timestamp": (now - timedelta(days=7, hours=4)).isoformat(),
                "status": "failed", "size_bytes": 0, "file_count": 0,
                "repository": "/backup/restic-repo", "duration_seconds": 5.2,
                "error_message": "Fatal: unable to open repository: permission denied",
                "source": "demo",
            },
        ]
        return {
            "configured": True,
            "repository": "/backup/restic-repo",
            "total_snapshots": 4,
            "last_backup_time": snapshots[0]["timestamp"],
            "last_status": "success",
            "total_size_bytes": sum(s["size_bytes"] for s in snapshots if s["status"] == "success"),
            "snapshots": snapshots,
        }

    @staticmethod
    def get_automation_tasks() -> list:
        """Tareas de automatización programadas."""
        now = DemoDataProvider._now()
        return [
            {
                "id": "demo-task-001", "name": "Copia de seguridad diaria",
                "description": "Ejecutar backup incremental con Restic del directorio /var/www y configuraciones",
                "cron_expression": "0 4 * * *", "enabled": True,
                "last_run": (now - timedelta(hours=4)).isoformat(),
                "next_run": (now + timedelta(hours=20)).isoformat(),
                "last_status": "success", "action_name": "run_backup", "action_params": {},
            },
            {
                "id": "demo-task-002", "name": "Verificación de servicios",
                "description": "Comprobar el estado de todos los servicios monitorizados",
                "cron_expression": "*/15 * * * *", "enabled": True,
                "last_run": (now - timedelta(minutes=8)).isoformat(),
                "next_run": (now + timedelta(minutes=7)).isoformat(),
                "last_status": "success", "action_name": "check_services", "action_params": {},
            },
            {
                "id": "demo-task-003", "name": "Verificación de disco",
                "description": "Comprobar el espacio disponible en todas las particiones",
                "cron_expression": "0 */6 * * *", "enabled": True,
                "last_run": (now - timedelta(hours=2)).isoformat(),
                "next_run": (now + timedelta(hours=4)).isoformat(),
                "last_status": "success", "action_name": "check_disk", "action_params": {},
            },
            {
                "id": "demo-task-004", "name": "Limpieza de temporales",
                "description": "Eliminar archivos temporales con más de 7 días de antigüedad",
                "cron_expression": "0 3 * * 0", "enabled": True,
                "last_run": (now - timedelta(days=3)).isoformat(),
                "next_run": (now + timedelta(days=4)).isoformat(),
                "last_status": "success", "action_name": "clear_temp", "action_params": {},
            },
            {
                "id": "demo-task-005", "name": "Actualización de paquetes",
                "description": "Actualizar la lista de paquetes del sistema",
                "cron_expression": "0 2 * * 1", "enabled": False,
                "last_run": (now - timedelta(days=7)).isoformat(),
                "next_run": None,
                "last_status": "success", "action_name": "update_packages", "action_params": {},
            },
        ]

    @staticmethod
    def get_pending_actions() -> list:
        """Acciones pendientes de aprobación."""
        now = DemoDataProvider._now()
        return [
            {
                "id": "demo-action-001", "action_name": "restart_nginx",
                "description": "Reiniciar Nginx para aplicar nueva configuración de seguridad",
                "command": "sudo systemctl restart nginx",
                "status": "pending", "parameters": {},
                "requested_by": "anomaly_detector",
                "approved_by": None, "execution_output": None, "exit_code": None,
                "created_at": (now - timedelta(minutes=15)).isoformat(),
                "executed_at": None,
                "expires_at": (now + timedelta(hours=23, minutes=45)).isoformat(),
            },
            {
                "id": "demo-action-002", "action_name": "clear_temp",
                "description": "Limpiar archivos temporales — disco al 75% en /var/log",
                "command": "find /tmp -type f -mtime +7 -delete",
                "status": "pending", "parameters": {},
                "requested_by": "disk_monitor",
                "approved_by": None, "execution_output": None, "exit_code": None,
                "created_at": (now - timedelta(hours=1)).isoformat(),
                "executed_at": None,
                "expires_at": (now + timedelta(hours=23)).isoformat(),
            },
            {
                "id": "demo-action-003", "action_name": "check_firewall",
                "description": "Verificar reglas del cortafuegos tras detección de escaneo",
                "command": "sudo ufw status verbose",
                "status": "approved", "parameters": {},
                "requested_by": "scan_detector",
                "approved_by": "admin", "execution_output": "Status: active\nDefault: deny (incoming), allow (outgoing)",
                "exit_code": 0,
                "created_at": (now - timedelta(hours=3)).isoformat(),
                "executed_at": (now - timedelta(hours=2, minutes=50)).isoformat(),
                "expires_at": (now + timedelta(hours=21)).isoformat(),
            },
        ]

    @staticmethod
    def get_dashboard_summary() -> dict:
        """Resumen consolidado para el panel de control."""
        metrics = DemoDataProvider.get_system_metrics()
        alerts = DemoDataProvider.get_alerts()
        services = DemoDataProvider.get_services()
        security = DemoDataProvider.get_security_status()
        backups = DemoDataProvider.get_backup_summary()

        active_alerts = [a for a in alerts if a["status"] == "active"]
        running_services = [s for s in services if s["state"] == "running"]

        return {
            "quick_stats": {
                "cpu_percent": metrics["cpu"]["percent"],
                "memory_percent": metrics["memory"]["percent"],
                "disk_percent": metrics["disk"]["percent"],
                "active_alerts_count": len(active_alerts),
                "security_score": security["overall_score"],
                "services_running_count": len(running_services),
                "services_total_count": len(services),
                "last_backup_status": backups["last_status"] or "unknown",
            },
            "recent_alerts": alerts[:5],
            "services": services,
            "system_metrics": metrics,
            "security_summary": security,
            "backup_summary": backups,
        }

    @staticmethod
    def get_ai_analysis(task_type: str, context: dict, user_prompt: str = None) -> dict:
        """Análisis basado en reglas cuando no hay proveedor de IA configurado."""
        analyses = {
            "analyze_events": {
                "summary": "Análisis de eventos del sistema (últimas 24 horas):\n\n"
                           "• Se detectaron 12 intentos de acceso SSH no autorizados desde la IP 203.0.113.45, "
                           "bloqueados correctamente por Fail2ban.\n"
                           "• El uso de CPU alcanzó un pico del 93.2% durante 7 minutos, asociado al proceso python3.\n"
                           "• Se identificó un patrón de escaneo web desde 192.0.2.201 con 48 solicitudes a rutas "
                           "típicas de vulnerabilidades (/wp-login.php, /.env, /phpmyadmin).\n"
                           "• La última copia de seguridad se completó correctamente hace 4 horas.",
                "root_cause_analysis": "Los intentos de fuerza bruta SSH provienen de rangos de IP conocidos por "
                                       "actividad maliciosa. El pico de CPU fue causado probablemente por una tarea "
                                       "de procesamiento puntual. El escaneo web es actividad automatizada de bots.",
                "recommended_actions": [
                    "Mantener Fail2ban activo y considerar aumentar el tiempo de bloqueo",
                    "Investigar el proceso python3 que causó el pico de CPU",
                    "Añadir las IPs de escaneo a la lista de bloqueo permanente de UFW",
                    "Considerar cambiar el puerto SSH del valor por defecto (22)",
                ],
                "confidence_score": 0.85,
            },
            "explain_anomaly": {
                "summary": "La anomalía detectada corresponde a un patrón de reconocimiento automatizado. "
                           "Los 48 errores 404 en 60 segundos desde una única IP indican el uso de herramientas "
                           "como Nikto, dirb o wfuzz para enumerar rutas del servidor web.",
                "root_cause_analysis": "Este tipo de actividad es habitual en la fase de reconocimiento de un "
                                       "posible ataque. Las rutas solicitadas (/admin, /wp-login.php, /.env) son "
                                       "objetivos comunes de escaneos automatizados.",
                "recommended_actions": [
                    "Bloquear la IP 192.0.2.201 en el cortafuegos",
                    "Configurar ModSecurity o CrowdSec para detección automática",
                    "Revisar que no existan archivos sensibles expuestos",
                ],
                "confidence_score": 0.92,
            },
            "recommend_action": {
                "summary": "Basándose en el estado actual del sistema, se recomiendan las siguientes acciones "
                           "de mantenimiento prioritarias.",
                "root_cause_analysis": None,
                "recommended_actions": [
                    "Rotar los registros en /var/log para liberar espacio (uso al 75%)",
                    "Cambiar el puerto SSH del valor por defecto para reducir ataques automatizados",
                    "Programar una verificación de integridad del repositorio de backups",
                    "Reducir MaxAuthTries de SSH de 6 a 3",
                ],
                "confidence_score": 0.78,
            },
            "summarize_logs": {
                "summary": "Resumen de registros del sistema:\n\n"
                           "• Total de eventos analizados: ~150 en las últimas 24 horas\n"
                           "• SSH: 14 intentos fallidos, 8 accesos exitosos con clave pública\n"
                           "• Nginx: 3 errores de upstream timeout, 48 solicitudes 404 sospechosas\n"
                           "• Fail2ban: 3 IPs bloqueadas, 1 desbloqueada tras expiración\n"
                           "• Sistema: Todos los servicios estables excepto reinicio puntual de Netdata",
                "root_cause_analysis": "La actividad registrada es consistente con un servidor web "
                                       "expuesto a Internet con protecciones básicas funcionando correctamente.",
                "recommended_actions": [
                    "Continuar monitorizando los intentos de acceso SSH",
                    "Investigar los timeouts de upstream en Nginx",
                    "Verificar la estabilidad de Netdata",
                ],
                "confidence_score": 0.88,
            },
        }
        result = analyses.get(task_type, analyses["analyze_events"])
        result["provider_used"] = "rule_engine"
        result["model_name"] = "factorio-rules-v1"
        return result
