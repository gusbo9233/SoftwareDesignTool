"""End-to-end test: create project, add all artifact types, export."""
import pytest
from app.services.project_service import ProjectService
from app.services.document_service import DocumentService
from app.services.diagram_service import DiagramService


class TestEndToEnd:
    def test_full_workflow(self, client):
        """Create a project via UI, add every artifact type, then export both formats."""
        pid = None
        try:
            # 1. Create project via form
            response = client.post(
                "/projects/new",
                data={"name": "E2E Test Project", "description": "Full workflow test"},
                follow_redirects=True,
            )
            assert response.status_code == 200
            assert b"E2E Test Project" in response.data

            # Get the project ID by name
            projects = ProjectService.get_all()
            project = next(p for p in projects if p.name == "E2E Test Project")
            pid = project.id

            # 2. Verify project detail page
            response = client.get(f"/projects/{pid}")
            assert response.status_code == 200
            assert b"E2E Test Project" in response.data
            assert b"Overview" in response.data
            assert b"Documents" in response.data
            assert b"Export JSON" in response.data
            assert b"Export" in response.data

            # 3. Create a user story
            response = client.post(
                f"/projects/{pid}/documents/new/user_story",
                data={
                    "user_type": "developer",
                    "action": "run the full workflow",
                    "benefit": "ensure everything works",
                    "priority": "high",
                    "status": "draft",
                    "acceptance_criteria": ["All steps pass", "Export is valid"],
                },
                follow_redirects=True,
            )
            assert response.status_code == 200
            assert b"developer" in response.data

            # 4. Create a requirement
            response = client.post(
                f"/projects/{pid}/documents/new/requirement",
                data={
                    "title": "E2E Requirement",
                    "description": "System must support full workflow",
                    "req_type": "functional",
                    "category": "Integration",
                    "priority": "must",
                    "status": "approved",
                    "rationale": "Core functionality",
                },
                follow_redirects=True,
            )
            assert response.status_code == 200
            assert b"E2E Requirement" in response.data

            # 5. Create a project plan
            response = client.post(
                f"/projects/{pid}/documents/new/project_plan",
                data={
                    "project_name": "E2E Plan",
                    "project_description": "Plan for E2E testing",
                    "goals": ["Complete E2E test"],
                    "in_scope": ["All artifact types"],
                    "out_scope": ["Performance testing"],
                    "milestone_name": ["v1.0"],
                    "milestone_date": ["2026-06-01"],
                    "milestone_deliverables": ["MVP"],
                    "milestone_status": ["planned"],
                    "risk_description": ["Scope creep"],
                    "risk_likelihood": ["medium"],
                    "risk_impact": ["high"],
                    "risk_mitigation": ["Stay focused"],
                },
                follow_redirects=True,
            )
            assert response.status_code == 200
            assert b"E2E Plan" in response.data

            # 6. Create a test plan
            response = client.post(
                f"/projects/{pid}/documents/new/test_plan",
                data={
                    "test_scope": "Full system test",
                    "test_strategy": "End-to-end via HTTP client",
                    "case_description": ["Full workflow"],
                    "case_test_name": ["test_full_workflow"],
                    "case_steps": ["Create, add, export"],
                    "case_expected": ["All pass"],
                    "case_status": ["not_run"],
                    "entry_criteria": "Code complete",
                    "exit_criteria": "All tests green",
                    "environment": "Python 3.10, Supabase",
                },
                follow_redirects=True,
            )
            assert response.status_code == 200
            assert b"Full system test" in response.data

            # 7. Create a diagram
            response = client.post(
                f"/projects/{pid}/diagrams/new",
                data={"name": "E2E Architecture", "type": "architecture"},
                follow_redirects=True,
            )
            assert response.status_code == 200
            assert b"E2E Architecture" in response.data

            diagram = DiagramService.get_all_for_project(pid)[0]
            response = client.put(
                f"/api/diagrams/{diagram.id}",
                json={
                    "data": {
                        "nodes": [
                            {"id": "1", "type": "component", "position": {"x": 0, "y": 0}, "data": {"label": "Service A"}},
                            {"id": "2", "type": "component", "position": {"x": 200, "y": 0}, "data": {"label": "Service B"}},
                        ],
                        "edges": [{"id": "e1-2", "source": "1", "target": "2", "label": "REST"}],
                    },
                },
            )
            assert response.status_code == 200

            # 8. Create an API endpoint
            response = client.post(
                f"/projects/{pid}/api-endpoints/new",
                data={
                    "path": "/api/e2e/test",
                    "method": "POST",
                    "description": "E2E test endpoint",
                    "param_name": ["id"],
                    "param_location": ["path"],
                    "param_type": ["string"],
                    "param_required": ["0"],
                    "param_description": ["Resource ID"],
                    "request_body": '{"type": "object"}',
                    "response_body": '{"type": "object"}',
                    "status_code": ["200", "404"],
                    "status_description": ["OK", "Not Found"],
                },
                follow_redirects=True,
            )
            assert response.status_code == 200
            assert b"/api/e2e/test" in response.data

            # 9. Export as JSON
            response = client.get(f"/api/projects/{pid}/export?format=json")
            assert response.status_code == 200
            data = response.get_json()

            assert data["project"] == "E2E Test Project"
            assert data["description"] == "Full workflow test"
            assert len(data["user_stories"]) == 1
            assert len(data["requirements"]) == 1
            assert len(data["project_plans"]) == 1
            assert len(data["test_plans"]) == 1
            assert len(data["diagrams"]) == 1
            assert len(data["api_endpoints"]) == 1
            assert data["user_stories"][0]["as_a"] == "developer"
            assert data["requirements"][0]["title"] == "E2E Requirement"
            assert data["project_plans"][0]["project_name"] == "E2E Plan"
            assert data["test_plans"][0]["test_scope"] == "Full system test"
            assert data["diagrams"][0]["name"] == "E2E Architecture"
            assert len(data["diagrams"][0]["nodes"]) == 2
            assert data["api_endpoints"][0]["path"] == "/api/e2e/test"

            # 10. Export as Markdown
            response = client.get(f"/api/projects/{pid}/export?format=markdown")
            assert response.status_code == 200
            assert response.content_type.startswith("text/markdown")
            md = response.data.decode("utf-8")
            assert "# E2E Test Project" in md
            assert "## Requirements" in md
            assert "## User Stories" in md
            assert "`POST /api/e2e/test`" in md

        finally:
            if pid:
                try:
                    project = ProjectService.get(pid)
                    if project:
                        ProjectService.delete(project)
                except Exception:
                    pass

    def test_sidebar_navigation_present(self, client, project):
        pid = project.id
        pages = [
            f"/projects/{pid}",
            f"/projects/{pid}/documents",
            f"/projects/{pid}/diagrams",
            f"/projects/{pid}/api-endpoints",
        ]
        for url in pages:
            response = client.get(url)
            assert response.status_code == 200, f"Failed on {url}"
            # New design uses "Deep Dock" sidebar with Tailwind classes
            assert b"Overview" in response.data, f"No sidebar on {url}"
            assert b"Projects" in response.data, f"No breadcrumb on {url}"

    def test_breadcrumb_on_nested_pages(self, client, project):
        pid = project.id
        doc = DocumentService.create(
            project_id=pid, doc_type="requirement",
            data={"title": "Test Req", "description": "Testing breadcrumbs"},
        )
        response = client.get(f"/projects/{pid}/documents/{doc.id}")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Projects" in html
        assert project.name in html
        assert "Documents" in html
        assert "Test Req" in html

    def test_dashboard_shows_artifact_counts(self, client, project):
        pid = project.id
        DocumentService.create(project_id=pid, doc_type="user_story", data={"user_type": "dev", "action": "test", "benefit": "quality"})
        DocumentService.create(project_id=pid, doc_type="requirement", data={"title": "R1", "description": "Req"})
        DiagramService.create(project_id=pid, diagram_type="architecture", name="D1")

        response = client.get("/")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert project.name in html
        # The new dashboard shows counts as separate numbers under labels
        assert "Documents" in html
        assert "Diagrams" in html
        assert "Endpoints" in html
