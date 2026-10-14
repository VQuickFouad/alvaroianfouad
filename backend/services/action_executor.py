from __future__ import annotations

import json
import shutil
import subprocess

import psutil
from backend.services.integrations import run_restic_backup
from backend.services.security_service import SecurityService


def execute_action(action_name: str) -> tuple[str, int]:
    if action_name == "check_disk":
        result = {
            partition.mountpoint: psutil.disk_usage(partition.mountpoint).percent
            for partition in psutil.disk_partitions(all=False)
        }
        return json.dumps(result, ensure_ascii=False), 0

    if action_name == "check_services":
        systemctl = shutil.which("systemctl")
        if systemctl is None:
            raise RuntimeError("systemctl no está disponible en este host.")
        results = {}
        for unit in ("nginx", "ssh", "ufw", "fail2ban"):
            process = subprocess.run(
                [systemctl, "is-active", unit],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            results[unit] = process.stdout.strip() or "unknown"
        return json.dumps(results, ensure_ascii=False), 0

    if action_name == "check_firewall":
        status = SecurityService().get_security_status()
        return json.dumps(status.firewall.model_dump(mode="json"), ensure_ascii=False), 0

    if action_name == "restart_nginx":
        systemctl = shutil.which("systemctl")
        if systemctl is None:
            raise RuntimeError("systemctl no está disponible en este host.")
        process = subprocess.run(
            [systemctl, "restart", "nginx"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        output = (process.stdout + process.stderr).strip()
        return output[:10000] or "systemctl restart nginx completado.", process.returncode

    if action_name == "run_backup":
        return run_restic_backup()

    raise NotImplementedError(
        f"La acción {action_name!r} no está habilitada en el executor restringido."
    )
