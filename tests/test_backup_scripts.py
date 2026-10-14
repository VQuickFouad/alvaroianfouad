import os
import shutil
import sqlite3
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_backup_script_records_restic_snapshot_and_cleans_temporary_dump(tmp_path):
    project = tmp_path / "project"
    scripts = project / "scripts"
    data = project / "data"
    config = project / "config"
    fake_bin = tmp_path / "bin"
    scripts.mkdir(parents=True)
    data.mkdir()
    config.mkdir()
    fake_bin.mkdir()
    shutil.copy(PROJECT_ROOT / "scripts/backup.sh", scripts / "backup.sh")
    (project / ".env").write_text("APP_NAME=test\n", encoding="utf-8")
    with sqlite3.connect(data / "factorio.db"):
        pass
    password_file = tmp_path / "restic-password"
    password_file.write_text("test-password\n", encoding="utf-8")

    restic = fake_bin / "restic"
    restic.write_text(
        """#!/bin/sh
case "$1" in
  snapshots) exit 0 ;;
  backup) printf '%s\\n' '{"message_type":"summary","snapshot_id":"test-snapshot","data_added":42}'; exit 0 ;;
  forget) exit 0 ;;
  *) exit 1 ;;
esac
""",
        encoding="utf-8",
    )
    restic.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}",
        "RESTIC_REPOSITORY": str(tmp_path / "repository"),
        "RESTIC_PASSWORD_FILE": str(password_file),
    }

    result = subprocess.run(
        ["bash", str(scripts / "backup.sh")],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    with sqlite3.connect(data / "factorio.db") as db:
        record = db.execute(
            "SELECT snapshot_id, status, size_bytes FROM backup_records"
        ).fetchone()
    assert record == ("test-snapshot", "success", 42)
    assert not list(data.glob("factorio.dump.db.*"))


def test_restore_script_rejects_destinations_outside_recovery_roots(tmp_path):
    project = tmp_path / "project"
    scripts = project / "scripts"
    data = project / "data"
    fake_bin = tmp_path / "bin"
    scripts.mkdir(parents=True)
    data.mkdir()
    fake_bin.mkdir()
    shutil.copy(PROJECT_ROOT / "scripts/restore.sh", scripts / "restore.sh")
    (project / ".env").write_text(
        "RESTIC_REPOSITORY=/tmp/test-repository\nRESTIC_PASSWORD=test-password\n",
        encoding="utf-8",
    )
    restic = fake_bin / "restic"
    restic.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    restic.chmod(0o755)
    target = Path(f"/etc/factorio-restore-test-{os.getpid()}")
    env = {**os.environ, "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}"}

    result = subprocess.run(
        ["bash", str(scripts / "restore.sh"), "latest", str(target)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode != 0
    assert "El destino debe estar dentro" in result.stderr
    assert not target.exists()


def test_integration_smoke_check_requires_repository_credentials():
    result = subprocess.run(
        ["bash", str(PROJECT_ROOT / "scripts/smoke-integrations.sh")],
        capture_output=True,
        text=True,
        env={
            "PATH": os.environ.get("PATH", ""),
            "LOKI_URL": "http://loki.test",
            "RESTIC_REPOSITORY": "",
            "RESTIC_PASSWORD": "",
        },
        check=False,
    )

    assert result.returncode != 0
    assert "RESTIC_REPOSITORY y RESTIC_PASSWORD" in result.stderr


def test_integration_smoke_check_reads_password_file_and_uses_read_commands(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    password_file = tmp_path / "restic-password"
    password_file.write_text("smoke-test-password\n", encoding="utf-8")
    restic = fake_bin / "restic"
    restic.write_text(
        '#!/bin/sh\n[ "$1" = "snapshots" ] && [ "$2" = "--json" ] && '
        '[ "$RESTIC_PASSWORD" = "smoke-test-password" ]\n',
        encoding="utf-8",
    )
    restic.chmod(0o755)
    curl = fake_bin / "curl"
    curl.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    curl.chmod(0o755)

    result = subprocess.run(
        ["bash", str(PROJECT_ROOT / "scripts/smoke-integrations.sh")],
        capture_output=True,
        text=True,
        env={
            "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}",
            "LOKI_URL": "http://loki.test",
            "RESTIC_REPOSITORY": "/srv/restic",
            "RESTIC_PASSWORD_FILE": str(password_file),
        },
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Loki responde a consultas" in result.stdout
    assert "Restic pudo leer" in result.stdout
    assert "smoke-test-password" not in result.stdout + result.stderr
