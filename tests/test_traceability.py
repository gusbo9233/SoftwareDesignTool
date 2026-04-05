"""Tests for requirement-to-acceptance-test traceability links."""
import pytest
from app.services.document_service import DocumentService
from app.services.traceability_service import TraceabilityService
from app.export.export_service import ExportService


@pytest.fixture
def req_id(project_id):
    doc = DocumentService.create(
        project_id=project_id,
        doc_type="requirement",
        data={"title": "Auth Required", "description": "All endpoints need auth"},
    )
    return doc.id


@pytest.fixture
def us_id(project_id):
    doc = DocumentService.create(
        project_id=project_id,
        doc_type="user_story",
        data={"user_type": "developer", "action": "log in", "benefit": "access the system"},
    )
    return doc.id


@pytest.fixture
def at_id(project_id):
    doc = DocumentService.create(
        project_id=project_id,
        doc_type="acceptance_test",
        data={"title": "Login succeeds", "steps": ["Enter creds"], "expected_result": "Redirect to dashboard"},
    )
    return doc.id


class TestTraceabilityService:
    def test_create_link_requirement(self, req_id, at_id):
        link = TraceabilityService.create_link(
            acceptance_test_id=at_id,
            requirement_id=req_id,
        )
        assert link.id is not None
        assert link.acceptance_test_id == at_id
        assert link.requirement_id == req_id
        assert link.user_story_id is None

    def test_create_link_user_story(self, us_id, at_id):
        link = TraceabilityService.create_link(
            acceptance_test_id=at_id,
            user_story_id=us_id,
        )
        assert link.user_story_id == us_id
        assert link.requirement_id is None

    def test_get_links_for_acceptance_test(self, req_id, at_id):
        TraceabilityService.create_link(acceptance_test_id=at_id, requirement_id=req_id)
        links = TraceabilityService.get_links_for_acceptance_test(at_id)
        assert len(links) == 1
        assert links[0].requirement_id == req_id

    def test_get_links_for_requirement(self, req_id, at_id):
        TraceabilityService.create_link(acceptance_test_id=at_id, requirement_id=req_id)
        links = TraceabilityService.get_links_for_requirement(req_id)
        assert len(links) == 1
        assert links[0].acceptance_test_id == at_id

    def test_get_links_for_user_story(self, us_id, at_id):
        TraceabilityService.create_link(acceptance_test_id=at_id, user_story_id=us_id)
        links = TraceabilityService.get_links_for_user_story(us_id)
        assert len(links) == 1

    def test_delete_link(self, req_id, at_id):
        link = TraceabilityService.create_link(acceptance_test_id=at_id, requirement_id=req_id)
        link_id = link.id
        TraceabilityService.delete_link(link)
        assert TraceabilityService.get_link(link_id) is None

    def test_get_nonexistent_link(self):
        assert TraceabilityService.get_link("00000000-0000-0000-0000-000000000000") is None

    def test_traceability_map(self, project_id, req_id, us_id, at_id):
        TraceabilityService.create_link(acceptance_test_id=at_id, requirement_id=req_id)
        TraceabilityService.create_link(acceptance_test_id=at_id, user_story_id=us_id)
        traceability = TraceabilityService.get_traceability_map(project_id)
        assert len(traceability) == 1
        entry = traceability[0]
        assert entry["acceptance_test_id"] == at_id
        assert req_id in entry["requirement_ids"]
        assert us_id in entry["user_story_ids"]


class TestTraceabilityRoutes:
    def test_add_link_via_route(self, client, project_id, req_id, at_id):
        response = client.post(
            f"/projects/{project_id}/traceability",
            data={
                "acceptance_test_id": at_id,
                "requirement_id": req_id,
                "user_story_id": "",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        links = TraceabilityService.get_links_for_acceptance_test(at_id)
        assert len(links) == 1

    def test_add_link_no_source_redirects_with_error(self, client, project_id, at_id):
        response = client.post(
            f"/projects/{project_id}/traceability",
            data={
                "acceptance_test_id": at_id,
                "requirement_id": "",
                "user_story_id": "",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Select at least one" in response.data

    def test_delete_link_via_route(self, client, project_id, req_id, at_id):
        link = TraceabilityService.create_link(acceptance_test_id=at_id, requirement_id=req_id)
        link_id = link.id
        response = client.post(
            f"/projects/{project_id}/traceability/{link_id}/delete",
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert TraceabilityService.get_link(link_id) is None


class TestTraceabilityExportIntegration:
    def test_export_includes_traceability(self, project_id, req_id, at_id):
        TraceabilityService.create_link(acceptance_test_id=at_id, requirement_id=req_id)
        result = ExportService.export_json(project_id)
        assert result is not None
        assert len(result["traceability"]) == 1
        entry = result["traceability"][0]
        assert entry["acceptance_test_id"] == at_id
        assert req_id in entry["requirement_ids"]

    def test_export_markdown_includes_traceability(self, project_id, req_id, at_id):
        TraceabilityService.create_link(acceptance_test_id=at_id, requirement_id=req_id)
        md = ExportService.export_markdown(project_id)
        assert md is not None
        assert "Traceability" in md

    def test_acceptance_test_detail_shows_traceability_panel(self, client, project_id, req_id, at_id):
        TraceabilityService.create_link(acceptance_test_id=at_id, requirement_id=req_id)
        response = client.get(f"/projects/{project_id}/documents/{at_id}")
        assert response.status_code == 200
        assert b"Traceability" in response.data
