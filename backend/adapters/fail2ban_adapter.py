from __future__ import annotations

import re
import shutil
import subprocess


def _run(executable: str, *args: str) -> str:
    result = subprocess.run(
        [executable, *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    return result.stdout


class Fail2banAdapter:
    def get_status(self) -> dict:
        executable = shutil.which("fail2ban-client")
        if executable is None:
            return {"data": {"running": False, "jails": []}}
        try:
            status = _run(executable, "status")
        except (OSError, subprocess.SubprocessError) as exc:
            raise RuntimeError("No se pudo consultar fail2ban-client.") from exc
        jail_match = re.search(r"Jail list:\s*(.*)", status)
        jail_names = [name.strip() for name in jail_match.group(1).split(",") if name.strip()] if jail_match else []
        jails = []
        for name in jail_names:
            jail_status = _run(executable, "status", name)
            currently_match = re.search(r"Currently banned:\s*(\d+)", jail_status)
            total_match = re.search(r"Total banned:\s*(\d+)", jail_status)
            ips_match = re.search(r" Banned IP list:\s*(.*)", jail_status)
            banned_ips = ips_match.group(1).split() if ips_match else []
            jails.append(
                {
                    "jail_name": name,
                    "currently_banned": int(currently_match.group(1)) if currently_match else len(banned_ips),
                    "total_banned": int(total_match.group(1)) if total_match else 0,
                    "banned_ips": banned_ips,
                }
            )
        return {"data": {"running": True, "jails": jails}}
