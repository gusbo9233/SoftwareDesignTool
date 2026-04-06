import requests

from app.services.stitch_service import StitchService


def test_call_tool_sends_expected_headers(app, monkeypatch):
    captured = {}

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"result": {"ok": True}}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr("app.services.stitch_service.requests.post", fake_post)
    app.config["STITCH_AUTH_TOKEN"] = "test-token"
    app.config["STITCH_API_URL"] = "https://mcp.stitch.withgoogle.com/v1"

    with app.app_context():
        result = StitchService._call_tool("generate_screen_from_text", {"prompt": "x"})

    assert result == {"ok": True}
    assert captured["url"] == "https://mcp.stitch.withgoogle.com/v1"
    assert captured["headers"]["Authorization"] == "Bearer test-token"
    assert captured["headers"]["User-Agent"].startswith("softwaredesign/")
    assert captured["headers"]["Accept"] == "application/json"
    assert captured["headers"]["Connection"] == "close"
    assert captured["timeout"] == 300


def test_call_tool_surfaces_connection_close_without_retry(app, monkeypatch):
    attempts = {"count": 0}

    def fake_post(url, json, headers, timeout):
        attempts["count"] += 1
        raise requests.exceptions.ConnectionError("connection dropped")

    monkeypatch.setattr("app.services.stitch_service.requests.post", fake_post)

    with app.app_context():
        try:
            StitchService._call_tool("generate_screen_from_text", {"prompt": "x"})
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "closed the connection before sending a response" in str(exc)

    assert attempts["count"] == 1


def test_call_tool_surfaces_http_response_body(app, monkeypatch):
    class _Response:
        status_code = 503
        text = "backend unavailable"

        def raise_for_status(self):
            raise requests.exceptions.HTTPError(response=self)

    monkeypatch.setattr(
        "app.services.stitch_service.requests.post",
        lambda url, json, headers, timeout: _Response(),
    )

    with app.app_context():
        try:
            StitchService._call_tool("generate_screen_from_text", {"prompt": "x"})
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "Stitch HTTP error 503." in str(exc)
            assert "backend unavailable" in str(exc)
