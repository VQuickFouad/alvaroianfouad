import importlib
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.config import Settings
from backend.models.database_models import Base
from app import main


@pytest.fixture
def client(monkeypatch, tmp_path):
    test_settings = Settings(
        DEMO_MODE=True,
        AUTH_SETUP_TOKEN="test-setup-token",
        SESSION_COOKIE_SECURE=False,
    )
    monkeypatch.setattr(main, "get_settings", lambda: test_settings)
    engine = create_engine(
        f"sqlite:///{tmp_path / 'api-tests.sqlite'}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(main, "init_db", lambda: Base.metadata.create_all(bind=engine))
    auth_module = importlib.import_module("app.auth")
    test_session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr(main, "SessionLocal", test_session_factory)
    monkeypatch.setattr(auth_module, "SessionLocal", test_session_factory)
    monkeypatch.setattr(
        importlib.import_module("backend.services.metrics_service"),
        "SessionLocal",
        test_session_factory,
    )
    monkeypatch.setattr(auth_module, "get_settings", lambda: test_settings)
    with TestClient(main.app) as test_client:
        setup = test_client.post(
            "/api/auth/setup",
            json={
                "setup_token": "test-setup-token",
                "username": "admin",
                "password": "correct-horse-battery",
            },
        )
        assert setup.status_code == 201
        login = test_client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "correct-horse-battery"},
        )
        assert login.status_code == 200
        yield test_client
    engine.dispose()


def test_health_endpoint_reports_demo_mode(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["demo_mode"] is True


def test_frontend_and_api_not_found_routes(client):
    assert client.get("/").status_code == 200
    assert client.get("/css/main.css").status_code == 200
    assert client.get("/api/not-a-route").status_code == 404


def test_authentication_session_requires_csrf_for_mutations(client):
    csrf = client.cookies.get("factorio_csrf")
    assert csrf
    client.cookies.delete("factorio_csrf")

    blocked = client.post(
        "/api/automation/actions/demo-action-001/approve",
        json={},
    )
    assert blocked.status_code == 403

    client.cookies.set("factorio_csrf", csrf)
    allowed = client.post(
        "/api/automation/actions/demo-action-001/approve",
        json={},
        headers={"X-CSRF-Token": csrf},
    )
    assert allowed.status_code == 200


def test_auth_status_and_logout_revoke_session(client):
    assert client.get("/api/auth/status").json()["authenticated"] is True
    csrf = client.cookies.get("factorio_csrf")

    response = client.post("/api/auth/logout", json={}, headers={"X-CSRF-Token": csrf})

    assert response.status_code == 200
    assert client.get("/api/auth/status").json()["authenticated"] is False
    assert client.get("/api/dashboard").status_code == 401


def test_frontend_endpoints_match_page_contracts(client):
    dashboard = client.get("/api/dashboard").json()
    security = client.get("/api/security").json()
    monitoring = client.get("/api/monitoring?range=1h").json()
    logs = client.get("/api/logs").json()
    backups = client.get("/api/backups").json()
    automation = client.get("/api/automation").json()

    assert dashboard["demo_mode"] is True
    assert {"server", "services", "recent_alerts"} <= dashboard.keys()
    assert {"services", "hardening_checklist", "events"} <= security.keys()
    assert {"disk_partitions", "cpu_usage", "memory_usage", "network_io", "processes"} <= monitoring.keys()
    assert {"entries", "stats"} <= logs.keys()
    assert {"repository", "integrity", "history", "restore_procedure"} <= backups.keys()
    assert {"pending_actions", "scheduled_tasks", "action_history"} <= automation.keys()


def test_monitoring_rejects_unknown_range(client):
    response = client.get("/api/monitoring?range=forever")

    assert response.status_code == 422


def test_frontend_file_handler_rejects_path_traversal():
    with pytest.raises(main.HTTPException) as error:
        main.frontend_files("../.env")

    assert error.value.status_code == 404


def test_production_action_is_not_claimed_as_executed(client, monkeypatch):
    monkeypatch.setattr(main, "get_settings", lambda: Settings(DEMO_MODE=False))
    with main.SessionLocal() as db:
        db.add(
            main.ActionModel(
                id="action-1",
                action_name="clear_temp",
                description="Unsupported test action",
                command="ignored",
            )
        )
        db.commit()

    csrf = client.cookies.get("factorio_csrf")
    response = client.post(
        "/api/automation/actions/action-1/approve",
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 501
    assert "no está habilitada" in response.json()["detail"]


def test_failed_production_action_is_persisted_and_audited(client, monkeypatch):
    monkeypatch.setattr(main, "get_settings", lambda: Settings(DEMO_MODE=False))

    def fail_action(_):
        raise RuntimeError("restic is not configured")

    monkeypatch.setattr(main, "execute_action", fail_action)
    with main.SessionLocal() as db:
        db.add(
            main.ActionModel(
                id="backup-action",
                action_name="run_backup",
                description="Run configured backup",
                command="ignored",
            )
        )
        db.commit()

    response = client.post(
        "/api/automation/actions/backup-action/approve",
        headers={"X-CSRF-Token": client.cookies.get("factorio_csrf")},
    )

    assert response.status_code == 503
    with main.SessionLocal() as db:
        action = db.query(main.ActionModel).filter_by(id="backup-action").one()
        audit = db.query(main.AuditLogModel).filter_by(action="administrative_action_execution_failed").one()
    assert action.status == "failed"
    assert action.exit_code == 1
    assert audit.actor == "admin"


def test_nonzero_action_exit_code_is_audited_as_failure(client, monkeypatch):
    monkeypatch.setattr(main, "get_settings", lambda: Settings(DEMO_MODE=False))
    monkeypatch.setattr(main, "execute_action", lambda _: ("access denied", 5))
    with main.SessionLocal() as db:
        db.add(
            main.ActionModel(
                id="nginx-restart",
                action_name="restart_nginx",
                description="Restart Nginx",
                command="ignored",
            )
        )
        db.commit()

    response = client.post(
        "/api/automation/actions/nginx-restart/approve",
        headers={"X-CSRF-Token": client.cookies.get("factorio_csrf")},
    )

    assert response.status_code == 200
    assert response.json()["success"] is False
    assert response.json()["status"] == "failed"
    with main.SessionLocal() as db:
        audit = db.query(main.AuditLogModel).filter_by(
            action="administrative_action_execution_failed"
        ).one()
        action = db.query(main.ActionModel).filter_by(id="nginx-restart").one()
    assert "access denied" in action.execution_output
    assert json.loads(audit.details)["exit_code"] == 5


def test_demo_action_response_says_it_was_only_simulated(client):
    csrf = client.cookies.get("factorio_csrf")
    response = client.post(
        "/api/automation/actions/demo-action-001/approve",
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "simulated_approve"
    assert "no se ejecutó ningún comando" in response.json()["message"]


def test_demo_settings_are_persisted_and_only_allowlisted_fields(client):
    response = client.post(
        "/api/settings",
        json={"section": "general", "values": {"app_name": "Lab", "refresh_interval": 45}},
        headers={"X-CSRF-Token": client.cookies.get("factorio_csrf")},
    )

    assert response.status_code == 200
    settings = client.get("/api/settings").json()
    assert settings["general"]["app_name"] == "Lab"
    assert settings["general"]["refresh_interval"] == 45

    rejected = client.post(
        "/api/settings",
        json={"section": "general", "values": {"SECRET_KEY": "should-not-be-saved"}},
        headers={"X-CSRF-Token": client.cookies.get("factorio_csrf")},
    )
    assert rejected.status_code == 422


def test_read_endpoints_work_when_demo_mode_is_disabled(client, monkeypatch):
    production_settings = lambda: Settings(DEMO_MODE=False)
    monkeypatch.setattr(main, "get_settings", production_settings)
    monkeypatch.setattr(
        importlib.import_module("backend.services.metrics_service"),
        "get_settings",
        production_settings,
    )
    monkeypatch.setattr(
        importlib.import_module("backend.services.security_service"),
        "get_settings",
        production_settings,
    )

    paths = [
        "/api/system/status",
        "/api/dashboard",
        "/api/security",
        "/api/monitoring?range=1h",
        "/api/logs",
        "/api/backups",
        "/api/automation",
        "/api/settings",
        "/api/ai/status",
    ]
    responses = [client.get(path) for path in paths]

    assert [response.status_code for response in responses] == [
        200, 200, 200, 200, 503, 503, 200, 200, 200
    ]
    assert all(
        response.json()["demo_mode"] is False
        for path, response in zip(paths, responses)
        if response.status_code == 200
    )


def test_ai_demo_response_matches_frontend_contract(client):
    response = client.post(
        "/api/ai/analyze",
        json={"query": "Resumen de seguridad"},
        headers={"X-CSRF-Token": client.cookies.get("factorio_csrf")},
    )

    assert response.status_code == 200
    assert {"analysis", "confidence", "evidence", "recommendations"} <= response.json().keys()


def test_settings_validate_values_and_accept_notification_toggle(client):
    csrf = client.cookies.get("factorio_csrf")
    saved = client.post(
        "/api/settings",
        json={"section": "notifications", "values": {"telegram_enabled": True}},
        headers={"X-CSRF-Token": csrf},
    )
    assert saved.status_code == 200
    assert client.get("/api/settings").json()["notifications"]["telegram_enabled"] is True

    invalid_number = client.post(
        "/api/settings",
        json={"section": "general", "values": {"refresh_interval": 0}},
        headers={"X-CSRF-Token": csrf},
    )
    invalid_url = client.post(
        "/api/settings",
        json={"section": "ai", "values": {"base_url": "https://user:password@example.com"}},
        headers={"X-CSRF-Token": csrf},
    )
    assert invalid_number.status_code == 422
    assert invalid_url.status_code == 422


def test_ai_sanitizes_prompt_and_authenticates_provider_request(monkeypatch):
    integrations = importlib.import_module("backend.services.integrations")
    settings = Settings(
        DEMO_MODE=False,
        AI_PROVIDER="openai",
        AI_API_KEY="test-api-key-value",
        AI_BASE_URL="https://ai.example/v1",
    )
    monkeypatch.setattr(integrations, "get_settings", lambda: settings)
    captured = {}

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "safe response"}}]}

    def mock_post(url, **kwargs):
        captured.update({"url": url, **kwargs})
        return MockResponse()

    monkeypatch.setattr(integrations.httpx, "post", mock_post)
    prompt = "password=hunter2 contact alice@example.com from 198.51.100.44"
    result = integrations.analyze_with_provider(prompt)

    assert captured["headers"]["Authorization"] == "Bearer test-api-key-value"
    assert "hunter2" not in captured["json"]["messages"][0]["content"]
    assert "alice@example.com" not in captured["json"]["messages"][0]["content"]
    assert "198.51.100.44" not in captured["json"]["messages"][0]["content"]
    assert result["analysis"] == "safe response"


def test_metric_history_is_persisted_between_service_instances(client, monkeypatch):
    metrics_module = importlib.import_module("backend.services.metrics_service")
    monkeypatch.setattr(metrics_module, "get_settings", lambda: Settings(DEMO_MODE=False))
    service = metrics_module.MetricsService()
    service._record_history_point(12.5, 45.0, 60.0, 4.0, 3.0)

    history = metrics_module.MetricsService().get_history("1h")

    assert len(history.points) == 1
    assert history.points[0].cpu_percent == 12.5


def test_metrics_service_normalizes_demo_provider_data(monkeypatch):
    metrics_module = importlib.import_module("backend.services.metrics_service")
    monkeypatch.setattr(metrics_module, "get_settings", lambda: Settings(DEMO_MODE=True))

    metrics = metrics_module.MetricsService().get_metrics()

    assert metrics.cpu.total_percent >= 0
    assert metrics.memory.total_bytes > 0
    assert metrics.disk.total_bytes > 0
