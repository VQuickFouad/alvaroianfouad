from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def _effective_config() -> dict[str, str]:
    executable = shutil.which("sshd")
    if executable:
        result = subprocess.run(
            [executable, "-T"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return {
            key.lower(): value.strip()
            for line in result.stdout.splitlines()
            if len(parts := line.split(None, 1)) == 2
            for key, value in [parts]
        }

    config_file = Path("/etc/ssh/sshd_config")
    if not config_file.is_file():
        return {}
    values = {}
    for line in config_file.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split("#", 1)[0].split(None, 1)
        if len(parts) == 2:
            values[parts[0].lower()] = parts[1].strip()
    return values


class SSHAdapter:
    def audit(self) -> dict:
        config = _effective_config()
        port = int(config.get("port", "22").split()[0])
        root_login = config.get("permitrootlogin", "yes").lower()
        password_auth = config.get("passwordauthentication", "yes").lower()
        pubkey_auth = config.get("pubkeyauthentication", "yes").lower()
        max_auth_tries = int(config.get("maxauthtries", "6").split()[0])
        checks = [
            ("PermitRootLogin", root_login, "no", root_login == "no", "Acceso SSH directo como root deshabilitado"),
            ("PasswordAuthentication", password_auth, "no", password_auth == "no", "Autenticación SSH por contraseña deshabilitada"),
            ("PubkeyAuthentication", pubkey_auth, "yes", pubkey_auth == "yes", "Autenticación por clave pública habilitada"),
            ("Port", str(port), "Puerto no estándar", port != 22, "Puerto SSH distinto del predeterminado"),
            ("MaxAuthTries", str(max_auth_tries), "3 o menos", max_auth_tries <= 3, "Intentos máximos de autenticación limitados"),
        ]
        audit_items = [
            {
                "parameter": name,
                "current_value": current,
                "recommended_value": recommended,
                "compliant": compliant,
                "description": description,
            }
            for name, current, recommended, compliant, description in checks
        ]
        compliant_count = sum(item["compliant"] for item in audit_items)
        score = round(compliant_count * 100 / len(audit_items))
        return {
            "data": {
                "listening_port": port,
                "root_login_allowed": root_login != "no",
                "password_auth_allowed": password_auth == "yes",
                "pubkey_auth_allowed": pubkey_auth == "yes",
                "security_score": score,
                "audit_items": audit_items,
            }
        }


SshAdapter = SSHAdapter
