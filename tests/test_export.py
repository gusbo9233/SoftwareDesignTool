import json
import pytest
from app import create_app, db
from app.services.project_service import ProjectService
from app.services.document_service import DocumentService
from app.services.diagram_service import DiagramService
from app.services.api_endpoint_service import APIEndpointService
from app.export.export_service import ExportService


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


@pytest.fixture
def project_id(app):
    with app.app_context():
        p = ProjectService.create(name="Export Test Project", description="A test project")
        return p.id


@pytest.fixture
def populated_project(app, project_id):
    """Create a project with one of each artifact type."""
    with app.app_context():
        DocumentService.create(project_id=project_id, doc_type="user_story", data={
            "user_type": "developer",
            "action": "export designs",
            "benefit": "share with team",
            "priority": "high",
            "status": "draft",
            "acceptance_criteria": ["Export works", "Format is correct"],
        })
        DocumentService.create(project_id=project_id, doc_type="requirement", data={
            "title": "Export Feature",
            "description": "Must support JSON and Markdown export",
            "type": "functional",
            "category": "Export",
            "priority": "must",
            "status": "approved",
            "rationale": "LLM agents need structured input",
        })
        DocumentService.create(project_id=project_id, doc_type="project_plan", data={
            "project_name": "Design Tool",
            "project_description": "A software design tool",
            "goals": ["Build export", "Test export"],
            "in_scope": ["JSON export", "Markdown export"],
            "out_scope": ["PDF export"],
            "milestones": [{"name": "v1.0", "target_date": "2026-05-01", "deliverables": "MVP", "status": "planned"}],
            "risks": [{"description": "Scope creep", "likelihood": "medium", "impact": "high", "mitigation": "Strict priorities"}],
        })
        DocumentService.create(project_id=project_id, doc_type="test_plan", data={
            "test_scope": "Export functionality",
            "test_strategy": "Unit + integration tests",
            "test_cases": [{"description": "JSON export", "steps": "Call export", "expected_result": "Valid JSON", "status": "passed"}],
            "entry_criteria": "Code complete",
            "exit_criteria": "All tests pass",
            "environment": "Python 3.10",
        })
        DiagramService.create(
            project_id=project_id, diagram_type="architecture", name="System Overview",
            data={
                "nodes": [{"id": "1", "type": "component", "position": {"x": 0, "y": 0}, "data": {"label": "Frontend"}}],
                "edges": [{"id": "e1-2", "source": "1", "target": "2", "label": "HTTP"}],
            },
        )
        APIEndpointService.create(
            project_id=project_id, path="/api/users", method="GET",
            description="List all users",
            request_schema={"parameters": [{"name": "page", "location": "query", "type": "integer", "required": False, "description": "Page number"}], "body": ""},
            response_schema={"body": '{"type": "array"}', "status_codes": [{"code": "200", "description": "OK"}]},
        )
    return project_id


class TestExportServiceJSON:
    def test_export_nonexistent_project(self, app):
        with app.app_context():
            assert ExportService.export_json("nonexistent") is None

    def test_export_empty_project(self, app, project_id):
        with app.app_context():
            result = ExportService.export_json(project_id)
            assert result is not None
            assert result["project"] == "Export Test Project"
            assert result["description"] == "A test project"
            assert result["requirements"] == []
            assert result["user_stories"] == []
            assert result["project_plans"] == []
            assert result["test_plans"] == []
            assert result["diagrams"] == []
            assert result["api_endpoints"] == []

    def test_export_with_all_artifacts(self, app, populated_project):
        with app.app_context():
            result = ExportService.export_json(populated_project)
            assert result["project"] == "Export Test Project"
            assert len(result["user_stories"]) == 1
            assert len(result["requirements"]) == 1
            assert len(result["project_plans"]) == 1
            assert len(result["test_plans"]) == 1
            assert len(result["diagrams"]) == 1
            assert len(result["api_endpoints"]) == 1

    def test_user_story_format(self, app, populated_project):
        with app.app_context():
            result = ExportService.export_json(populated_project)
            story = result["user_stories"][0]
            assert story["as_a"] == "developer"
            assert story["i_want_to"] == "export designs"
            assert story["so_that"] == "share with team"
            assert story["priority"] == "high"
            assert len(story["acceptance_criteria"]) == 2

    def test_requirement_format(self, app, populated_project):
        with app.app_context():
            result = ExportService.export_json(populated_project)
            req = result["requirements"][0]
            assert req["title"] == "Export Feature"
            assert req["type"] == "functional"
            assert req["priority"] == "must"
            assert req["rationale"] == "LLM agents need structured input"

    def test_project_plan_format(self, app, populated_project):
        with app.app_context():
            result = ExportService.export_json(populated_project)
            plan = result["project_plans"][0]
            assert plan["project_name"] == "Design Tool"
            assert len(plan["goals"]) == 2
            assert len(plan["milestones"]) == 1
            assert len(plan["risks"]) == 1

    def test_test_plan_format(self, app, populated_project):
        with app.app_context():
            result = ExportService.export_json(populated_project)
            tp = result["test_plans"][0]
            assert tp["test_scope"] == "Export functionality"
            assert len(tp["test_cases"]) == 1
            assert tp["entry_criteria"] == "Code complete"

    def test_diagram_format(self, app, populated_project):
        with app.app_context():
            result = ExportService.export_json(populated_project)
            diag = result["diagrams"][0]
            assert diag["type"] == "architecture"
            assert diag["name"] == "System Overview"
            assert len(diag["nodes"]) == 1
            assert len(diag["edges"]) == 1

    def test_api_endpoint_format(self, app, populated_project):
        with app.app_context():
            result = ExportService.export_json(populated_project)
            ep = result["api_endpoints"][0]
            assert ep["path"] == "/api/users"
            assert ep["method"] == "GET"
            assert ep["description"] == "List all users"
            assert len(ep["parameters"]) == 1
            assert len(ep["status_codes"]) == 1


class TestExportServiceMarkdown:
    def test_markdown_nonexistent(self, app):
        with app.app_context():
            assert ExportService.export_markdown("nonexistent") is None

    def test_markdown_empty_project(self, app, project_id):
        with app.app_context():
            result = ExportService.export_markdown(project_id)
            assert result is not None
            assert "# Export Test Project" in result

    def test_markdown_with_all_artifacts(self, app, populated_project):
        with app.app_context():
            result = ExportService.export_markdown(populated_project)
            assert "## Requirements" in result
            assert "## User Stories" in result
            assert "## Project Plans" in result
            assert "## Test Plans" in result
            assert "## Diagrams" in result
            assert "## API Endpoints" in result

    def test_markdown_user_story_format(self, app, populated_project):
        with app.app_context():
            result = ExportService.export_markdown(populated_project)
            assert "As a **developer**" in result
            assert "export designs" in result
            assert "- [ ] Export works" in result

    def test_markdown_requirement_format(self, app, populated_project):
        with app.app_context():
            result = ExportService.export_markdown(populated_project)
            assert "### Export Feature" in result
            assert "**Priority:** must" in result

    def test_markdown_diagram_format(self, app, populated_project):
        with app.app_context():
            result = ExportService.export_markdown(populated_project)
            assert "### System Overview (architecture)" in result
            assert "Frontend" in result

    def test_markdown_api_format(self, app, populated_project):
        with app.app_context():
            result = ExportService.export_markdown(populated_project)
            assert "`GET /api/users`" in result
            assert "List all users" in result


class TestExportRoute:
    def test_json_export_route(self, client, populated_project):
        response = client.get(f"/api/projects/{populated_project}/export?format=json")
        assert response.status_code == 200
        data = response.get_json()
        assert data["project"] == "Export Test Project"
        assert "user_stories" in data
        assert "requirements" in data
        assert "diagrams" in data
        assert "api_endpoints" in data

    def test_json_export_default_format(self, client, populated_project):
        response = client.get(f"/api/projects/{populated_project}/export")
        assert response.status_code == 200
        data = response.get_json()
        assert data["project"] == "Export Test Project"

    def test_markdown_export_route(self, client, populated_project):
        response = client.get(f"/api/projects/{populated_project}/export?format=markdown")
        assert response.status_code == 200
        assert response.content_type.startswith("text/markdown")
        text = response.data.decode("utf-8")
        assert "# Export Test Project" in text

    def test_export_not_found(self, client):
        response = client.get("/api/projects/nonexistent/export")
        assert response.status_code == 404

    def test_export_button_on_project_page(self, client, project_id):
        response = client.get(f"/projects/{project_id}")
        assert response.status_code == 200
        assert b"Export JSON" in response.data
        assert b"Export Markdown" in response.data
