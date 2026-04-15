import json
import pytest
from app.services.document_service import DocumentService
from app.services.diagram_service import DiagramService
from app.services.api_endpoint_service import APIEndpointService
from app.services.project_service import ProjectService
from app.services.project_template_service import ProjectTemplateService
from app.export.export_service import ExportService


@pytest.fixture
def populated_project(project_id):
    """Populate the test project with one of each artifact type."""
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
        "tags": ["integration", "e2e"],
        "test_strategy": "Unit + integration tests",
        "test_cases": [{"description": "JSON export", "test_name": "export_json", "test_uid": "abc123ef", "steps": "Call export", "expected_result": "Valid JSON", "status": "passed"}],
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
    def test_export_nonexistent_project(self):
        assert ExportService.export_json("00000000-0000-0000-0000-000000000000") is None

    def test_export_empty_project(self, project, project_id):
        result = ExportService.export_json(project_id)
        assert result is not None
        assert result["project"] == project.name
        assert result["project_template"]["key"] == "generic"
        assert result["requirements"] == []
        assert result["user_stories"] == []
        assert result["project_plans"] == []
        assert result["test_plans"] == []
        assert result["diagrams"] == []
        assert result["api_endpoints"] == []

    def test_export_with_project_template(self, project):
        ProjectService.update(project, template_key="aspnetcore_clean_architecture")
        ProjectTemplateService.seed_project_template(project, "aspnetcore_clean_architecture")

        result = ExportService.export_json(project.id)

        assert result["project_template"]["key"] == "aspnetcore_clean_architecture"
        assert result["project_template"]["label"] == "ASP.NET Core Clean Architecture"
        assert "Domain" in " ".join(result["project_template"]["layers"])
        assert len(result["folder_structures"]) == 1
        assert any(item["is_fixed"] for item in result["folder_structures"][0]["items"])

    def test_export_with_all_artifacts(self, populated_project):
        result = ExportService.export_json(populated_project)
        assert len(result["user_stories"]) == 1
        assert len(result["requirements"]) == 1
        assert len(result["project_plans"]) == 1
        assert len(result["test_plans"]) == 1
        assert len(result["diagrams"]) == 1
        assert len(result["api_endpoints"]) == 1

    def test_user_story_format(self, populated_project):
        result = ExportService.export_json(populated_project)
        story = result["user_stories"][0]
        assert story["as_a"] == "developer"
        assert story["i_want_to"] == "export designs"
        assert story["so_that"] == "share with team"
        assert story["priority"] == "high"
        assert len(story["acceptance_criteria"]) == 2

    def test_multi_user_story_document_exports_each_story(self, project_id):
        DocumentService.create(project_id=project_id, doc_type="user_story", data={
            "stories": [
                {
                    "user_type": "developer",
                    "action": "export designs",
                    "benefit": "share with team",
                    "priority": "high",
                    "status": "draft",
                    "acceptance_criteria": ["Export works"],
                },
                {
                    "user_type": "manager",
                    "action": "review exports",
                    "benefit": "approve deliverables",
                    "priority": "medium",
                    "status": "approved",
                    "acceptance_criteria": ["Review is visible"],
                },
            ],
        })

        result = ExportService.export_json(project_id)

        assert len(result["user_stories"]) == 2
        assert result["user_stories"][0]["as_a"] == "developer"
        assert result["user_stories"][1]["as_a"] == "manager"

    def test_requirement_format(self, populated_project):
        result = ExportService.export_json(populated_project)
        req = result["requirements"][0]
        assert req["title"] == "Export Feature"
        assert req["type"] == "functional"
        assert req["priority"] == "must"
        assert req["rationale"] == "LLM agents need structured input"

    def test_project_plan_format(self, populated_project):
        result = ExportService.export_json(populated_project)
        plan = result["project_plans"][0]
        assert plan["project_name"] == "Design Tool"
        assert len(plan["goals"]) == 2
        assert len(plan["milestones"]) == 1
        assert len(plan["risks"]) == 1

    def test_test_plan_format(self, populated_project):
        result = ExportService.export_json(populated_project)
        tp = result["test_plans"][0]
        assert tp["test_scope"] == "Export functionality"
        assert tp["tags"] == ["integration", "e2e"]
        assert len(tp["test_cases"]) == 1
        assert tp["test_cases"][0]["test_name"] == "export_json"
        assert tp["entry_criteria"] == "Code complete"

    def test_diagram_format(self, populated_project):
        result = ExportService.export_json(populated_project)
        diag = result["diagrams"][0]
        assert diag["type"] == "architecture"
        assert diag["name"] == "System Overview"
        assert len(diag["nodes"]) == 1
        assert len(diag["edges"]) == 1

    def test_api_endpoint_format(self, populated_project):
        result = ExportService.export_json(populated_project)
        ep = result["api_endpoints"][0]
        assert ep["path"] == "/api/users"
        assert ep["method"] == "GET"
        assert ep["description"] == "List all users"
        assert len(ep["parameters"]) == 1
        assert len(ep["status_codes"]) == 1

    def test_single_diagram_json_export(self, project, project_id):
        diagram = DiagramService.create(
            project_id=project_id,
            diagram_type="workflow",
            name="Decision Flow",
            data={
                "nodes": [{"id": "1", "type": "workflowState", "data": {"label": "Decision"}}],
                "edges": [{"id": "e1-2", "source": "1", "target": "2", "label": "Yes"}],
            },
        )

        result = ExportService.export_diagram_json(project_id, diagram.id)

        assert result["project"]["id"] == project.id
        assert result["diagram"]["name"] == "Decision Flow"
        assert result["diagram"]["edges"][0]["label"] == "Yes"


class TestExportServiceMarkdown:
    def test_markdown_nonexistent(self):
        assert ExportService.export_markdown("00000000-0000-0000-0000-000000000000") is None

    def test_markdown_empty_project(self, project, project_id):
        result = ExportService.export_markdown(project_id)
        assert result is not None
        assert f"# {project.name}" in result
        assert "## Project Template" in result

    def test_markdown_with_project_template(self, project):
        ProjectService.update(project, template_key="aspnetcore_clean_architecture")
        ProjectTemplateService.seed_project_template(project, "aspnetcore_clean_architecture")

        result = ExportService.export_markdown(project.id)

        assert "ASP.NET Core Clean Architecture" in result
        assert "Starter Outputs" in result
        assert "Clean Architecture Overview" in result
        assert "## Folder Structures" in result

    def test_markdown_with_all_artifacts(self, populated_project):
        result = ExportService.export_markdown(populated_project)
        assert "## Requirements" in result
        assert "## User Stories" in result
        assert "## Project Plans" in result
        assert "## Test Plans" in result
        assert "## Diagrams" in result
        assert "## API Endpoints" in result

    def test_markdown_user_story_format(self, populated_project):
        result = ExportService.export_markdown(populated_project)
        assert "As a **developer**" in result
        assert "export designs" in result
        assert "- [ ] Export works" in result

    def test_markdown_test_plan_tags(self, populated_project):
        result = ExportService.export_markdown(populated_project)
        assert "**Tags:** integration, e2e" in result

    def test_markdown_requirement_format(self, populated_project):
        result = ExportService.export_markdown(populated_project)
        assert "### Export Feature" in result
        assert "**Priority:** must" in result

    def test_markdown_diagram_format(self, populated_project):
        result = ExportService.export_markdown(populated_project)
        assert "### System Overview (architecture)" in result
        assert "Frontend" in result

    def test_markdown_api_format(self, populated_project):
        result = ExportService.export_markdown(populated_project)
        assert "`GET /api/users`" in result
        assert "List all users" in result

    def test_single_diagram_markdown_export(self, project_id):
        diagram = DiagramService.create(
            project_id=project_id,
            diagram_type="architecture",
            name="System Overview",
            data={
                "nodes": [{"id": "1", "type": "component", "data": {"label": "Frontend"}}],
                "edges": [{"id": "e1-2", "source": "1", "target": "2", "label": "HTTP"}],
            },
        )

        result = ExportService.export_diagram_markdown(project_id, diagram.id)

        assert "# System Overview" in result
        assert "## Nodes" in result
        assert "Frontend" in result
        assert "## Edges" in result
        assert "HTTP" in result


class TestExportRoute:
    def test_json_export_route(self, client, populated_project):
        response = client.get(f"/api/projects/{populated_project}/export?format=json")
        assert response.status_code == 200
        data = response.get_json()
        assert "user_stories" in data
        assert "requirements" in data
        assert "diagrams" in data
        assert "api_endpoints" in data

    def test_json_export_default_format(self, client, populated_project):
        response = client.get(f"/api/projects/{populated_project}/export")
        assert response.status_code == 200
        assert response.get_json() is not None

    def test_markdown_export_route(self, client, populated_project):
        response = client.get(f"/api/projects/{populated_project}/export?format=markdown")
        assert response.status_code == 200
        assert response.content_type.startswith("text/markdown")
        assert b"## Requirements" in response.data

    def test_export_not_found(self, client):
        response = client.get("/api/projects/00000000-0000-0000-0000-000000000000/export")
        assert response.status_code == 404

    def test_single_diagram_json_export_route(self, client, project_id):
        diagram = DiagramService.create(project_id=project_id, diagram_type="architecture", name="Exportable Diagram")

        response = client.get(f"/projects/{project_id}/diagrams/{diagram.id}/export?format=json")

        assert response.status_code == 200
        assert response.content_type.startswith("application/json")
        data = json.loads(response.data)
        assert data["diagram"]["name"] == "Exportable Diagram"

    def test_single_diagram_markdown_export_route(self, client, project_id):
        diagram = DiagramService.create(project_id=project_id, diagram_type="architecture", name="Markdown Diagram")

        response = client.get(f"/projects/{project_id}/diagrams/{diagram.id}/export?format=markdown")

        assert response.status_code == 200
        assert response.content_type.startswith("text/markdown")
        assert b"# Markdown Diagram" in response.data

    def test_export_button_on_project_page(self, client, project_id):
        response = client.get(f"/projects/{project_id}")
        assert response.status_code == 200
        assert b"Export JSON" in response.data
        assert b"Export Markdown" in response.data
