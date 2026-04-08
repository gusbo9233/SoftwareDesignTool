import pytest
from app.services.project_service import ProjectService, ProjectServiceUnavailableError
from app.services.document_service import DocumentService
from app.services.diagram_service import DiagramService
from app.services.project_template_service import ProjectTemplateService


class TestProjectService:
    def test_create_project(self):
        p = ProjectService.create(name="Test", description="A test project")
        try:
            assert p.id is not None
            assert p.name == "Test"
            assert p.description == "A test project"
            assert p.template_key == "generic"
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
        ProjectService.update(
            project,
            name="New Name",
            description="Updated",
            template_key="aspnetcore_clean_architecture",
        )
        refreshed = ProjectService.get(project.id)
        assert refreshed.name == "New Name"
        assert refreshed.description == "Updated"
        assert refreshed.template_key == "aspnetcore_clean_architecture"

    def test_delete_project(self):
        p = ProjectService.create(name="To Delete")
        pid = p.id
        ProjectService.delete(p)
        assert ProjectService.get(pid) is None

    def test_create_project_falls_back_when_template_key_column_missing(self, monkeypatch):
        class FakeInsert:
            def __init__(self, payload):
                self.payload = payload

            def execute(self):
                if "template_key" in self.payload:
                    raise Exception("Could not find the 'template_key' column of 'projects' in the schema cache")
                return type("Response", (), {
                    "data": [{
                        "id": "fallback-project",
                        "name": self.payload["name"],
                        "description": self.payload["description"],
                    }]
                })()

        class FakeTable:
            def insert(self, payload):
                return FakeInsert(payload)

        class FakeSupabase:
            def table(self, name):
                assert name == "projects"
                return FakeTable()

        monkeypatch.setattr("app.services.project_service._app.supabase", FakeSupabase())

        project = ProjectService.create(name="Fallback", description="Created without template_key")

        assert project.id == "fallback-project"
        assert project.name == "Fallback"
        assert project.template_key == "generic"


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

    def test_create_project_post_with_aspnet_template_seeds_artifacts(self, client):
        response = client.post(
            "/projects/new",
            data={
                "name": "Clean API",
                "description": "Seed ASP.NET Core clean architecture",
                "template_key": "aspnetcore_clean_architecture",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"ASP.NET Core Clean Architecture" in response.data
        assert b"Starter Blueprint" in response.data

        projects = ProjectService.get_all()
        created = next(p for p in projects if p.name == "Clean API")
        try:
            documents = DocumentService.get_all_for_project(created.id)
            diagrams = DiagramService.get_all_for_project(created.id)
            assert any(doc.type == "tech_stack" for doc in documents)
            assert any(doc.type == "project_plan" for doc in documents)
            assert any(doc.type == "adr" for doc in documents)
            assert any(doc.type == "folder_structure" for doc in documents)
            assert any(diagram.name == "Clean Architecture Overview" for diagram in diagrams)
        finally:
            ProjectService.delete(created)

    def test_create_project_post_with_mvc_template_seeds_artifacts(self, client):
        response = client.post(
            "/projects/new",
            data={
                "name": "MVC App",
                "description": "Seed MVC architecture",
                "template_key": "mvc",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Model View Controller" in response.data
        assert b"Starter Blueprint" in response.data

        projects = ProjectService.get_all()
        created = next(p for p in projects if p.name == "MVC App")
        try:
            documents = DocumentService.get_all_for_project(created.id)
            diagrams = DiagramService.get_all_for_project(created.id)
            assert any(doc.type == "tech_stack" for doc in documents)
            assert any(doc.type == "project_plan" for doc in documents)
            assert any(doc.type == "adr" for doc in documents)
            assert any(doc.type == "folder_structure" for doc in documents)
            assert any(diagram.name == "MVC Overview" for diagram in diagrams)
        finally:
            ProjectService.delete(created)

    def test_existing_aspnet_template_project_auto_backfills_folder_structure(self, client):
        project = ProjectService.create(name="Legacy Clean", template_key="aspnetcore_clean_architecture")
        try:
            DocumentService.create(
                project_id=project.id,
                doc_type="tech_stack",
                data=ProjectTemplateService._tech_stack("aspnetcore_clean_architecture"),
            )

            response = client.get(f"/projects/{project.id}/documents", follow_redirects=True)

            assert response.status_code == 200
            documents = DocumentService.get_all_for_project(project.id)
            assert any(doc.type == "folder_structure" for doc in documents)
            assert b"Create Folder Structure" not in response.data
        finally:
            ProjectService.delete(project)

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

    def test_project_detail_handles_backend_disconnect(self, client, monkeypatch, project):
        def fail(_id):
            raise ProjectServiceUnavailableError("Could not reach project storage while trying to load the project. Please try again.")

        monkeypatch.setattr("app.routes.projects.ProjectService.get", fail)

        response = client.get(f"/projects/{project.id}", follow_redirects=True)

        assert response.status_code == 200
        assert b"Could not reach project storage" in response.data

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
