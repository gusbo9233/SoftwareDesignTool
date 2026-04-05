import pytest
from pydantic import ValidationError
from app import create_app, db
from app.services.project_service import ProjectService
from app.services.document_service import DocumentService
from app.schemas.document import (
    UserStoryData, RequirementData, ProjectPlanData, TestPlanData,
)


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
        p = ProjectService.create(name="Test Project", description="For document tests")
        return p.id


class TestDocumentService:
    def test_create_user_story(self, app, project_id):
        with app.app_context():
            doc = DocumentService.create(
                project_id=project_id,
                doc_type="user_story",
                data={"user_type": "developer", "action": "write code", "benefit": "ship features"},
            )
            assert doc.id is not None
            assert doc.type == "user_story"
            assert doc.data["user_type"] == "developer"

    def test_create_requirement(self, app, project_id):
        with app.app_context():
            doc = DocumentService.create(
                project_id=project_id,
                doc_type="requirement",
                data={"title": "Auth", "description": "JWT authentication"},
            )
            assert doc.type == "requirement"
            assert doc.data["title"] == "Auth"

    def test_create_project_plan(self, app, project_id):
        with app.app_context():
            doc = DocumentService.create(
                project_id=project_id,
                doc_type="project_plan",
                data={"project_name": "My Plan", "goals": ["Goal 1"]},
            )
            assert doc.type == "project_plan"
            assert doc.data["goals"] == ["Goal 1"]

    def test_create_test_plan(self, app, project_id):
        with app.app_context():
            doc = DocumentService.create(
                project_id=project_id,
                doc_type="test_plan",
                data={"test_scope": "API layer"},
            )
            assert doc.type == "test_plan"
            assert doc.data["test_scope"] == "API layer"

    def test_get_document(self, app, project_id):
        with app.app_context():
            created = DocumentService.create(project_id=project_id, doc_type="user_story", data={"user_type": "admin", "action": "manage", "benefit": "control"})
            found = DocumentService.get(created.id)
            assert found is not None
            assert found.data["user_type"] == "admin"

    def test_get_nonexistent(self, app):
        with app.app_context():
            assert DocumentService.get("nonexistent") is None

    def test_get_all_for_project(self, app, project_id):
        with app.app_context():
            DocumentService.create(project_id=project_id, doc_type="user_story", data={"user_type": "a", "action": "b", "benefit": "c"})
            DocumentService.create(project_id=project_id, doc_type="requirement", data={"title": "t", "description": "d"})
            docs = DocumentService.get_all_for_project(project_id)
            assert len(docs) == 2

    def test_get_all_filtered_by_type(self, app, project_id):
        with app.app_context():
            DocumentService.create(project_id=project_id, doc_type="user_story", data={})
            DocumentService.create(project_id=project_id, doc_type="requirement", data={})
            docs = DocumentService.get_all_for_project(project_id, doc_type="user_story")
            assert len(docs) == 1
            assert docs[0].type == "user_story"

    def test_update_document(self, app, project_id):
        with app.app_context():
            doc = DocumentService.create(project_id=project_id, doc_type="user_story", data={"user_type": "old"})
            DocumentService.update(doc, data={"user_type": "new", "action": "test", "benefit": "test"})
            refreshed = DocumentService.get(doc.id)
            assert refreshed.data["user_type"] == "new"

    def test_delete_document(self, app, project_id):
        with app.app_context():
            doc = DocumentService.create(project_id=project_id, doc_type="user_story", data={})
            did = doc.id
            DocumentService.delete(doc)
            assert DocumentService.get(did) is None


class TestDocumentRoutes:
    def test_documents_index(self, client, project_id):
        response = client.get(f"/projects/{project_id}/documents")
        assert response.status_code == 200
        assert b"Documents" in response.data

    def test_create_user_story_get(self, client, project_id):
        response = client.get(f"/projects/{project_id}/documents/new/user_story")
        assert response.status_code == 200
        assert b"User Story" in response.data

    def test_create_user_story_post(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/documents/new/user_story",
            data={
                "user_type": "developer",
                "action": "write tests",
                "benefit": "ensure quality",
                "priority": "high",
                "status": "draft",
                "acceptance_criteria": ["Tests pass", "Coverage > 80%"],
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"developer" in response.data

    def test_create_user_story_missing_fields(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/documents/new/user_story",
            data={"user_type": "", "action": "", "benefit": ""},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"required" in response.data

    def test_create_requirement_post(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/documents/new/requirement",
            data={
                "title": "Auth Required",
                "description": "All endpoints need auth",
                "req_type": "functional",
                "category": "Security",
                "priority": "must",
                "status": "draft",
                "rationale": "Multi-tenant system",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Auth Required" in response.data

    def test_create_requirement_missing_title(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/documents/new/requirement",
            data={"title": "", "description": ""},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"required" in response.data

    def test_create_project_plan_post(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/documents/new/project_plan",
            data={
                "project_name": "My Plan",
                "project_description": "A test plan",
                "goals": ["Goal 1", "Goal 2"],
                "in_scope": ["Feature A"],
                "out_scope": ["Feature B"],
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"My Plan" in response.data

    def test_create_test_plan_post(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/documents/new/test_plan",
            data={
                "test_scope": "API endpoints",
                "test_strategy": "Unit and integration",
                "entry_criteria": "Code complete",
                "exit_criteria": "All tests pass",
                "environment": "Python 3.11, SQLite",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"API endpoints" in response.data

    def test_document_detail(self, client, app, project_id):
        with app.app_context():
            doc = DocumentService.create(
                project_id=project_id, doc_type="user_story",
                data={"user_type": "admin", "action": "manage users", "benefit": "control access"},
            )
            did = doc.id
        response = client.get(f"/projects/{project_id}/documents/{did}")
        assert response.status_code == 200
        assert b"admin" in response.data

    def test_document_detail_not_found(self, client, project_id):
        response = client.get(f"/projects/{project_id}/documents/nonexistent", follow_redirects=True)
        assert response.status_code == 200
        assert b"not found" in response.data

    def test_edit_document(self, client, app, project_id):
        with app.app_context():
            doc = DocumentService.create(
                project_id=project_id, doc_type="requirement",
                data={"title": "Old Title", "description": "Old desc"},
            )
            did = doc.id
        response = client.post(
            f"/projects/{project_id}/documents/{did}/edit",
            data={"title": "New Title", "description": "New desc", "req_type": "functional", "priority": "must", "status": "approved", "category": "", "rationale": ""},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"New Title" in response.data

    def test_delete_document_route(self, client, app, project_id):
        with app.app_context():
            doc = DocumentService.create(
                project_id=project_id, doc_type="user_story",
                data={"user_type": "tester", "action": "test", "benefit": "quality"},
            )
            did = doc.id
        response = client.post(f"/projects/{project_id}/documents/{did}/delete", follow_redirects=True)
        assert response.status_code == 200

    def test_invalid_doc_type(self, client, project_id):
        response = client.get(f"/projects/{project_id}/documents/new/invalid", follow_redirects=True)
        assert response.status_code == 200
        assert b"Invalid" in response.data


class TestDocumentSchemas:
    def test_user_story_valid(self):
        data = UserStoryData(user_type="dev", action="code", benefit="ship")
        assert data.priority == "medium"

    def test_user_story_missing_required(self):
        with pytest.raises(ValidationError):
            UserStoryData(user_type="", action="code", benefit="ship")

    def test_requirement_valid(self):
        data = RequirementData(title="Auth", description="JWT auth")
        assert data.type == "functional"
        assert data.priority == "should"

    def test_requirement_invalid_priority(self):
        with pytest.raises(ValidationError):
            RequirementData(title="Auth", description="JWT", priority="invalid")

    def test_project_plan_valid(self):
        data = ProjectPlanData(project_name="Plan", goals=["G1"])
        assert data.milestones == []

    def test_project_plan_missing_name(self):
        with pytest.raises(ValidationError):
            ProjectPlanData(project_name="")

    def test_test_plan_valid(self):
        data = TestPlanData(test_scope="All APIs")
        assert data.test_cases == []

    def test_test_plan_missing_scope(self):
        with pytest.raises(ValidationError):
            TestPlanData(test_scope="")
