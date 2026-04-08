from types import SimpleNamespace

from app.services.project_service import ProjectServiceUnavailableError
from app.services.screen_service import ScreenService


class _DeferredExecutor:
    def __init__(self):
        self.calls = []

    def submit(self, fn, *args, **kwargs):
        self.calls.append((fn, args, kwargs))
        return SimpleNamespace()


def test_generate_screen_starts_background_job(client, project, monkeypatch):
    import app.routes.screens as screens_module

    executor = _DeferredExecutor()
    monkeypatch.setattr(screens_module, "_GENERATION_EXECUTOR", executor)

    response = client.post(
        f"/projects/{project.id}/screens/generate",
        data={
            "prompt": "Create a dashboard screen",
            "name": "Dashboard",
            "device_type": "DESKTOP",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    screens = ScreenService.get_all_for_project(project.id)
    assert len(screens) == 1
    screen = screens[0]
    assert screen.name == "Dashboard"
    assert screen.data["generation_status"] == "queued"
    assert screen.data["prompt"] == "Create a dashboard screen"
    assert len(executor.calls) == 1
    assert f"/projects/{project.id}/screens/{screen.id}" in response.headers["Location"]


def test_background_generation_updates_screen_on_success(app, project, monkeypatch):
    import app.routes.screens as screens_module

    screen = ScreenService.create(
        project_id=project.id,
        name="Dashboard",
        device_type="desktop",
        description="Generated from prompt: Create a dashboard screen",
        data={
            "prompt": "Create a dashboard screen",
            "generation_status": "queued",
            "generation_error": "",
        },
    )

    monkeypatch.setattr(
        screens_module.StitchService,
        "create_project",
        lambda title="": {"content": [{"type": "text", "text": '{"projectId":"stitch-project"}'}]},
    )
    monkeypatch.setattr(
        screens_module.StitchService,
        "generate_screen",
        lambda **kwargs: {
            "content": [
                {
                    "type": "text",
                    "text": '{"screenId":"screen-123","html":"<div>hello</div>","imageUrl":"https://example.com/screen.png"}',
                }
            ]
        },
    )
    monkeypatch.setattr(screens_module.StitchService, "list_screens", lambda project_id: [])

    screens_module._run_screen_generation(
        app,
        project.id,
        screen.id,
        "Create a dashboard screen",
        "DESKTOP",
        "",
    )

    updated = ScreenService.get(screen.id)
    assert updated.data["generation_status"] == "completed"
    assert updated.data["stitch_project_id"] == "stitch-project"
    assert updated.data["stitch_screen_id"] == "screen-123"
    assert updated.data["html"] == "<div>hello</div>"
    assert updated.data["image_url"] == "https://example.com/screen.png"
    assert updated.data["generation_error"] == ""
    assert len(updated.data["materials"]) == 2
    assert updated.data["materials"][0]["id"] == "screen-html"


def test_background_generation_updates_screen_on_sdk_structured_success(app, project, monkeypatch):
    import app.routes.screens as screens_module

    screen = ScreenService.create(
        project_id=project.id,
        name="Dashboard",
        device_type="desktop",
        description="Generated from prompt: Create a dashboard screen",
        data={
            "prompt": "Create a dashboard screen",
            "generation_status": "queued",
            "generation_error": "",
        },
    )

    monkeypatch.setattr(
        screens_module.StitchService,
        "create_project",
        lambda title="": {"name": "projects/stitch-project", "title": title},
    )
    monkeypatch.setattr(
        screens_module.StitchService,
        "generate_screen",
        lambda **kwargs: {
            "outputComponents": [
                {
                    "design": {
                        "screens": [
                            {
                                "name": "projects/stitch-project/screens/screen-456",
                                "screenshot": {"downloadUrl": "https://example.com/sdk-screen.png"},
                                "htmlCode": {"downloadUrl": "https://example.com/sdk-screen.html"},
                            }
                        ]
                    }
                }
            ]
        },
    )
    monkeypatch.setattr(screens_module.StitchService, "list_screens", lambda project_id: [])

    screens_module._run_screen_generation(
        app,
        project.id,
        screen.id,
        "Create a dashboard screen",
        "DESKTOP",
        "",
    )

    updated = ScreenService.get(screen.id)
    assert updated.data["generation_status"] == "completed"
    assert updated.data["stitch_project_id"] == "stitch-project"
    assert updated.data["stitch_screen_id"] == "screen-456"
    assert updated.data["image_url"] == "https://example.com/sdk-screen.png"
    assert updated.data["generation_error"] == ""
    assert updated.data["materials"][0]["id"] == "screen-image"


def test_background_generation_updates_screen_on_failure(app, project, monkeypatch):
    import app.routes.screens as screens_module

    screen = ScreenService.create(
        project_id=project.id,
        name="Dashboard",
        device_type="desktop",
        description="Generated from prompt: Create a dashboard screen",
        data={
            "prompt": "Create a dashboard screen",
            "generation_status": "queued",
            "generation_error": "",
        },
    )

    monkeypatch.setattr(
        screens_module.StitchService,
        "create_project",
        lambda title="": (_ for _ in ()).throw(RuntimeError("stitch unavailable")),
    )

    screens_module._run_screen_generation(
        app,
        project.id,
        screen.id,
        "Create a dashboard screen",
        "DESKTOP",
        "",
    )

    updated = ScreenService.get(screen.id)
    assert updated.data["generation_status"] == "failed"
    assert updated.data["generation_error"] == "stitch unavailable"


def test_background_generation_handles_chatty_output_gracefully(app, project, monkeypatch):
    import app.routes.screens as screens_module

    screen = ScreenService.create(
        project_id=project.id,
        name="Hello World",
        device_type="desktop",
        description="Generated from prompt: hello world",
        data={
            "prompt": "hello world",
            "generation_status": "queued",
            "generation_error": "",
        },
    )

    monkeypatch.setattr(
        screens_module.StitchService,
        "create_project",
        lambda title="": {"content": [{"type": "text", "text": '{"projectId":"stitch-project"}'}]},
    )
    monkeypatch.setattr(
        screens_module.StitchService,
        "generate_screen",
        lambda **kwargs: {
            "content": [
                {
                    "type": "text",
                    "text": '{"projectId":"stitch-project","sessionId":"123","outputComponents":[{"text":"Hello! How can I help you with your design project today?"},{"suggestion":"Design a landing page for a coffee shop"}]}',
                }
            ]
        },
    )
    monkeypatch.setattr(screens_module.StitchService, "list_screens", lambda project_id: [])

    screens_module._run_screen_generation(
        app,
        project.id,
        screen.id,
        "hello world",
        "DESKTOP",
        "",
    )

    updated = ScreenService.get(screen.id)
    assert updated.data["generation_status"] == "needs_input"
    assert updated.data["generation_error"] == ""
    assert updated.data["assistant_text"] == "Hello! How can I help you with your design project today?"
    assert updated.data["assistant_suggestions"] == ["Design a landing page for a coffee shop"]


def test_background_generation_recovers_after_connection_drop(app, project, monkeypatch):
    import app.routes.screens as screens_module

    screen = ScreenService.create(
        project_id=project.id,
        name="Dashboard",
        device_type="desktop",
        description="Generated from prompt: Create a dashboard screen",
        data={
            "prompt": "Create a dashboard screen",
            "generation_status": "queued",
            "generation_error": "",
        },
    )

    monkeypatch.setattr(
        screens_module.StitchService,
        "create_project",
        lambda title="": {"content": [{"type": "text", "text": '{"projectId":"stitch-project"}'}]},
    )

    list_calls = {"count": 0}

    def fake_list_screens(project_id):
        list_calls["count"] += 1
        if list_calls["count"] == 1:
            return []
        return [{"name": "projects/stitch-project/screens/screen-999"}]

    monkeypatch.setattr(screens_module.StitchService, "list_screens", fake_list_screens)
    monkeypatch.setattr(
        screens_module.StitchService,
        "generate_screen",
        lambda **kwargs: (_ for _ in ()).throw(
            RuntimeError("Stitch closed the connection before sending a response.")
        ),
    )
    monkeypatch.setattr(
        screens_module.StitchService,
        "get_screen",
        lambda project_id, screen_id: {
            "name": f"projects/{project_id}/screens/{screen_id}",
            "screenshot": {"downloadUrl": "https://example.com/screen.png"},
        },
    )
    monkeypatch.setattr(screens_module.time, "sleep", lambda seconds: None)

    screens_module._run_screen_generation(
        app,
        project.id,
        screen.id,
        "Create a dashboard screen",
        "DESKTOP",
        "",
    )

    updated = ScreenService.get(screen.id)
    assert updated.data["generation_status"] == "completed"
    assert updated.data["stitch_project_id"] == "stitch-project"
    assert updated.data["stitch_screen_id"] == "screen-999"
    assert updated.data["image_url"] == "https://example.com/screen.png"
    assert updated.data["generation_error"] == ""


def test_background_generation_enters_recovering_state_when_recovery_runs_async(app, project, monkeypatch):
    import app.routes.screens as screens_module

    screen = ScreenService.create(
        project_id=project.id,
        name="Dashboard",
        device_type="desktop",
        description="Generated from prompt: Create a dashboard screen",
        data={
            "prompt": "Create a dashboard screen",
            "generation_status": "queued",
            "generation_error": "",
        },
    )

    monkeypatch.setattr(
        screens_module.StitchService,
        "create_project",
        lambda title="": {"content": [{"type": "text", "text": '{"projectId":"stitch-project"}'}]},
    )
    monkeypatch.setattr(screens_module.StitchService, "list_screens", lambda project_id: [])
    monkeypatch.setattr(
        screens_module.StitchService,
        "generate_screen",
        lambda **kwargs: (_ for _ in ()).throw(
            RuntimeError("Stitch closed the connection before sending a response.")
        ),
    )

    submitted = {}

    class _Executor:
        def submit(self, fn, *args, **kwargs):
            submitted["fn"] = fn
            submitted["args"] = args
            submitted["kwargs"] = kwargs
            return SimpleNamespace()

    monkeypatch.setattr(screens_module, "_GENERATION_EXECUTOR", _Executor())

    screens_module._run_screen_generation(
        app,
        project.id,
        screen.id,
        "Create a dashboard screen",
        "DESKTOP",
        "",
    )

    updated = ScreenService.get(screen.id)
    assert updated.data["generation_status"] == "recovering"
    assert updated.data["generation_error"] == ""
    assert submitted["fn"] == screens_module._recover_generation_after_disconnect


def test_screen_detail_handles_project_backend_disconnect(client, project, monkeypatch):
    screen = ScreenService.create(
        project_id=project.id,
        name="Dashboard",
        device_type="desktop",
        data={},
    )

    def fail(_project_id):
        raise ProjectServiceUnavailableError(
            "Could not reach project storage while trying to load the project. Please try again."
        )

    monkeypatch.setattr("app.routes.screens.ProjectService.get", fail)

    response = client.get(
        f"/projects/{project.id}/screens/{screen.id}",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Could not reach project storage" in response.data
