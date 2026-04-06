import json
import subprocess

from app.services.stitch_service import StitchService


def test_call_tool_runs_node_bridge_with_expected_env(app, monkeypatch):
    captured = {}

    class _Completed:
        returncode = 0
        stdout = json.dumps({"ok": True, "result": {"ok": True}})
        stderr = ""

    def fake_run(command, input, capture_output, text, timeout, env, cwd):
        captured["command"] = command
        captured["input"] = input
        captured["timeout"] = timeout
        captured["env"] = env
        captured["cwd"] = cwd
        return _Completed()

    monkeypatch.setattr("app.services.stitch_service.os.path.exists", lambda path: True)
    monkeypatch.setattr("app.services.stitch_service.subprocess.run", fake_run)
    app.config["STITCH_NODE_BINARY"] = "node"
    app.config["STITCH_BRIDGE_SCRIPT"] = "/tmp/stitch_bridge.mjs"
    app.config["STITCH_API_KEY"] = "sdk-api-key"
    app.config["STITCH_AUTH_TOKEN"] = "oauth-token"
    app.config["STITCH_GCP_PROJECT"] = "gcp-project"
    app.config["STITCH_API_URL"] = "https://stitch.googleapis.com/mcp"

    with app.app_context():
        result = StitchService._call_tool("generate_screen_from_text", {"prompt": "x"})

    assert result == {"ok": True}
    assert captured["command"] == ["node", "/tmp/stitch_bridge.mjs", "generate_screen_from_text"]
    assert json.loads(captured["input"]) == {"prompt": "x"}
    assert captured["timeout"] == 330
    assert captured["env"]["STITCH_API_KEY"] == "sdk-api-key"
    assert captured["env"]["STITCH_ACCESS_TOKEN"] == "oauth-token"
    assert captured["env"]["GOOGLE_CLOUD_PROJECT"] == "gcp-project"
    assert captured["env"]["STITCH_API_URL"] == "https://stitch.googleapis.com/mcp"
    assert captured["cwd"] == "/tmp"


def test_call_tool_surfaces_bridge_error_message(app, monkeypatch):
    class _Completed:
        returncode = 1
        stdout = ""
        stderr = json.dumps({
            "ok": False,
            "error": {
                "code": "AUTH_FAILED",
                "message": "Tool Call Failed [generate_screen_from_text]: invalid authentication credentials",
            },
        })

    monkeypatch.setattr("app.services.stitch_service.os.path.exists", lambda path: True)
    monkeypatch.setattr(
        "app.services.stitch_service.subprocess.run",
        lambda *args, **kwargs: _Completed(),
    )
    app.config["STITCH_BRIDGE_SCRIPT"] = "/tmp/stitch_bridge.mjs"

    with app.app_context():
        try:
            StitchService._call_tool("generate_screen_from_text", {"prompt": "x"})
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "invalid authentication credentials" in str(exc)


def test_call_tool_ignores_noisy_bridge_logs_and_reads_final_json(app, monkeypatch):
    class _Completed:
        returncode = 1
        stdout = ""
        stderr = "\n".join([
            "Stitch Transport Error: TypeError: fetch failed",
            json.dumps({
                "ok": False,
                "error": {
                    "code": "NETWORK_ERROR",
                    "message": "Stitch closed the connection before sending a response.",
                },
            }),
        ])

    monkeypatch.setattr("app.services.stitch_service.os.path.exists", lambda path: True)
    monkeypatch.setattr(
        "app.services.stitch_service.subprocess.run",
        lambda *args, **kwargs: _Completed(),
    )
    app.config["STITCH_BRIDGE_SCRIPT"] = "/tmp/stitch_bridge.mjs"

    with app.app_context():
        try:
            StitchService._call_tool("generate_screen_from_text", {"prompt": "x"})
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert str(exc) == "Stitch closed the connection before sending a response."


def test_call_tool_surfaces_timeout(app, monkeypatch):
    monkeypatch.setattr("app.services.stitch_service.os.path.exists", lambda path: True)

    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="node", timeout=330)

    monkeypatch.setattr("app.services.stitch_service.subprocess.run", raise_timeout)
    app.config["STITCH_BRIDGE_SCRIPT"] = "/tmp/stitch_bridge.mjs"

    with app.app_context():
        try:
            StitchService._call_tool("generate_screen_from_text", {"prompt": "x"})
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert str(exc) == "Stitch request timed out before the SDK returned a response."


def test_call_tool_requires_node_binary(app, monkeypatch):
    monkeypatch.setattr("app.services.stitch_service.os.path.exists", lambda path: True)

    def raise_missing_node(*args, **kwargs):
        raise FileNotFoundError("node not found")

    monkeypatch.setattr("app.services.stitch_service.subprocess.run", raise_missing_node)
    app.config["STITCH_BRIDGE_SCRIPT"] = "/tmp/stitch_bridge.mjs"

    with app.app_context():
        try:
            StitchService._call_tool("generate_screen_from_text", {"prompt": "x"})
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "Node.js is required for Stitch SDK integration" in str(exc)


def test_call_tool_requires_bridge_script(app):
    app.config["STITCH_BRIDGE_SCRIPT"] = "/tmp/missing_bridge.mjs"

    with app.app_context():
        try:
            StitchService._call_tool("generate_screen_from_text", {"prompt": "x"})
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "Stitch bridge script not found" in str(exc)
