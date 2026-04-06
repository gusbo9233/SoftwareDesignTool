from types import SimpleNamespace

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
