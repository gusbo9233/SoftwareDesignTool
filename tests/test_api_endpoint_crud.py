import pytest
from app.services.api_endpoint_service import APIEndpointService


class TestAPIEndpointService:
    def test_create_endpoint(self, project_id):
        ep = APIEndpointService.create(
            project_id=project_id, path="/api/users", method="GET",
            description="List all users",
        )
        assert ep.id is not None
        assert ep.path == "/api/users"
        assert ep.method == "GET"
        assert ep.description == "List all users"

    def test_create_with_schemas(self, project_id):
        req = {"parameters": [{"name": "id", "location": "path", "type": "string"}], "body": ""}
        resp = {"body": '{"type": "object"}', "status_codes": [{"code": "200", "description": "OK"}]}
        ep = APIEndpointService.create(
            project_id=project_id, path="/api/users/{id}", method="GET",
            request_schema=req, response_schema=resp,
        )
        assert len(ep.request_schema["parameters"]) == 1
        assert ep.response_schema["status_codes"][0]["code"] == "200"

    def test_get_endpoint(self, project_id):
        created = APIEndpointService.create(
            project_id=project_id, path="/api/items", method="POST",
        )
        found = APIEndpointService.get(created.id)
        assert found is not None
        assert found.path == "/api/items"

    def test_get_nonexistent(self):
        assert APIEndpointService.get("00000000-0000-0000-0000-000000000000") is None

    def test_get_all_for_project(self, project_id):
        APIEndpointService.create(project_id=project_id, path="/api/a", method="GET")
        APIEndpointService.create(project_id=project_id, path="/api/b", method="POST")
        endpoints = APIEndpointService.get_all_for_project(project_id)
        assert len(endpoints) == 2

    def test_update_endpoint(self, project_id):
        ep = APIEndpointService.create(
            project_id=project_id, path="/api/old", method="GET",
        )
        APIEndpointService.update(ep, path="/api/new", method="POST", description="Updated")
        refreshed = APIEndpointService.get(ep.id)
        assert refreshed.path == "/api/new"
        assert refreshed.method == "POST"
        assert refreshed.description == "Updated"

    def test_delete_endpoint(self, project_id):
        ep = APIEndpointService.create(
            project_id=project_id, path="/api/del", method="DELETE",
        )
        eid = ep.id
        APIEndpointService.delete(ep)
        assert APIEndpointService.get(eid) is None


class TestAPIEndpointRoutes:
    def test_index(self, client, project_id):
        response = client.get(f"/projects/{project_id}/api-endpoints")
        assert response.status_code == 200
        assert b"API Endpoints" in response.data

    def test_create_get(self, client, project_id):
        response = client.get(f"/projects/{project_id}/api-endpoints/new")
        assert response.status_code == 200
        assert b"New" in response.data
        assert b"API Endpoint" in response.data

    def test_create_post(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/api-endpoints/new",
            data={"path": "/api/users", "method": "GET", "description": "List users"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"/api/users" in response.data

    def test_create_empty_path(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/api-endpoints/new",
            data={"path": "", "method": "GET"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"required" in response.data

    def test_create_invalid_method(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/api-endpoints/new",
            data={"path": "/api/test", "method": "INVALID"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Invalid" in response.data

    def test_detail(self, client, project_id):
        ep = APIEndpointService.create(
            project_id=project_id, path="/api/detail-test", method="GET",
            description="Detail test endpoint",
        )
        response = client.get(f"/projects/{project_id}/api-endpoints/{ep.id}")
        assert response.status_code == 200
        assert b"/api/detail-test" in response.data
        assert b"Detail test endpoint" in response.data

    def test_detail_not_found(self, client, project_id):
        response = client.get(
            f"/projects/{project_id}/api-endpoints/00000000-0000-0000-0000-000000000000",
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"not found" in response.data

    def test_edit_get(self, client, project_id):
        ep = APIEndpointService.create(
            project_id=project_id, path="/api/edit-test", method="PUT",
        )
        response = client.get(f"/projects/{project_id}/api-endpoints/{ep.id}/edit")
        assert response.status_code == 200
        assert b"/api/edit-test" in response.data
        assert b"Edit" in response.data

    def test_edit_post(self, client, project_id):
        ep = APIEndpointService.create(
            project_id=project_id, path="/api/old-path", method="GET",
        )
        response = client.post(
            f"/projects/{project_id}/api-endpoints/{ep.id}/edit",
            data={"path": "/api/new-path", "method": "POST", "description": "Updated"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"/api/new-path" in response.data

    def test_delete(self, client, project_id):
        ep = APIEndpointService.create(
            project_id=project_id, path="/api/delete-me", method="DELETE",
        )
        response = client.post(
            f"/projects/{project_id}/api-endpoints/{ep.id}/delete",
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"/api/delete-me" not in response.data

    def test_create_with_parameters(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/api-endpoints/new",
            data={
                "path": "/api/users/{id}",
                "method": "GET",
                "description": "Get user by ID",
                "param_name": ["id"],
                "param_location": ["path"],
                "param_type": ["string"],
                "param_required": ["0"],
                "param_description": ["User identifier"],
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"/api/users/{id}" in response.data

    def test_create_with_status_codes(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/api-endpoints/new",
            data={
                "path": "/api/items",
                "method": "POST",
                "description": "Create item",
                "status_code": ["201", "400"],
                "status_description": ["Created", "Bad Request"],
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"/api/items" in response.data

    def test_detail_shows_parameters(self, client, project_id):
        ep = APIEndpointService.create(
            project_id=project_id, path="/api/test", method="GET",
            request_schema={
                "parameters": [{"name": "page", "location": "query", "type": "integer", "required": False, "description": "Page number"}],
                "body": "",
            },
            response_schema={"body": "", "status_codes": [{"code": "200", "description": "OK"}]},
        )
        response = client.get(f"/projects/{project_id}/api-endpoints/{ep.id}")
        assert response.status_code == 200
        assert b"page" in response.data
        assert b"Page number" in response.data
        assert b"200" in response.data
