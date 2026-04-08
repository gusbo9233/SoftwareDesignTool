from io import BytesIO

from app.services.screen_service import ScreenService


def test_manual_screen_folder_collects_initial_materials(client, project):
    response = client.post(
        f"/projects/{project.id}/screens/new",
        data={
            "name": "Login Screen",
            "device_type": "DESKTOP",
            "description": "Authentication entry point",
            "html_content": "<div>Login</div>",
            "image_url": "https://example.com/login.png",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    screens = ScreenService.get_all_for_project(project.id)
    assert len(screens) == 1

    screen = screens[0]
    assert screen.data["folder_name"] == "Login Screen"
    material_ids = [item["id"] for item in screen.data["materials"]]
    assert "screen-html" in material_ids
    assert "screen-image" in material_ids
    html_material = next(item for item in screen.data["materials"] if item["id"] == "screen-html")
    assert html_material["storage_name"] == "current-screen.html"


def test_screen_folder_can_be_created_with_parent(client, project):
    parent = ScreenService.create(
        project_id=project.id,
        name="Auth",
        device_type="desktop",
        data={"folder_name": "Auth"},
    )

    response = client.post(
        f"/projects/{project.id}/screens/new",
        data={
            "name": "Login",
            "device_type": "DESKTOP",
            "description": "Child folder",
            "parent_id": parent.id,
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    screens = ScreenService.get_all_for_project(project.id)
    child = next(screen for screen in screens if screen.name == "Login")
    assert child.data["parent_id"] == parent.id


def test_upload_material_adds_file_to_folder_and_serves_it(client, project):
    screen = ScreenService.create(
        project_id=project.id,
        name="Checkout",
        device_type="desktop",
        description="Checkout flow",
        data={"folder_name": "Checkout"},
    )

    upload_response = client.post(
        f"/projects/{project.id}/screens/{screen.id}/materials",
        data={"material_file": (BytesIO(b"wireframe-content"), "wireframe.txt")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert upload_response.status_code == 302

    updated = ScreenService.get(screen.id)
    uploads = [item for item in updated.data["materials"] if item["source"] == "upload"]
    assert len(uploads) == 1
    material = uploads[0]
    assert material["original_filename"] == "wireframe.txt"

    download_response = client.get(
        f"/projects/{project.id}/screens/{screen.id}/materials/{material['id']}"
    )

    assert download_response.status_code == 200
    assert download_response.data == b"wireframe-content"


def test_detail_page_renders_folder_materials_section(client, project):
    screen = ScreenService.create(
        project_id=project.id,
        name="Dashboard",
        device_type="desktop",
        description="Main app dashboard",
        data={
            "folder_name": "Dashboard",
            "html": "<div>Dashboard</div>",
        },
    )

    response = client.get(f"/projects/{project.id}/screens/{screen.id}")

    assert response.status_code == 200
    assert b"Folder Materials" in response.data
    assert b"Upload to Folder" in response.data
    assert b"Dashboard" in response.data


def test_index_page_renders_folder_tree(client, project):
    parent = ScreenService.create(
        project_id=project.id,
        name="Checkout",
        device_type="desktop",
        data={"folder_name": "Checkout"},
    )
    ScreenService.create(
        project_id=project.id,
        name="Payment",
        device_type="desktop",
        data={"folder_name": "Payment", "parent_id": parent.id},
    )

    response = client.get(f"/projects/{project.id}/screens")

    assert response.status_code == 200
    assert b"Folder Tree" in response.data
    assert b"Checkout" in response.data
    assert b"Payment" in response.data
    assert b"Add Child" in response.data


def test_wireframe_editor_route_renders_inside_folder(client, project):
    screen = ScreenService.create(
        project_id=project.id,
        name="Settings",
        device_type="desktop",
        data={"folder_name": "Settings"},
    )

    response = client.get(f"/projects/{project.id}/screens/{screen.id}/wireframe")

    assert response.status_code == 200
    assert b"Wireframe Tool" in response.data
    assert b"Wireframe Library" in response.data
    assert b"Wireframe 1" in response.data
    assert b"Start Connection" in response.data
    assert b"Collection" in response.data
    assert b"Block ID" in response.data
    assert b"Notes" in response.data
    assert b"Parent" in response.data


def test_current_screen_html_file_can_be_edited(client, project):
    screen = ScreenService.create(
        project_id=project.id,
        name="Landing",
        device_type="desktop",
        data={"folder_name": "Landing", "html": "<div>Old</div>"},
    )

    response = client.post(
        f"/projects/{project.id}/screens/{screen.id}/materials/screen-html/edit",
        data={"html_content": "<div>New</div>"},
        follow_redirects=False,
    )

    assert response.status_code == 302

    updated = ScreenService.get(screen.id)
    assert updated.data["html"] == "<div>New</div>"


def test_api_update_with_wireframe_registers_wireframe_material(client, project):
    screen = ScreenService.create(
        project_id=project.id,
        name="Profile",
        device_type="desktop",
        data={"folder_name": "Profile"},
    )

    response = client.put(
        f"/api/screens/{screen.id}",
        json={
            "data": {
                "folder_name": "Profile",
                "wireframes": [
                    {
                        "id": "board-a",
                        "name": "Primary layout",
                        "canvas": {"width": 960, "height": 640},
                        "items": [{"id": "wf-1", "label": "Header", "x": 10, "y": 10, "width": 100, "height": 40}],
                        "created_at": "2026-04-07T10:00:00+00:00",
                        "updated_at": "2026-04-07T10:10:00+00:00",
                    }
                ],
            }
        },
    )

    assert response.status_code == 200

    updated = ScreenService.get(screen.id)
    material_ids = [item["id"] for item in updated.data["materials"]]
    assert "wireframe-board-board-a" in material_ids


def test_screen_folder_can_hold_multiple_wireframes(client, project):
    screen = ScreenService.create(
        project_id=project.id,
        name="Profile",
        device_type="desktop",
        data={"folder_name": "Profile"},
    )

    response = client.put(
        f"/api/screens/{screen.id}",
        json={
            "data": {
                "folder_name": "Profile",
                "wireframes": [
                    {
                        "id": "board-a",
                        "name": "Primary layout",
                        "canvas": {"width": 960, "height": 640},
                        "items": [{"id": "wf-1"}],
                        "connections": [],
                        "created_at": "2026-04-07T10:00:00+00:00",
                        "updated_at": "2026-04-07T10:10:00+00:00",
                    },
                    {
                        "id": "board-b",
                        "name": "Alt mobile",
                        "canvas": {"width": 900, "height": 700},
                        "items": [{"id": "wf-2"}],
                        "connections": [],
                        "created_at": "2026-04-07T11:00:00+00:00",
                        "updated_at": "2026-04-07T11:10:00+00:00",
                    },
                ],
            }
        },
    )

    assert response.status_code == 200

    updated = ScreenService.get(screen.id)
    assert len(updated.data["wireframes"]) == 2
    material_ids = [item["id"] for item in updated.data["materials"]]
    assert "wireframe-board-board-a" in material_ids
    assert "wireframe-board-board-b" in material_ids


def test_wireframe_can_export_as_json(client, project):
    screen = ScreenService.create(
        project_id=project.id,
        name="Profile",
        device_type="desktop",
        data={
            "folder_name": "Profile",
            "wireframes": [
                {
                    "id": "board-a",
                    "name": "Primary layout",
                    "canvas": {"width": 960, "height": 640},
                    "items": [{"id": "wf-1", "label": "Header", "type": "header", "x": 10, "y": 20, "width": 200, "height": 50}],
                    "connections": [],
                    "created_at": "2026-04-07T10:00:00+00:00",
                    "updated_at": "2026-04-07T10:10:00+00:00",
                }
            ],
        },
    )

    response = client.get(
        f"/projects/{project.id}/screens/{screen.id}/wireframes/board-a/export?format=json"
    )

    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert "filename=Profile-Primary_layout.json" in response.headers["Content-Disposition"]
    assert b'"wireframe_id": "board-a"' in response.data
    assert b'"wireframe_name": "Primary layout"' in response.data


def test_wireframe_can_export_as_markdown(client, project):
    screen = ScreenService.create(
        project_id=project.id,
        name="Profile",
        device_type="desktop",
        data={
            "folder_name": "Profile",
            "wireframes": [
                {
                    "id": "board-a",
                    "name": "Primary layout",
                    "canvas": {"width": 960, "height": 640},
                    "items": [{"id": "wf-1", "label": "Header", "objectId": "hero_header", "type": "header", "x": 10, "y": 20, "width": 200, "height": 50}],
                    "connections": [{"from": "wf-1", "to": "wf-2"}],
                    "created_at": "2026-04-07T10:00:00+00:00",
                    "updated_at": "2026-04-07T10:10:00+00:00",
                }
            ],
        },
    )

    response = client.get(
        f"/projects/{project.id}/screens/{screen.id}/wireframes/board-a/export?format=markdown"
    )

    assert response.status_code == 200
    assert response.mimetype == "text/markdown"
    assert "filename=Profile-Primary_layout.md" in response.headers["Content-Disposition"]
    assert b"# Primary layout" in response.data
    assert b"## Blocks" in response.data
    assert b"hero_header" in response.data
