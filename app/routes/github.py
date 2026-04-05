"""Routes for GitHub integration: settings, sync, dashboard, webhook."""
import hashlib
import hmac

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, jsonify,
)

from app.services.project_service import ProjectService
from app.services.git_connection_service import GitConnectionService
from app.services.test_result_service import TestResultService
from app.services.github_service import GitHubService, GitHubAPIError

github_bp = Blueprint("github", __name__)


# ---------------------------------------------------------------------------
# Settings: connect/edit repository
# ---------------------------------------------------------------------------

@github_bp.route("/projects/<project_id>/github/settings", methods=["GET", "POST"])
def settings(project_id):
    project = ProjectService.get(project_id)
    if not project:
        flash("Project not found.", "error")
        return redirect(url_for("projects.index"))

    connection = GitConnectionService.get_for_project(project_id)

    if request.method == "POST":
        repo_owner = request.form.get("repo_owner", "").strip()
        repo_name = request.form.get("repo_name", "").strip()
        default_branch = request.form.get("default_branch", "main").strip()
        auth_token = request.form.get("auth_token", "").strip()
        webhook_secret = request.form.get("webhook_secret", "").strip() or None
        polling_enabled = request.form.get("polling_enabled") == "on"

        if not repo_owner or not repo_name:
            flash("Repository owner and name are required.", "error")
            return render_template(
                "github/settings.html", project=project, connection=connection,
                active_section="github",
            )

        if connection:
            updates = {
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "default_branch": default_branch,
                "polling_enabled": polling_enabled,
                "webhook_secret": webhook_secret,
            }
            if auth_token:
                updates["auth_token_encrypted"] = auth_token
            GitConnectionService.update(connection, **updates)
            flash("GitHub connection updated.", "success")
        else:
            if not auth_token:
                flash("Personal access token is required for initial setup.", "error")
                return render_template(
                    "github/settings.html", project=project, connection=connection,
                    active_section="github",
                )
            GitConnectionService.create(
                project_id=project_id,
                repo_owner=repo_owner,
                repo_name=repo_name,
                auth_token_encrypted=auth_token,
                default_branch=default_branch,
                webhook_secret=webhook_secret,
                polling_enabled=polling_enabled,
            )
            flash("GitHub connection created.", "success")

        return redirect(url_for("github.dashboard", project_id=project_id))

    return render_template(
        "github/settings.html", project=project, connection=connection,
        active_section="github",
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@github_bp.route("/projects/<project_id>/github")
def dashboard(project_id):
    project = ProjectService.get(project_id)
    if not project:
        flash("Project not found.", "error")
        return redirect(url_for("projects.index"))

    connection = GitConnectionService.get_for_project(project_id)
    if not connection:
        return redirect(url_for("github.settings", project_id=project_id))

    gh = GitHubService(
        token=connection.auth_token_encrypted,
        repo_owner=connection.repo_owner,
        repo_name=connection.repo_name,
    )

    commits = []
    pulls = []
    error_msg = None

    try:
        commits = gh.list_commits(branch=connection.default_branch, per_page=20)
    except GitHubAPIError as e:
        error_msg = f"Failed to fetch commits: {e.message}"

    try:
        pulls = gh.list_pulls(state="open", per_page=20)
    except GitHubAPIError as e:
        error_msg = f"Failed to fetch pull requests: {e.message}"

    test_runs = TestResultService.get_runs_for_project(project_id, limit=10)

    return render_template(
        "github/dashboard.html",
        project=project,
        connection=connection,
        commits=commits,
        pulls=pulls,
        test_runs=test_runs,
        error_msg=error_msg,
        active_section="github",
    )


# ---------------------------------------------------------------------------
# API: Sync
# ---------------------------------------------------------------------------

@github_bp.route("/api/projects/<project_id>/github/sync", methods=["POST"])
def sync(project_id):
    project = ProjectService.get(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    connection = GitConnectionService.get_for_project(project_id)
    if not connection:
        return jsonify({"error": "No GitHub connection configured"}), 400

    try:
        synced = TestResultService.sync_workflow_runs(project_id, connection)
        GitConnectionService.touch_synced(connection)
    except GitHubAPIError as e:
        return jsonify({"error": e.message}), e.status_code

    return jsonify({
        "synced_runs": len(synced),
        "message": f"Synced {len(synced)} new workflow run(s).",
    })


# ---------------------------------------------------------------------------
# API: Proxy endpoints (cached via Supabase for test runs, live for commits/PRs)
# ---------------------------------------------------------------------------

@github_bp.route("/api/projects/<project_id>/github/commits")
def api_commits(project_id):
    connection = GitConnectionService.get_for_project(project_id)
    if not connection:
        return jsonify({"error": "No GitHub connection configured"}), 400

    gh = GitHubService(
        token=connection.auth_token_encrypted,
        repo_owner=connection.repo_owner,
        repo_name=connection.repo_name,
    )
    branch = request.args.get("branch", connection.default_branch)
    try:
        commits = gh.list_commits(branch=branch, per_page=20)
    except GitHubAPIError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(commits)


@github_bp.route("/api/projects/<project_id>/github/pulls")
def api_pulls(project_id):
    connection = GitConnectionService.get_for_project(project_id)
    if not connection:
        return jsonify({"error": "No GitHub connection configured"}), 400

    gh = GitHubService(
        token=connection.auth_token_encrypted,
        repo_owner=connection.repo_owner,
        repo_name=connection.repo_name,
    )
    state = request.args.get("state", "open")
    try:
        pulls = gh.list_pulls(state=state, per_page=20)
    except GitHubAPIError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(pulls)


@github_bp.route("/api/projects/<project_id>/github/test-runs")
def api_test_runs(project_id):
    runs = TestResultService.get_runs_for_project(project_id)
    return jsonify([{
        "id": r.id,
        "github_run_id": r.github_run_id,
        "branch": r.branch,
        "commit_sha": r.commit_sha,
        "status": r.status,
        "conclusion": r.conclusion,
        "total_tests": r.total_tests,
        "passed": r.passed,
        "failed": r.failed,
        "skipped": r.skipped,
        "duration_seconds": r.duration_seconds,
        "run_url": r.run_url,
        "created_at": str(r.created_at),
    } for r in runs])


@github_bp.route("/api/projects/<project_id>/github/test-runs/<run_id>")
def api_test_run_detail(project_id, run_id):
    run = TestResultService.get_run(run_id)
    if not run:
        return jsonify({"error": "Test run not found"}), 404

    results = TestResultService.get_results_for_run(run_id)
    return jsonify({
        "run": {
            "id": run.id,
            "github_run_id": run.github_run_id,
            "branch": run.branch,
            "commit_sha": run.commit_sha,
            "status": run.status,
            "conclusion": run.conclusion,
            "total_tests": run.total_tests,
            "passed": run.passed,
            "failed": run.failed,
            "skipped": run.skipped,
            "duration_seconds": run.duration_seconds,
            "run_url": run.run_url,
        },
        "results": [{
            "id": r.id,
            "test_name": r.test_name,
            "class_name": r.class_name,
            "status": r.status,
            "duration_seconds": r.duration_seconds,
            "failure_message": r.failure_message,
            "failure_output": r.failure_output,
        } for r in results],
    })


# ---------------------------------------------------------------------------
# Webhook receiver (optional)
# ---------------------------------------------------------------------------

@github_bp.route("/api/webhooks/github", methods=["POST"])
def webhook():
    """Receive GitHub webhook events. Validates signature and handles workflow_run."""
    payload = request.get_data()
    signature = request.headers.get("X-Hub-Signature-256", "")
    event = request.headers.get("X-GitHub-Event", "")

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid payload"}), 400

    # Find the connection by repo to validate the webhook secret
    repo = data.get("repository", {})
    owner = repo.get("owner", {}).get("login", "")
    repo_name = repo.get("name", "")

    if not owner or not repo_name:
        return jsonify({"error": "Could not determine repository"}), 400

    # Look up connection — we need to find the project that has this repo connected
    # Since we don't have a direct lookup by repo, scan is acceptable for single-user tool
    import app as _app
    res = (
        _app.supabase.table("git_connections")
        .select("*")
        .eq("repo_owner", owner)
        .eq("repo_name", repo_name)
        .maybe_single()
        .execute()
    )
    if not res.data:
        return jsonify({"error": "No matching connection"}), 404

    connection_data = res.data
    webhook_secret = connection_data.get("webhook_secret")

    # Validate signature if webhook secret is configured
    if webhook_secret:
        expected = "sha256=" + hmac.new(
            webhook_secret.encode(), payload, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return jsonify({"error": "Invalid signature"}), 403

    # Handle workflow_run completed events
    if event == "workflow_run" and data.get("action") == "completed":
        project_id = connection_data["project_id"]
        from app.services.git_connection_service import GitConnectionService
        conn = GitConnectionService.get_for_project(project_id)
        if conn:
            TestResultService.sync_workflow_runs(project_id, conn)

    return jsonify({"status": "ok"})
