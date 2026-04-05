import pytest
from app.services.project_service import ProjectService


class TestProjectService:
    def test_create_project(self):
        p = ProjectService.create(name="Test", description="A test project")
        try:
            assert p.id is not None
            assert p.name == "Test"
            assert p.description == "A test project"
        finally:
            ProjectService.delete(p)

    def test_get_project(self):
        created = ProjectService.create(name="Lookup")
        try:
            found = ProjectService.get(created.id)
            assert found is not None
            assert found.name == "Lookup"
        finally:
            ProjectService.delete(created)

    def test_get_nonexistent_project(self):
        assert ProjectService.get("00000000-0000-0000-0000-000000000000") is None

    def test_get_all_projects(self):
        p1 = ProjectService.create(name="A")
        p2 = ProjectService.create(name="B")
        try:
            projects = ProjectService.get_all()
            ids = {p.id for p in projects}
            assert p1.id in ids
            assert p2.id in ids
        finally:
            ProjectService.delete(p1)
            ProjectService.delete(p2)

    def test_update_project(self, project):
        ProjectService.update(project, name="New Name", description="Updated")
        refreshed = ProjectService.get(project.id)
        assert refreshed.name == "New Name"
        assert refreshed.description == "Updated"

    def test_delete_project(self):
        p = ProjectService.create(name="To Delete")
        pid = p.id
        ProjectService.delete(p)
        assert ProjectService.get(pid) is None


class TestProjectRoutes:
    def test_dashboard(self, client, project):
        response = client.get("/")
        assert response.status_code == 200
        assert project.name.encode() in response.data

    def test_create_project_get(self, client):
        response = client.get("/projects/new")
        assert response.status_code == 200
        assert b"New" in response.data

    def test_create_project_post(self, client):
        response = client.post(
            "/projects/new",
            data={"name": "Created", "description": "Via form"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Created" in response.data
        # Cleanup the project created via HTTP
        projects = ProjectService.get_all()
        for p in projects:
            if p.name == "Created":
                ProjectService.delete(p)
                break

    def test_create_project_empty_name(self, client):
        response = client.post(
            "/projects/new",
            data={"name": "", "description": "No name"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"required" in response.data

    def test_project_detail(self, client, project):
        response = client.get(f"/projects/{project.id}")
        assert response.status_code == 200
        assert project.name.encode() in response.data

    def test_project_detail_not_found(self, client):
        response = client.get("/projects/00000000-0000-0000-0000-000000000000", follow_redirects=True)
        assert response.status_code == 200
        assert b"not found" in response.data

    def test_edit_project(self, client, project):
        response = client.post(
            f"/projects/{project.id}/edit",
            data={"name": "Edited", "description": "Updated"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Edited" in response.data

    def test_delete_project_route(self, client, project):
        pid = project.id
        response = client.post(f"/projects/{pid}/delete", follow_redirects=True)
        assert response.status_code == 200
        assert ProjectService.get(pid) is None
