"""Service for fetching CI test results from GitHub and parsing JUnit XML."""
import hashlib
import re
import xml.etree.ElementTree as ET
from types import SimpleNamespace
from datetime import datetime

import app as _app
from app.services.github_service import GitHubService


def generate_test_uid(test_name: str) -> str:
    """Generate a short deterministic ID from a test case name.

    Returns an 8-character hex string.  Same name always produces the same ID,
    so developers can derive it when writing test methods.
    """
    return hashlib.sha256(test_name.strip().lower().encode()).hexdigest()[:8]


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


def parse_pytest_output(log_text):
    """Parse pytest -v style console output into test case rows."""
    if not log_text:
        return {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "duration_seconds": None,
        }, []

    pattern = re.compile(
        r"^(?:\d{4}-\d{2}-\d{2}T[^\s]+\s+)?(?P<nodeid>\S+::(?P<test_name>[^\s]+))\s+"
        r"(?P<status>PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\b",
        re.MULTILINE,
    )
    cases = []
    passed = failed = skipped = 0

    for match in pattern.finditer(log_text):
        raw_status = match.group("status")
        status = {
            "PASSED": "passed",
            "FAILED": "failed",
            "ERROR": "error",
            "SKIPPED": "skipped",
            "XFAIL": "skipped",
            "XPASS": "passed",
        }[raw_status]
        if status == "passed":
            passed += 1
        elif status in {"failed", "error"}:
            failed += 1
        elif status == "skipped":
            skipped += 1

        nodeid = match.group("nodeid")
        class_name = nodeid.rsplit("::", 1)[0]
        cases.append({
            "test_name": match.group("test_name"),
            "class_name": class_name,
            "status": status,
            "duration_seconds": None,
            "failure_message": None,
            "failure_output": None,
        })

    summary = {
        "total_tests": len(cases),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "duration_seconds": None,
    }
    return summary, cases


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
            row = {
                "test_run_id": test_run_id,
                "test_name": tc["test_name"],
                "class_name": tc.get("class_name"),
                "status": tc["status"],
                "duration_seconds": tc.get("duration_seconds"),
                "failure_message": tc.get("failure_message"),
                "failure_output": tc.get("failure_output"),
            }
            if tc.get("linked_acceptance_test_id"):
                row["linked_acceptance_test_id"] = tc["linked_acceptance_test_id"]
            rows.append(row)
        for row in rows:
            _app.supabase.table("test_results").insert(row).execute()

    @staticmethod
    def _resolve_linked_documents(project_id, test_cases):
        """Match test_uid values found in CI test names to project documents.

        Scans all documents in the project that have a ``test_uid`` in their
        data and checks whether that UID appears in each CI test name.
        Mutates each test case dict in-place, setting
        ``linked_acceptance_test_id`` when a match is found.
        """
        from app.services.document_service import DocumentService
        all_docs = DocumentService.get_all_for_project(project_id)
        # Build lookup: test_uid → document id
        uid_to_doc: dict[str, str] = {}
        for doc in all_docs:
            test_uid = (doc.data or {}).get("test_uid")
            if test_uid:
                uid_to_doc[test_uid] = doc.id

        if not uid_to_doc:
            return

        for tc in test_cases:
            name_lower = tc["test_name"].lower()
            for uid, doc_id in uid_to_doc.items():
                if uid in name_lower:
                    tc["linked_acceptance_test_id"] = doc_id
                    break

    @staticmethod
    def get_linked_results_for_acceptance_test(acceptance_test_id):
        """Get the most recent CI test results linked to an acceptance test."""
        res = (
            _app.supabase.table("test_results")
            .select("*, test_runs(*)")
            .eq("linked_acceptance_test_id", acceptance_test_id)
            .order("test_run_id", desc=True)
            .execute()
        )
        return [_result(d) for d in res.data]

    @staticmethod
    def get_latest_results_for_test_names(project_id, test_names, limit_runs=20):
        wanted = {name.strip().lower(): name for name in test_names if name and name.strip()}
        if not wanted:
            return {}

        latest = {}
        runs = TestResultService.get_runs_for_project(project_id, limit=limit_runs)
        for run in runs:
            results = TestResultService.get_results_for_run(run.id)
            for result in results:
                normalized_name = (result.test_name or "").strip().lower()
                if normalized_name in wanted and normalized_name not in latest:
                    latest[normalized_name] = {
                        "result": result,
                        "run": run,
                    }
            if len(latest) == len(wanted):
                break
        return latest

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
            should_backfill_existing = bool(existing and getattr(existing, "total_tests", None) is None)
            if existing and not should_backfill_existing:
                continue

            status = wr.get("status", "queued")
            conclusion = wr.get("conclusion")

            if existing:
                run_record = existing
            else:
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
                    parsed = False
                    artifacts_data = gh.list_run_artifacts(github_run_id)
                    for art in artifacts_data.get("artifacts", []):
                        if "test" in art["name"].lower() or "junit" in art["name"].lower():
                            xml_bytes = gh.download_artifact_file(art["id"])
                            if xml_bytes:
                                summary, cases = parse_junit_xml(xml_bytes)
                                # Update run with parsed results
                                _app.supabase.table("test_results").delete().eq("test_run_id", run_record.id).execute()
                                _app.supabase.table("test_runs").update({
                                    "total_tests": summary["total_tests"],
                                    "passed": summary["passed"],
                                    "failed": summary["failed"],
                                    "skipped": summary["skipped"],
                                    "duration_seconds": summary["duration_seconds"],
                                }).eq("id", run_record.id).execute()

                                TestResultService._resolve_linked_documents(project_id, cases)
                                TestResultService.create_results(run_record.id, cases)
                                run_record.total_tests = summary["total_tests"]
                                run_record.passed = summary["passed"]
                                run_record.failed = summary["failed"]
                                run_record.skipped = summary["skipped"]
                                parsed = True
                                break

                    if not parsed:
                        jobs_data = gh.list_run_jobs(github_run_id)
                        all_cases = []
                        for job in jobs_data.get("jobs", []):
                            log_text = gh.download_job_logs(job["id"])
                            _, cases = parse_pytest_output(log_text)
                            all_cases.extend(cases)

                        deduped_cases = []
                        seen_names = set()
                        for case in all_cases:
                            normalized_name = (case.get("test_name") or "").strip().lower()
                            if normalized_name and normalized_name not in seen_names:
                                seen_names.add(normalized_name)
                                deduped_cases.append(case)

                        if deduped_cases:
                            _app.supabase.table("test_results").delete().eq("test_run_id", run_record.id).execute()
                            summary = {
                                "total_tests": len(deduped_cases),
                                "passed": sum(1 for c in deduped_cases if c["status"] == "passed"),
                                "failed": sum(1 for c in deduped_cases if c["status"] in {"failed", "error"}),
                                "skipped": sum(1 for c in deduped_cases if c["status"] == "skipped"),
                                "duration_seconds": None,
                            }
                            _app.supabase.table("test_runs").update({
                                "total_tests": summary["total_tests"],
                                "passed": summary["passed"],
                                "failed": summary["failed"],
                                "skipped": summary["skipped"],
                                "duration_seconds": summary["duration_seconds"],
                            }).eq("id", run_record.id).execute()

                            TestResultService._resolve_linked_documents(project_id, deduped_cases)
                            TestResultService.create_results(run_record.id, deduped_cases)
                            run_record.total_tests = summary["total_tests"]
                            run_record.passed = summary["passed"]
                            run_record.failed = summary["failed"]
                            run_record.skipped = summary["skipped"]
                except Exception:
                    pass  # Artifact download may fail; run record still saved

            if not existing or should_backfill_existing:
                synced.append(run_record)

        return synced
