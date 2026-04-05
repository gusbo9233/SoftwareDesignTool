"""Tests for the GitHub integration: services, JUnit parsing, routes."""
import json
from unittest.mock import patch, MagicMock

import pytest

from app.services.git_connection_service import GitConnectionService
from app.services.test_result_service import TestResultService, parse_junit_xml
from app.services.github_service import GitHubService, GitHubAPIError


# ---------------------------------------------------------------------------
# JUnit XML parsing
# ---------------------------------------------------------------------------

SAMPLE_JUNIT_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="tests" tests="5" errors="1" failures="1" skipped="1" time="2.345">
    <testcase classname="tests.test_one" name="test_pass_a" time="0.100"></testcase>
    <testcase classname="tests.test_one" name="test_pass_b" time="0.200"></testcase>
    <testcase classname="tests.test_two" name="test_fail" time="0.500">
      <failure message="AssertionError: 1 != 2">Traceback: ...</failure>
    </testcase>
    <testcase classname="tests.test_two" name="test_error" time="0.300">
      <error message="RuntimeError: boom">Traceback: ...</error>
    </testcase>
    <testcase classname="tests.test_three" name="test_skip" time="0.000">
      <skipped message="Not implemented yet"/>
    </testcase>
  </testsuite>
</testsuites>
"""

SAMPLE_JUNIT_BARE = b"""<?xml version="1.0" encoding="utf-8"?>
<testsuite name="pytest" tests="2" failures="0" errors="0" time="0.5">
  <testcase classname="tests.test_a" name="test_ok" time="0.25"></testcase>
  <testcase classname="tests.test_a" name="test_ok2" time="0.25"></testcase>
</testsuite>
"""


class TestJUnitParsing:
    def test_parse_full_suite(self):
        summary, cases = parse_junit_xml(SAMPLE_JUNIT_XML)
        assert summary["total_tests"] == 5
        assert summary["passed"] == 2
        assert summary["failed"] == 2  # 1 failure + 1 error
        assert summary["skipped"] == 1
        assert summary["duration_seconds"] == pytest.approx(1.1, abs=0.01)

        statuses = {c["test_name"]: c["status"] for c in cases}
        assert statuses["test_pass_a"] == "passed"
        assert statuses["test_fail"] == "failed"
        assert statuses["test_error"] == "error"
        assert statuses["test_skip"] == "skipped"

    def test_parse_bare_testsuite(self):
        summary, cases = parse_junit_xml(SAMPLE_JUNIT_BARE)
        assert summary["total_tests"] == 2
        assert summary["passed"] == 2
        assert summary["failed"] == 0
        assert summary["skipped"] == 0

    def test_failure_messages_captured(self):
        _, cases = parse_junit_xml(SAMPLE_JUNIT_XML)
        fail_case = next(c for c in cases if c["test_name"] == "test_fail")
        assert "AssertionError" in fail_case["failure_message"]
        assert "Traceback" in fail_case["failure_output"]

    def test_passed_cases_have_no_failure(self):
        _, cases = parse_junit_xml(SAMPLE_JUNIT_XML)
        pass_case = next(c for c in cases if c["test_name"] == "test_pass_a")
        assert pass_case["failure_message"] is None
        assert pass_case["failure_output"] is None


# ---------------------------------------------------------------------------
# GitConnectionService CRUD
# ---------------------------------------------------------------------------

class TestGitConnectionService:
    def test_create_and_get(self, project):
        conn = GitConnectionService.create(
            project_id=project.id,
            repo_owner="octocat",
            repo_name="hello-world",
            auth_token_encrypted="ghp_test123",
        )
        assert conn.repo_owner == "octocat"
        assert conn.repo_name == "hello-world"

        fetched = GitConnectionService.get_for_project(project.id)
        assert fetched is not None
        assert fetched.id == conn.id
        assert fetched.default_branch == "main"

    def test_update(self, project):
        conn = GitConnectionService.create(
            project_id=project.id,
            repo_owner="octocat",
            repo_name="hello-world",
            auth_token_encrypted="ghp_test123",
        )
        updated = GitConnectionService.update(conn, repo_name="new-repo", default_branch="develop")
        assert updated.repo_name == "new-repo"
        assert updated.default_branch == "develop"

    def test_delete(self, project):
        conn = GitConnectionService.create(
            project_id=project.id,
            repo_owner="octocat",
            repo_name="hello-world",
            auth_token_encrypted="ghp_test123",
        )
        GitConnectionService.delete(conn)
        assert GitConnectionService.get_for_project(project.id) is None

    def test_no_connection(self, project):
        assert GitConnectionService.get_for_project(project.id) is None


# ---------------------------------------------------------------------------
# TestResultService CRUD
# ---------------------------------------------------------------------------

class TestTestResultService:
    def test_create_and_get_run(self, project):
        run = TestResultService.create_run(
            project_id=project.id,
            github_run_id=12345,
            branch="main",
            commit_sha="abc1234",
            status="completed",
            conclusion="success",
            run_url="https://github.com/test/runs/12345",
            total_tests=5,
            passed=4,
            failed=1,
            skipped=0,
            duration_seconds=2.5,
        )
        assert run.github_run_id == 12345
        assert run.conclusion == "success"

        fetched = TestResultService.get_run(run.id)
        assert fetched is not None
        assert fetched.total_tests == 5

    def test_get_run_by_github_id(self, project):
        run = TestResultService.create_run(
            project_id=project.id,
            github_run_id=99999,
            branch="main",
            commit_sha="def5678",
            status="completed",
            conclusion="failure",
            run_url="https://github.com/test/runs/99999",
        )
        found = TestResultService.get_run_by_github_id(99999)
        assert found is not None
        assert found.id == run.id

    def test_get_runs_for_project(self, project):
        TestResultService.create_run(
            project_id=project.id, github_run_id=1, branch="main",
            commit_sha="a", status="completed", conclusion="success",
            run_url="https://example.com/1",
        )
        TestResultService.create_run(
            project_id=project.id, github_run_id=2, branch="main",
            commit_sha="b", status="completed", conclusion="failure",
            run_url="https://example.com/2",
        )
        runs = TestResultService.get_runs_for_project(project.id)
        assert len(runs) == 2

    def test_create_and_get_results(self, project):
        run = TestResultService.create_run(
            project_id=project.id, github_run_id=555, branch="main",
            commit_sha="xyz", status="completed", conclusion="success",
            run_url="https://example.com/555",
        )
        cases = [
            {"test_name": "test_a", "class_name": "TestFoo", "status": "passed",
             "duration_seconds": 0.1, "failure_message": None, "failure_output": None},
            {"test_name": "test_b", "class_name": "TestFoo", "status": "failed",
             "duration_seconds": 0.2, "failure_message": "assert False",
             "failure_output": "line 10"},
        ]
        TestResultService.create_results(run.id, cases)

        results = TestResultService.get_results_for_run(run.id)
        assert len(results) == 2
        names = {r.test_name for r in results}
        assert "test_a" in names
        assert "test_b" in names


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

class TestGitHubRoutes:
    def test_settings_page_get(self, client, project):
        resp = client.get(f"/projects/{project.id}/github/settings")
        assert resp.status_code == 200
        assert b"Repository Connection" in resp.data

    def test_settings_create_connection(self, client, project):
        resp = client.post(
            f"/projects/{project.id}/github/settings",
            data={
                "repo_owner": "octocat",
                "repo_name": "hello-world",
                "default_branch": "main",
                "auth_token": "ghp_test123",
                "polling_enabled": "on",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302  # redirect to dashboard

        conn = GitConnectionService.get_for_project(project.id)
        assert conn is not None
        assert conn.repo_owner == "octocat"

    def test_settings_requires_owner_and_name(self, client, project):
        resp = client.post(
            f"/projects/{project.id}/github/settings",
            data={"repo_owner": "", "repo_name": "", "auth_token": "ghp_x"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"required" in resp.data

    def test_dashboard_redirects_without_connection(self, client, project):
        resp = client.get(f"/projects/{project.id}/github", follow_redirects=False)
        assert resp.status_code == 302
        assert "settings" in resp.headers["Location"]

    @patch("app.routes.github.GitHubService")
    def test_dashboard_with_connection(self, mock_gh_class, client, project):
        GitConnectionService.create(
            project_id=project.id,
            repo_owner="octocat",
            repo_name="hello-world",
            auth_token_encrypted="ghp_test",
        )

        mock_gh = MagicMock()
        mock_gh.list_commits.return_value = []
        mock_gh.list_pulls.return_value = []
        mock_gh_class.return_value = mock_gh

        resp = client.get(f"/projects/{project.id}/github")
        assert resp.status_code == 200
        assert b"octocat/hello-world" in resp.data

    def test_api_test_runs_empty(self, client, project):
        resp = client.get(f"/api/projects/{project.id}/github/test-runs")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_api_test_runs_with_data(self, client, project):
        TestResultService.create_run(
            project_id=project.id, github_run_id=42, branch="main",
            commit_sha="abc", status="completed", conclusion="success",
            run_url="https://example.com/42",
            total_tests=3, passed=3, failed=0, skipped=0,
        )
        resp = client.get(f"/api/projects/{project.id}/github/test-runs")
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["github_run_id"] == 42
        assert data[0]["passed"] == 3

    def test_api_test_run_detail(self, client, project):
        run = TestResultService.create_run(
            project_id=project.id, github_run_id=77, branch="main",
            commit_sha="xyz", status="completed", conclusion="failure",
            run_url="https://example.com/77",
        )
        TestResultService.create_results(run.id, [
            {"test_name": "test_one", "status": "passed", "duration_seconds": 0.1},
            {"test_name": "test_two", "status": "failed", "duration_seconds": 0.2,
             "failure_message": "oops", "failure_output": "stack trace"},
        ])
        resp = client.get(f"/api/projects/{project.id}/github/test-runs/{run.id}")
        data = resp.get_json()
        assert data["run"]["conclusion"] == "failure"
        assert len(data["results"]) == 2

    def test_api_test_run_not_found(self, client, project):
        resp = client.get(f"/api/projects/{project.id}/github/test-runs/nonexistent-id")
        assert resp.status_code == 404

    def test_sync_no_connection(self, client, project):
        resp = client.post(f"/api/projects/{project.id}/github/sync")
        assert resp.status_code == 400

    @patch("app.services.test_result_service.GitHubService")
    def test_sync_with_connection(self, mock_gh_class, client, project):
        GitConnectionService.create(
            project_id=project.id,
            repo_owner="octocat",
            repo_name="hello-world",
            auth_token_encrypted="ghp_test",
        )
        mock_gh = MagicMock()
        mock_gh.list_workflow_runs.return_value = {"workflow_runs": []}
        mock_gh_class.return_value = mock_gh

        resp = client.post(f"/api/projects/{project.id}/github/sync")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["synced_runs"] == 0


# ---------------------------------------------------------------------------
# Export includes ci_status
# ---------------------------------------------------------------------------

class TestExportCIStatus:
    def test_export_without_connection(self, client, project):
        resp = client.get(f"/api/projects/{project.id}/export?format=json")
        data = resp.get_json()
        assert data["ci_status"] is None

    def test_export_with_ci_data(self, client, project):
        GitConnectionService.create(
            project_id=project.id,
            repo_owner="octocat",
            repo_name="hello-world",
            auth_token_encrypted="ghp_test",
        )
        TestResultService.create_run(
            project_id=project.id, github_run_id=100, branch="main",
            commit_sha="aaa", status="completed", conclusion="success",
            run_url="https://example.com/100",
            total_tests=10, passed=9, failed=1, skipped=0,
        )
        resp = client.get(f"/api/projects/{project.id}/export?format=json")
        data = resp.get_json()
        ci = data["ci_status"]
        assert ci is not None
        assert ci["repo"] == "octocat/hello-world"
        assert ci["total_tests"] == 10
        assert ci["passed"] == 9
        assert ci["failed"] == 1
