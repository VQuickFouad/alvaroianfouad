import importlib
from pathlib import Path

import pytest


def test_settings_loads_secrets_from_files(monkeypatch, tmp_path):
    config = importlib.import_module("backend.config")
    secret_file = tmp_path / "restic-password"
    secret_file.write_text("secret-value\n", encoding="utf-8")
    monkeypatch.setenv("RESTIC_PASSWORD_FILE", str(secret_file))
    monkeypatch.setenv("RESTIC_PASSWORD", "")
    config.get_settings.cache_clear()

    try:
        assert config.get_settings().RESTIC_PASSWORD == "secret-value"
    finally:
        config.get_settings.cache_clear()


def test_settings_reports_missing_secret_file(monkeypatch, tmp_path):
    config = importlib.import_module("backend.config")
    monkeypatch.setenv("RESTIC_PASSWORD_FILE", str(tmp_path / "missing-secret"))
    monkeypatch.setenv("RESTIC_PASSWORD", "")
    config.get_settings.cache_clear()

    try:
        with pytest.raises(RuntimeError, match="No se pudo leer"):
            config.get_settings()
    finally:
        config.get_settings.cache_clear()


def test_docker_build_context_excludes_private_deployment_files():
    ignore_rules = (Path(__file__).resolve().parents[1] / ".dockerignore").read_text(encoding="utf-8")

    assert "deploy/docker/secrets" in ignore_rules
    assert "deploy/docker/certs" in ignore_rules
    assert "**/.env.*" in ignore_rules
