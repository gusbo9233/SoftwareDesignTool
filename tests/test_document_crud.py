import pytest
from pydantic import ValidationError
from app.services.document_service import DocumentService
from app.services.test_result_service import TestResultService
from app.schemas.document import (
    UserStoryData, RequirementData, ProjectPlanData, TestPlanData,
)


class TestDocumentService:
    def test_create_user_story(self, project_id):
        doc = DocumentService.create(
            project_id=project_id,
            doc_type="user_story",
            data={"user_type": "developer", "action": "write code", "benefit": "ship features"},
        )
        assert doc.id is not None
        assert doc.type == "user_story"
        assert doc.data["user_type"] == "developer"

    def test_create_requirement(self, project_id):
        doc = DocumentService.create(
            project_id=project_id,
            doc_type="requirement",
            data={"title": "Auth", "description": "JWT authentication"},
        )
        assert doc.type == "requirement"
        assert doc.data["title"] == "Auth"

    def test_create_project_plan(self, project_id):
        doc = DocumentService.create(
            project_id=project_id,
            doc_type="project_plan",
            data={"project_name": "My Plan", "goals": ["Goal 1"]},
        )
        assert doc.type == "project_plan"
        assert doc.data["goals"] == ["Goal 1"]

    def test_create_test_plan(self, project_id):
        doc = DocumentService.create(
            project_id=project_id,
            doc_type="test_plan",
            data={"test_scope": "API layer"},
        )
        assert doc.type == "test_plan"
        assert doc.data["test_scope"] == "API layer"

    def test_get_document(self, project_id):
        created = DocumentService.create(
            project_id=project_id, doc_type="user_story",
            data={"user_type": "admin", "action": "manage", "benefit": "control"},
        )
        found = DocumentService.get(created.id)
        assert found is not None
        assert found.data["user_type"] == "admin"

    def test_get_nonexistent(self):
        assert DocumentService.get("00000000-0000-0000-0000-000000000000") is None

    def test_get_all_for_project(self, project_id):
        DocumentService.create(project_id=project_id, doc_type="user_story", data={"user_type": "a", "action": "b", "benefit": "c"})
        DocumentService.create(project_id=project_id, doc_type="requirement", data={"title": "t", "description": "d"})
        docs = DocumentService.get_all_for_project(project_id)
        assert len(docs) == 2

    def test_get_all_filtered_by_type(self, project_id):
        DocumentService.create(project_id=project_id, doc_type="user_story", data={})
        DocumentService.create(project_id=project_id, doc_type="requirement", data={})
        docs = DocumentService.get_all_for_project(project_id, doc_type="user_story")
        assert len(docs) == 1
        assert docs[0].type == "user_story"

    def test_update_document(self, project_id):
        doc = DocumentService.create(project_id=project_id, doc_type="user_story", data={"user_type": "old"})
        DocumentService.update(doc, data={"user_type": "new", "action": "test", "benefit": "test"})
        refreshed = DocumentService.get(doc.id)
        assert refreshed.data["user_type"] == "new"

    def test_delete_document(self, project_id):
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
        response = client.get(f"/projects/{project_id}/documents/new/user_story", follow_redirects=True)
        assert response.status_code == 200
        assert b"User Stories" in response.data
        assert b"Add Story" in response.data

    def test_create_user_story_post(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/documents/new/user_story",
            data={
                "user_type": "developer",
                "action": "write tests",
                "benefit": "ensure quality",
                "acceptance_criteria": ["Tests pass", "Coverage > 80%"],
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"developer" in response.data

    def test_create_multi_user_story_post(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/documents/new/user_story",
            data={
                "story_user_type": ["developer", "admin"],
                "story_action": ["write tests", "manage users"],
                "story_benefit": ["ensure quality", "control access"],
                "story_acceptance_criteria": ["Tests pass\nCoverage > 80%", "Users can be assigned roles"],
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Story 1" in response.data
        assert b"Story 2" in response.data
        assert b"manage users" in response.data

    def test_create_user_story_reuses_single_document(self, client, project_id):
        first = client.post(
            f"/projects/{project_id}/documents/new/user_story",
            data={
                "story_user_type": ["developer"],
                "story_action": ["write tests"],
                "story_benefit": ["ensure quality"],
                "story_acceptance_criteria": ["Tests pass"],
            },
            follow_redirects=True,
        )
        assert first.status_code == 200

        second = client.post(
            f"/projects/{project_id}/documents/new/user_story",
            data={
                "story_user_type": ["admin"],
                "story_action": ["manage users"],
                "story_benefit": ["control access"],
                "story_acceptance_criteria": ["Roles can be assigned"],
            },
            follow_redirects=True,
        )
        assert second.status_code == 200
        assert b"Story 2" in second.data

        docs = DocumentService.get_all_for_project(project_id, doc_type="user_story")
        assert len(docs) == 1
        assert len(docs[0].data["stories"]) == 2

    def test_add_user_story_from_detail_page(self, client, project_id):
        response = client.get(f"/projects/{project_id}/documents/new/user_story", follow_redirects=True)
        assert response.status_code == 200

        docs = DocumentService.get_all_for_project(project_id, doc_type="user_story")
        assert len(docs) == 1
        doc = docs[0]

        response = client.post(
            f"/projects/{project_id}/documents/{doc.id}/user-stories/add",
            data={
                "user_type": "learner",
                "action": "practice vocabulary",
                "benefit": "learn language",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"practice vocabulary" in response.data
        assert b"Priority" not in response.data
        assert b"Acceptance Criteria" not in response.data

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
                "tags": ["unit", "integration"],
                "custom_tags": "api",
                "test_strategy": "Unit and integration",
                "case_description": ["Valid login test"],
                "case_test_name": ["login_valid_credentials"],
                "case_steps": ["Submit valid credentials"],
                "case_expected": ["Dashboard is shown"],
                "case_status": ["not_run"],
                "entry_criteria": "Code complete",
                "exit_criteria": "All tests pass",
                "environment": "Python 3.11, Supabase",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"API endpoints" in response.data
        assert b"unit" in response.data
        assert b"integration" in response.data
        assert b"login_valid_credentials" in response.data

    def test_create_test_plan_requires_test_name_per_case(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/documents/new/test_plan",
            data={
                "test_scope": "API endpoints",
                "case_description": ["Valid login test"],
                "case_test_name": [""],
                "case_steps": ["Submit valid credentials"],
                "case_expected": ["Dashboard is shown"],
                "case_status": ["not_run"],
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Each test case requires a test name." in response.data

    def test_create_multiple_test_plans(self, client, project_id):
        first = client.post(
            f"/projects/{project_id}/documents/new/test_plan",
            data={
                "test_scope": "Core unit test plan",
                "tags": ["unit"],
            },
            follow_redirects=True,
        )
        assert first.status_code == 200

        second = client.post(
            f"/projects/{project_id}/documents/new/test_plan",
            data={
                "test_scope": "Critical flow end-to-end plan",
                "tags": ["e2e"],
            },
            follow_redirects=True,
        )
        assert second.status_code == 200

        docs = DocumentService.get_all_for_project(project_id, doc_type="test_plan")
        assert len(docs) == 2

    def test_document_detail(self, client, project_id):
        doc = DocumentService.create(
            project_id=project_id, doc_type="user_story",
            data={"user_type": "admin", "action": "manage users", "benefit": "control access"},
        )
        response = client.get(f"/projects/{project_id}/documents/{doc.id}")
        assert response.status_code == 200
        assert b"admin" in response.data

    def test_test_plan_detail_shows_latest_ci_result_per_test_case(self, client, project):
        doc = DocumentService.create(
            project_id=project.id,
            doc_type="test_plan",
            data={
                "test_scope": "Calculator",
                "test_cases": [
                    {"test_name": "test_add", "description": "adding two numbers", "test_uid": "039a3612", "steps": "", "expected_result": "", "status": "not_run"},
                    {"test_name": "test_divide", "description": "dividing two numbers", "test_uid": "f08e363a", "steps": "", "expected_result": "", "status": "not_run"},
                ],
            },
        )
        run = TestResultService.create_run(
            project_id=project.id,
            github_run_id=321,
            branch="main",
            commit_sha="4ac1e2c",
            status="completed",
            conclusion="success",
            run_url="https://github.com/example/run/321",
            total_tests=2,
            passed=2,
            failed=0,
            skipped=0,
        )
        TestResultService.create_results(run.id, [
            {"test_name": "test_add", "class_name": "test_calculator.py", "status": "passed", "duration_seconds": 0.1, "failure_message": None, "failure_output": None},
            {"test_name": "test_divide", "class_name": "test_calculator.py", "status": "passed", "duration_seconds": 0.1, "failure_message": None, "failure_output": None},
        ])

        response = client.get(f"/projects/{project.id}/documents/{doc.id}")

        assert response.status_code == 200
        assert b"Latest CI" in response.data
        assert b"Run 4ac1e2c" in response.data

    def test_document_detail_not_found(self, client, project_id):
        response = client.get(f"/projects/{project_id}/documents/00000000-0000-0000-0000-000000000000", follow_redirects=True)
        assert response.status_code == 200
        assert b"not found" in response.data

    def test_edit_document(self, client, project_id):
        doc = DocumentService.create(
            project_id=project_id, doc_type="requirement",
            data={"title": "Old Title", "description": "Old desc"},
        )
        response = client.post(
            f"/projects/{project_id}/documents/{doc.id}/edit",
            data={"title": "New Title", "description": "New desc", "req_type": "functional", "priority": "must", "status": "approved", "category": "", "rationale": ""},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"New Title" in response.data

    def test_delete_document_route(self, client, project_id):
        doc = DocumentService.create(
            project_id=project_id, doc_type="user_story",
            data={"user_type": "tester", "action": "test", "benefit": "quality"},
        )
        response = client.post(f"/projects/{project_id}/documents/{doc.id}/delete", follow_redirects=True)
        assert response.status_code == 200

    def test_invalid_doc_type(self, client, project_id):
        response = client.get(f"/projects/{project_id}/documents/new/invalid", follow_redirects=True)
        assert response.status_code == 200
        assert b"Invalid" in response.data


class TestDocumentSchemas:
    def test_user_story_valid(self):
        data = UserStoryData(user_type="dev", action="code", benefit="ship")
        assert data.priority == "medium"

    def test_multi_user_story_valid(self):
        data = UserStoryData(stories=[
            {"user_type": "dev", "action": "code", "benefit": "ship"},
            {"user_type": "admin", "action": "manage", "benefit": "control"},
        ])
        assert len(data.stories) == 2

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
