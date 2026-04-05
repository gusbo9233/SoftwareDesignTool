"""Service for fetching CI test results from GitHub and parsing JUnit XML."""
import xml.etree.ElementTree as ET
from types import SimpleNamespace
from datetime import datetime

import app as _app
from app.services.github_service import GitHubService


def _parse_dt(s):
    if not s or not isinstance(s, str):
        return s
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return s


def _run(d):
    d = dict(d)
    for field in ("created_at",):
        if field in d:
            d[field] = _parse_dt(d[field])
    return SimpleNamespace(**d)


def _result(d):
    return SimpleNamespace(**dict(d))


def parse_junit_xml(xml_bytes):
    """Parse JUnit XML bytes into a list of test case dicts.

    Returns (summary_dict, list_of_test_case_dicts).
    """
    root = ET.fromstring(xml_bytes)
    test_cases = []

    # Handle both <testsuites><testsuite>... and bare <testsuite>...
    suites = root.findall(".//testsuite")
    if root.tag == "testsuite":
        suites = [root]

    total = 0
    passed = 0
    failed = 0
    errors = 0
    skipped = 0
    total_time = 0.0

    for suite in suites:
        for tc in suite.findall("testcase"):
            total += 1
            name = tc.get("name", "unknown")
            classname = tc.get("classname", "")
            duration = float(tc.get("time", 0))
            total_time += duration

            failure_el = tc.find("failure")
            error_el = tc.find("error")
            skipped_el = tc.find("skipped")

            if failure_el is not None:
                status = "failed"
                failed += 1
                test_cases.append({
                    "test_name": name,
                    "class_name": classname,
                    "status": status,
                    "duration_seconds": duration,
                    "failure_message": failure_el.get("message", ""),
                    "failure_output": failure_el.text or "",
                })
            elif error_el is not None:
                status = "error"
                errors += 1
                test_cases.append({
                    "test_name": name,
                    "class_name": classname,
                    "status": status,
                    "duration_seconds": duration,
                    "failure_message": error_el.get("message", ""),
                    "failure_output": error_el.text or "",
                })
            elif skipped_el is not None:
                status = "skipped"
                skipped += 1
                test_cases.append({
                    "test_name": name,
                    "class_name": classname,
                    "status": status,
                    "duration_seconds": duration,
                    "failure_message": skipped_el.get("message", ""),
                    "failure_output": "",
                })
            else:
                status = "passed"
                passed += 1
                test_cases.append({
                    "test_name": name,
                    "class_name": classname,
                    "status": status,
                    "duration_seconds": duration,
                    "failure_message": None,
                    "failure_output": None,
                })

    summary = {
        "total_tests": total,
        "passed": passed,
        "failed": failed + errors,
        "skipped": skipped,
        "duration_seconds": round(total_time, 3),
    }
    return summary, test_cases


class TestResultService:
    @staticmethod
    def get_runs_for_project(project_id, limit=20):
        res = (
            _app.supabase.table("test_runs")
            .select("*")
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .execute()
        )
        runs = [_run(d) for d in res.data]
        return runs[:limit]

    @staticmethod
    def get_run(run_id):
        res = (
            _app.supabase.table("test_runs")
            .select("*")
            .eq("id", run_id)
            .maybe_single()
            .execute()
        )
        if res is None or res.data is None:
            return None
        return _run(res.data)

    @staticmethod
    def get_run_by_github_id(github_run_id):
        res = (
            _app.supabase.table("test_runs")
            .select("*")
            .eq("github_run_id", github_run_id)
            .maybe_single()
            .execute()
        )
        if res is None or res.data is None:
            return None
        return _run(res.data)

    @staticmethod
    def get_results_for_run(test_run_id):
        res = (
            _app.supabase.table("test_results")
            .select("*")
            .eq("test_run_id", test_run_id)
            .execute()
        )
        return [_result(d) for d in res.data]

    @staticmethod
    def create_run(project_id, github_run_id, branch, commit_sha, status,
                   conclusion, run_url, total_tests=None, passed=None,
                   failed=None, skipped=None, duration_seconds=None):
        res = _app.supabase.table("test_runs").insert({
            "project_id": project_id,
            "github_run_id": github_run_id,
            "branch": branch,
            "commit_sha": commit_sha,
            "status": status,
            "conclusion": conclusion,
            "total_tests": total_tests,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "duration_seconds": duration_seconds,
            "run_url": run_url,
        }).execute()
        return _run(res.data[0])

    @staticmethod
    def create_results(test_run_id, test_cases):
        """Bulk insert test case results for a run."""
        rows = []
        for tc in test_cases:
            rows.append({
                "test_run_id": test_run_id,
                "test_name": tc["test_name"],
                "class_name": tc.get("class_name"),
                "status": tc["status"],
                "duration_seconds": tc.get("duration_seconds"),
                "failure_message": tc.get("failure_message"),
                "failure_output": tc.get("failure_output"),
            })
        for row in rows:
            _app.supabase.table("test_results").insert(row).execute()

    @staticmethod
    def sync_workflow_runs(project_id, git_connection):
        """Fetch recent workflow runs from GitHub, download artifacts, parse results.

        Returns a list of newly synced run summaries.
        """
        gh = GitHubService(
            token=git_connection.auth_token_encrypted,
            repo_owner=git_connection.repo_owner,
            repo_name=git_connection.repo_name,
        )

        runs_data = gh.list_workflow_runs(
            branch=git_connection.default_branch, per_page=10
        )
        workflow_runs = runs_data.get("workflow_runs", [])
        synced = []

        for wr in workflow_runs:
            github_run_id = wr["id"]
            existing = TestResultService.get_run_by_github_id(github_run_id)
            if existing:
                continue

            status = wr.get("status", "queued")
            conclusion = wr.get("conclusion")

            run_record = TestResultService.create_run(
                project_id=project_id,
                github_run_id=github_run_id,
                branch=wr.get("head_branch", git_connection.default_branch),
                commit_sha=wr.get("head_sha", ""),
                status=status,
                conclusion=conclusion,
                run_url=wr.get("html_url", ""),
            )

            # Try to download and parse test artifacts
            if status == "completed":
                try:
                    artifacts_data = gh.list_run_artifacts(github_run_id)
                    for art in artifacts_data.get("artifacts", []):
                        if "test" in art["name"].lower() or "junit" in art["name"].lower():
                            xml_bytes = gh.download_artifact_file(art["id"])
                            if xml_bytes:
                                summary, cases = parse_junit_xml(xml_bytes)
                                # Update run with parsed results
                                _app.supabase.table("test_runs").update({
                                    "total_tests": summary["total_tests"],
                                    "passed": summary["passed"],
                                    "failed": summary["failed"],
                                    "skipped": summary["skipped"],
                                    "duration_seconds": summary["duration_seconds"],
                                }).eq("id", run_record.id).execute()

                                TestResultService.create_results(run_record.id, cases)
                                run_record.total_tests = summary["total_tests"]
                                run_record.passed = summary["passed"]
                                run_record.failed = summary["failed"]
                                run_record.skipped = summary["skipped"]
                                break
                except Exception:
                    pass  # Artifact download may fail; run record still saved

            synced.append(run_record)

        return synced
