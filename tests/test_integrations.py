import importlib
import json
import subprocess

import pytest
from fastapi import HTTPException

from backend.config import Settings


def test_query_loki_maps_streams_and_applies_filters(monkeypatch):
    integrations = importlib.import_module("backend.services.integrations")
    monkeypatch.setattr(
        integrations,
        "get_settings",
        lambda: Settings(LOKI_URL="http://loki.test"),
    )
    captured = {}

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "status": "success",
                "data": {
                    "result": [
                        {
                            "stream": {"service": "nginx", "host": "web-1"},
                            "values": [["1792000000000000000", "ERROR request failed"]],
                        },
                        {
                            "stream": {"service": "ssh"},
                            "values": [["1792000000000000000", "INFO connection accepted"]],
                        },
                    ]
                },
            }

    def mock_get(url, **kwargs):
        captured.update({"url": url, **kwargs})
        return Response()

    monkeypatch.setattr(integrations.httpx, "get", mock_get)

    entries, stats = integrations.query_loki("nginx", "error", "request", 25)

    assert captured["url"] == "http://loki.test/loki/api/v1/query_range"
    assert "request" in captured["params"]["query"]
    assert len(entries) == 1
    assert entries[0]["service"] == "nginx"
    assert entries[0]["severity"] == "error"
    assert stats == {"total": 1, "critical": 0, "error": 1, "warning": 0, "info": 0}


def test_query_loki_rejects_malformed_payload(monkeypatch):
    integrations = importlib.import_module("backend.services.integrations")
    monkeypatch.setattr(integrations, "get_settings", lambda: Settings(LOKI_URL="http://loki.test"))

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"status": "success", "data": {"result": "not-a-list"}}

    monkeypatch.setattr(integrations.httpx, "get", lambda *args, **kwargs: Response())

    with pytest.raises(HTTPException) as error:
        integrations.query_loki(None, None, None, 10)
    assert error.value.status_code == 502


def test_list_restic_backups_calls_fixed_read_only_commands(monkeypatch):
    integrations = importlib.import_module("backend.services.integrations")
    settings = Settings(
        RESTIC_REPOSITORY="/srv/restic",
        RESTIC_PASSWORD="unit-test-password",
        RESTIC_TIMEOUT_SECONDS=17,
    )
    monkeypatch.setattr(integrations, "get_settings", lambda: settings)
    monkeypatch.setattr(integrations.shutil, "which", lambda _: "/usr/bin/restic")
    calls = []

    def mock_run(args, **kwargs):
        calls.append((args, kwargs))
        if args[1] == "snapshots":
            return subprocess.CompletedProcess(
                args,
                0,
                stdout=json.dumps([{"short_id": "abc123", "time": "2026-10-14T18:00:00Z"}]),
                stderr="",
            )
        return subprocess.CompletedProcess(
            args,
            0,
            stdout=json.dumps({"total_size": 2048}),
            stderr="",
        )

    monkeypatch.setattr(integrations.subprocess, "run", mock_run)

    result = integrations.list_restic_backups()

    assert [call[0][1] for call in calls] == ["snapshots", "stats"]
    assert all(call[1]["timeout"] == 17 for call in calls)
    assert all(call[1]["stdin"] == subprocess.DEVNULL for call in calls)
    assert all(call[1]["env"]["RESTIC_PASSWORD"] == "unit-test-password" for call in calls)
    assert result["history"][0]["id"] == "abc123"
    assert result["repository"]["total_snapshots"] == 1


def test_restic_backup_validates_paths_and_uses_argument_vector(monkeypatch, tmp_path):
    integrations = importlib.import_module("backend.services.integrations")
    backup_path = tmp_path / "backup-data"
    backup_path.mkdir()
    settings = Settings(
        RESTIC_REPOSITORY="/srv/restic",
        RESTIC_PASSWORD="unit-test-password",
        RESTIC_BACKUP_PATHS=json.dumps([str(backup_path)]),
    )
    monkeypatch.setattr(integrations, "get_settings", lambda: settings)
    monkeypatch.setattr(integrations.shutil, "which", lambda _: "/usr/bin/restic")
    captured = {}

    def mock_run(args, **kwargs):
        captured.update({"args": args, **kwargs})
        return subprocess.CompletedProcess(
            args,
            0,
            stdout='{"message_type":"summary","snapshot_id":"snapshot-1","data_added":10}\n',
            stderr="",
        )

    monkeypatch.setattr(integrations.subprocess, "run", mock_run)

    output, exit_code = integrations.run_restic_backup()

    assert exit_code == 0
    assert captured["args"][:3] == ["/usr/bin/restic", "backup", "--json"]
    assert captured["args"][3] == "--"
    assert captured["args"][4] == str(backup_path.resolve())
    assert json.loads(output)["snapshot_id"] == "snapshot-1"


def test_restic_backup_rejects_missing_paths_without_running_command(monkeypatch, tmp_path):
    integrations = importlib.import_module("backend.services.integrations")
    settings = Settings(
        RESTIC_REPOSITORY="/srv/restic",
        RESTIC_PASSWORD="unit-test-password",
        RESTIC_BACKUP_PATHS=json.dumps([str(tmp_path / "does-not-exist")]),
    )
    monkeypatch.setattr(integrations, "get_settings", lambda: settings)
    monkeypatch.setattr(integrations.shutil, "which", lambda _: "/usr/bin/restic")

    def unexpected_run(*args, **kwargs):
        pytest.fail("Restic must not run for an invalid backup path.")

    monkeypatch.setattr(integrations.subprocess, "run", unexpected_run)

    with pytest.raises(RuntimeError, match="debe existir y ser absoluta"):
        integrations.run_restic_backup()


def test_action_executor_uses_fixed_systemctl_arguments(monkeypatch):
    executor = importlib.import_module("backend.services.action_executor")
    monkeypatch.setattr(executor.shutil, "which", lambda _: "/usr/bin/systemctl")
    calls = []

    def mock_run(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, stdout="active\n", stderr="")

    monkeypatch.setattr(executor.subprocess, "run", mock_run)

    output, status = executor.execute_action("check_services")

    assert status == 0
    assert json.loads(output) == {
        "nginx": "active",
        "ssh": "active",
        "ufw": "active",
        "fail2ban": "active",
    }
    assert [call[0] for call in calls] == [
        ["/usr/bin/systemctl", "is-active", "nginx"],
        ["/usr/bin/systemctl", "is-active", "ssh"],
        ["/usr/bin/systemctl", "is-active", "ufw"],
        ["/usr/bin/systemctl", "is-active", "fail2ban"],
    ]
    assert all(call[1]["timeout"] == 5 for call in calls)


def test_action_executor_restarts_only_nginx_and_reports_failure(monkeypatch):
    executor = importlib.import_module("backend.services.action_executor")
    monkeypatch.setattr(executor.shutil, "which", lambda _: "/usr/bin/systemctl")
    captured = {}

    def mock_run(args, **kwargs):
        captured.update({"args": args, **kwargs})
        return subprocess.CompletedProcess(args, 5, stdout="", stderr="access denied")

    monkeypatch.setattr(executor.subprocess, "run", mock_run)

    output, status = executor.execute_action("restart_nginx")

    assert captured["args"] == ["/usr/bin/systemctl", "restart", "nginx"]
    assert captured["timeout"] == 30
    assert output == "access denied"
    assert status == 5


def test_action_executor_rejects_unlisted_command_name():
    executor = importlib.import_module("backend.services.action_executor")

    with pytest.raises(NotImplementedError):
        executor.execute_action("systemctl restart ssh; id")
