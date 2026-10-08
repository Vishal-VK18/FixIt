import base64
import json
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image
import pytest

import ai_service
import config
import db
import openrouter_client
from ai_service import AIAnalysisError
from openrouter_client import OpenRouterError


def test_config_uses_dotenv_next_to_project_config():
    assert config.ENV_FILE == Path(config.__file__).resolve().parent / ".env"
    assert config.OPENROUTER_MODEL == "openrouter/free"
    assert config.OPENROUTER_TIMEOUT_SECONDS > 0


def _image():
    output = BytesIO()
    Image.new("RGB", (8, 8), "#777").save(output, format="PNG")
    return output.getvalue()


def _install_mock(monkeypatch, handler):
    real_client = httpx.Client

    def mock_client(**kwargs):
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(openrouter_client.httpx, "Client", mock_client)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "test-openrouter-key")


def _response(content, status=200):
    return httpx.Response(status, json={"choices": [{"message": {"content": content}}]})


def _analysis(issue="Damaged classroom chair", category="Furniture", priority="MEDIUM", emergency=False):
    return json.dumps({
        "issue": issue,
        "category": category,
        "priority": priority,
        "department": db.DEPARTMENT_MAP[category],
        "suggested_fix": "Inspect and repair the reported item.",
        "is_emergency": emergency,
    })


def test_success_sends_base64_image_data_url_and_returns_analysis(monkeypatch, caplog):
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["payload"] = json.loads(request.content)
        return _response(_analysis())

    _install_mock(monkeypatch, handler)
    result = ai_service.analyze_image_with_ai(_image(), "image/png")

    data_url = seen["payload"]["messages"][0]["content"][1]["image_url"]["url"]
    assert seen["url"] == openrouter_client.ENDPOINT
    assert seen["auth"] == "Bearer test-openrouter-key"
    assert seen["payload"]["model"] == config.OPENROUTER_MODEL
    assert data_url.startswith("data:image/png;base64,")
    assert base64.b64decode(data_url.split(",", 1)[1]) == _image()
    assert set(result) == {"issue", "category", "priority", "department", "suggested_fix", "is_emergency"}
    assert "test-openrouter-key" not in caplog.text


def test_malformed_json_is_a_clear_analysis_error(monkeypatch):
    _install_mock(monkeypatch, lambda _request: _response("not-json"))
    with pytest.raises(AIAnalysisError, match="malformed JSON"):
        ai_service.analyze_image_with_ai(_image(), "image/png")


def test_unauthorized_response_is_not_retried(monkeypatch):
    calls = 0

    def handler(_request):
        nonlocal calls
        calls += 1
        return httpx.Response(401)

    _install_mock(monkeypatch, handler)
    with pytest.raises(OpenRouterError, match="authentication failed") as err:
        openrouter_client.request_vision("prompt", _image(), "image/png")
    assert err.value.status_code == 401
    assert calls == 1


def test_rate_limit_is_retried_once_then_reported(monkeypatch):
    calls = 0
    delays = []

    def handler(_request):
        nonlocal calls
        calls += 1
        return httpx.Response(429, headers={"Retry-After": "7"})

    _install_mock(monkeypatch, handler)
    monkeypatch.setattr(openrouter_client.time, "sleep", delays.append)
    with pytest.raises(OpenRouterError, match="rate limit") as err:
        openrouter_client.request_vision("prompt", _image(), "image/png")
    assert err.value.status_code == 429
    assert calls == 2
    assert delays == [7.0]


def test_timeout_retries_once_then_returns_timeout(monkeypatch):
    calls = 0

    def handler(_request):
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("simulated read timeout")

    _install_mock(monkeypatch, handler)
    monkeypatch.setattr(openrouter_client.time, "sleep", lambda _delay: None)
    with pytest.raises(OpenRouterError, match="timed out") as err:
        openrouter_client.request_vision("prompt", _image(), "image/png")
    assert err.value.status_code == 504
    assert calls == 2


def test_emergency_classification_forces_critical_priority(monkeypatch):
    _install_mock(monkeypatch, lambda _request: _response(_analysis(
        "Sparks from an exposed live wire", "Electrical", "HIGH", False
    )))
    result = ai_service.analyze_image_with_ai(_image(), "image/png")
    assert result["priority"] == "CRITICAL"
    assert result["is_emergency"] is True


def test_normal_maintenance_classification_is_preserved(monkeypatch):
    _install_mock(monkeypatch, lambda _request: _response(_analysis()))
    result = ai_service.analyze_image_with_ai(_image(), "image/png")
    assert result["category"] == "Furniture"
    assert result["priority"] == "MEDIUM"
    assert result["is_emergency"] is False


def test_image_endpoint_result_submits_through_existing_ticket_route(client, monkeypatch):
    monkeypatch.setattr(ai_service, "request_vision", lambda *_args: _analysis())
    client.post("/api/auth/student/login", json={"email": "student@example.test", "password": client.test_student_password})
    response = client.post("/api/analyze-image", files={"file": ("report.png", _image(), "image/png")})
    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert set(analysis) == {"issue", "category", "priority", "department", "suggested_fix", "is_emergency"}

    submitted = client.post("/api/tickets", json={
        **analysis,
        "block": "Block A",
        "room": "OR-TEST-01",
    })
    assert submitted.status_code == 200
    assert submitted.json()["success"] is True
    assert submitted.json()["ticket"]["issue"] == analysis["issue"]


def test_server_error_is_retried_once(monkeypatch):
    calls = 0

    def handler(_request):
        nonlocal calls
        calls += 1
        return httpx.Response(503)

    _install_mock(monkeypatch, handler)
    monkeypatch.setattr(openrouter_client.time, "sleep", lambda _delay: None)
    with pytest.raises(OpenRouterError, match="temporarily unavailable") as err:
        openrouter_client.request_vision("prompt", _image(), "image/png")
    assert err.value.status_code == 502
    assert calls == 2
