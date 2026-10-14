from __future__ import annotations

import re
import shutil
import subprocess


class UFWAdapter:
    def get_status(self) -> dict:
        executable = shutil.which("ufw")
        if executable is None:
            return {"data": {"status": "No disponible", "rules": []}}
        result = subprocess.run(
            [executable, "status", "verbose"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stdout
        status_match = re.search(r"^Status:\s*(.+)$", output, re.MULTILINE)
        default_match = re.search(r"^Default:\s*(.+)$", output, re.MULTILINE)
        defaults = default_match.group(1).lower().split(",") if default_match else []
        rules = []
        for line in output.splitlines():
            match = re.match(r"^\s*(\S+)\s+(ALLOW|DENY|REJECT|LIMIT)\s+(IN|OUT)\s+(.+?)\s*$", line)
            if match is None:
                continue
            destination, action, _, source = match.groups()
            rules.append(
                {
                    "to": destination,
                    "action": action,
                    "from_ip": source,
                    "comment": None,
                }
            )
        return {
            "data": {
                "status": status_match.group(1) if status_match else "unknown",
                "default_incoming": defaults[0].strip().split()[0] if defaults else "unknown",
                "default_outgoing": defaults[1].strip().split()[0] if len(defaults) > 1 else "unknown",
                "rules": rules,
            }
        }


UfwAdapter = UFWAdapter
