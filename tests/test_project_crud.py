import pytest
from app import create_app, db
from app.models.project import Project
from app.services.project_service import ProjectService


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


class TestProjectService:
    def test_create_project(self, app):
        with app.app_context():
            project = ProjectService.create(name="Test", description="A test project")
            assert project.id is not None
            assert project.name == "Test"
            assert project.description == "A test project"

    def test_get_project(self, app):
        with app.app_context():
            created = ProjectService.create(name="Lookup")
            found = ProjectService.get(created.id)
            assert found is not None
            assert found.name == "Lookup"

    def test_get_nonexistent_project(self, app):
        with app.app_context():
            assert ProjectService.get("nonexistent") is None

    def test_get_all_projects(self, app):
        with app.app_context():
            ProjectService.create(name="A")
            ProjectService.create(name="B")
            projects = ProjectService.get_all()
            assert len(projects) == 2

    def test_update_project(self, app):
        with app.app_context():
            project = ProjectService.create(name="Old Name")
            ProjectService.update(project, name="New Name", description="Updated")
            refreshed = ProjectService.get(project.id)
            assert refreshed.name == "New Name"
            assert refreshed.description == "Updated"

    def test_delete_project(self, app):
        with app.app_context():
            project = ProjectService.create(name="To Delete")
            pid = project.id
            ProjectService.delete(project)
            assert ProjectService.get(pid) is None


class TestProjectRoutes:
    def test_dashboard(self, client, app):
        with app.app_context():
            ProjectService.create(name="Dashboard Project")
        response = client.get("/")
        assert response.status_code == 200
        assert b"Dashboard Project" in response.data

    def test_create_project_get(self, client):
        response = client.get("/projects/new")
        assert response.status_code == 200
        assert b"New" in response.data

    def test_create_project_post(self, client, app):
        response = client.post(
            "/projects/new",
            data={"name": "Created", "description": "Via form"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Created" in response.data

    def test_create_project_empty_name(self, client):
        response = client.post(
            "/projects/new",
            data={"name": "", "description": "No name"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"required" in response.data

    def test_project_detail(self, client, app):
        with app.app_context():
            project = ProjectService.create(name="Detail Test")
            pid = project.id
        response = client.get(f"/projects/{pid}")
        assert response.status_code == 200
        assert b"Detail Test" in response.data

    def test_project_detail_not_found(self, client):
        response = client.get("/projects/nonexistent", follow_redirects=True)
        assert response.status_code == 200
        assert b"not found" in response.data

    def test_edit_project(self, client, app):
        with app.app_context():
            project = ProjectService.create(name="Edit Me")
            pid = project.id
        response = client.post(
            f"/projects/{pid}/edit",
            data={"name": "Edited", "description": "Updated"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Edited" in response.data

    def test_delete_project_route(self, client, app):
        with app.app_context():
            project = ProjectService.create(name="Delete Me")
            pid = project.id
        response = client.post(f"/projects/{pid}/delete", follow_redirects=True)
        assert response.status_code == 200
        assert b"Delete Me" not in response.data
