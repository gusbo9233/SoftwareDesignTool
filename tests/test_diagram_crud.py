import json
import pytest
from app.services.diagram_service import DiagramService


class TestDiagramService:
    def test_create_diagram(self, project_id):
        d = DiagramService.create(
            project_id=project_id, diagram_type="architecture", name="System Overview"
        )
        assert d.id is not None
        assert d.type == "architecture"
        assert d.name == "System Overview"
        assert d.data == {"nodes": [], "edges": []}

    def test_create_with_data(self, project_id):
        data = {
            "nodes": [{"id": "1", "type": "component", "position": {"x": 0, "y": 0}, "data": {"label": "A"}}],
            "edges": [],
        }
        d = DiagramService.create(
            project_id=project_id, diagram_type="er", name="ER Diagram", data=data
        )
        assert len(d.data["nodes"]) == 1

    def test_get_diagram(self, project_id):
        created = DiagramService.create(project_id=project_id, diagram_type="workflow", name="Flow")
        found = DiagramService.get(created.id)
        assert found is not None
        assert found.name == "Flow"

    def test_get_nonexistent(self):
        assert DiagramService.get("00000000-0000-0000-0000-000000000000") is None

    def test_get_all_for_project(self, project_id):
        DiagramService.create(project_id=project_id, diagram_type="architecture", name="A")
        DiagramService.create(project_id=project_id, diagram_type="er", name="B")
        diagrams = DiagramService.get_all_for_project(project_id)
        assert len(diagrams) == 2

    def test_update_diagram(self, project_id):
        d = DiagramService.create(project_id=project_id, diagram_type="architecture", name="Old")
        new_data = {"nodes": [{"id": "1", "position": {"x": 50, "y": 50}, "data": {"label": "Updated"}}], "edges": []}
        DiagramService.update(d, name="New Name", data=new_data)
        refreshed = DiagramService.get(d.id)
        assert refreshed.name == "New Name"
        assert len(refreshed.data["nodes"]) == 1

    def test_delete_diagram(self, project_id):
        d = DiagramService.create(project_id=project_id, diagram_type="architecture", name="Del")
        did = d.id
        DiagramService.delete(d)
        assert DiagramService.get(did) is None


class TestDiagramRoutes:
    def test_diagrams_index(self, client, project_id):
        response = client.get(f"/projects/{project_id}/diagrams")
        assert response.status_code == 200
        assert b"Diagrams" in response.data

    def test_create_diagram_get(self, client, project_id):
        response = client.get(f"/projects/{project_id}/diagrams/new")
        assert response.status_code == 200
        assert b"New Diagram" in response.data

    def test_create_diagram_post(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/diagrams/new",
            data={"name": "My Diagram", "type": "architecture"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"My Diagram" in response.data

    def test_create_diagram_empty_name(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/diagrams/new",
            data={"name": "", "type": "architecture"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"required" in response.data

    def test_create_diagram_invalid_type(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/diagrams/new",
            data={"name": "Test", "type": "invalid"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Invalid" in response.data

    def test_diagram_editor(self, client, project_id):
        d = DiagramService.create(project_id=project_id, diagram_type="architecture", name="Edit Test")
        response = client.get(f"/projects/{project_id}/diagrams/{d.id}")
        assert response.status_code == 200
        assert b"Edit Test" in response.data
        assert b"diagram-editor" in response.data

    def test_diagram_editor_not_found(self, client, project_id):
        response = client.get(f"/projects/{project_id}/diagrams/00000000-0000-0000-0000-000000000000", follow_redirects=True)
        assert response.status_code == 200
        assert b"not found" in response.data

    def test_delete_diagram_route(self, client, project_id):
        d = DiagramService.create(project_id=project_id, diagram_type="er", name="Delete Me")
        response = client.post(f"/projects/{project_id}/diagrams/{d.id}/delete", follow_redirects=True)
        assert response.status_code == 200
        assert b"Delete Me" not in response.data


class TestDiagramAPI:
    def test_api_get(self, client, project_id):
        d = DiagramService.create(project_id=project_id, diagram_type="architecture", name="API Test")
        response = client.get(f"/api/diagrams/{d.id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "API Test"
        assert data["data"]["nodes"] == []

    def test_api_get_not_found(self, client):
        response = client.get("/api/diagrams/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    def test_api_update(self, client, project_id):
        d = DiagramService.create(project_id=project_id, diagram_type="architecture", name="Update Me")
        new_data = {
            "nodes": [{"id": "1", "type": "component", "position": {"x": 100, "y": 100}, "data": {"label": "Service"}}],
            "edges": [],
        }
        response = client.put(
            f"/api/diagrams/{d.id}",
            data=json.dumps({"data": new_data}),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.get_json()["status"] == "ok"

        get_resp = client.get(f"/api/diagrams/{d.id}")
        assert len(get_resp.get_json()["data"]["nodes"]) == 1

    def test_api_update_not_found(self, client):
        response = client.put(
            "/api/diagrams/00000000-0000-0000-0000-000000000000",
            data=json.dumps({"data": {}}),
            content_type="application/json",
        )
        assert response.status_code == 404

    def test_api_update_name(self, client, project_id):
        d = DiagramService.create(project_id=project_id, diagram_type="workflow", name="Old Name")
        response = client.put(
            f"/api/diagrams/{d.id}",
            data=json.dumps({"name": "New Name"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        get_resp = client.get(f"/api/diagrams/{d.id}")
        assert get_resp.get_json()["name"] == "New Name"

    def test_api_update_invalid_json(self, client, project_id):
        d = DiagramService.create(project_id=project_id, diagram_type="architecture", name="Test")
        response = client.put(f"/api/diagrams/{d.id}", data="not json", content_type="text/plain")
        assert response.status_code in (400, 415)
