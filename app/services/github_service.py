"""GitHub REST API client service.

Wraps GitHub API calls for commits, pull requests, workflow runs, and artifacts.
Uses httpx for HTTP requests with rate-limit handling.
"""
import io
import time
import zipfile

import httpx

BASE_URL = "https://api.github.com"
DEFAULT_PER_PAGE = 30


class GitHubAPIError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(f"GitHub API error {status_code}: {message}")


class GitHubService:
    def __init__(self, token, repo_owner, repo_name):
        self.token = token
        self.repo_owner = repo_owner
        self.repo_name = repo_name

    @property
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    @property
    def _repo_url(self):
        return f"{BASE_URL}/repos/{self.repo_owner}/{self.repo_name}"

    def _request(self, method, url, **kwargs):
        """Make an HTTP request with rate-limit backoff."""
        response = httpx.request(method, url, headers=self._headers, timeout=30, **kwargs)

        # Rate limit handling
        if response.status_code == 403:
            remaining = response.headers.get("X-RateLimit-Remaining")
            if remaining == "0":
                reset_at = int(response.headers.get("X-RateLimit-Reset", 0))
                wait = max(reset_at - int(time.time()), 1)
                raise GitHubAPIError(429, f"Rate limited. Resets in {wait}s.")

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            raise GitHubAPIError(429, f"Rate limited. Retry after {retry_after}s.")

        if response.status_code >= 400:
            raise GitHubAPIError(response.status_code, response.text)

        return response

    def get_repo_info(self):
        """Get basic repository information."""
        resp = self._request("GET", self._repo_url)
        return resp.json()

    def list_commits(self, branch="main", per_page=20, page=1):
        """List commits on a branch."""
        resp = self._request("GET", f"{self._repo_url}/commits", params={
            "sha": branch,
            "per_page": per_page,
            "page": page,
        })
        return resp.json()

    def list_pulls(self, state="open", per_page=20, page=1):
        """List pull requests."""
        resp = self._request("GET", f"{self._repo_url}/pulls", params={
            "state": state,
            "per_page": per_page,
            "page": page,
        })
        return resp.json()

    def list_workflow_runs(self, branch=None, per_page=20, page=1):
        """List workflow runs, optionally filtered by branch."""
        params = {"per_page": per_page, "page": page}
        if branch:
            params["branch"] = branch
        resp = self._request("GET", f"{self._repo_url}/actions/runs", params=params)
        return resp.json()

    def get_workflow_run(self, run_id):
        """Get a specific workflow run."""
        resp = self._request("GET", f"{self._repo_url}/actions/runs/{run_id}")
        return resp.json()

    def list_run_artifacts(self, run_id):
        """List artifacts for a workflow run."""
        resp = self._request("GET", f"{self._repo_url}/actions/runs/{run_id}/artifacts")
        return resp.json()

    def download_artifact(self, artifact_id):
        """Download an artifact ZIP and return the bytes."""
        resp = self._request(
            "GET",
            f"{self._repo_url}/actions/artifacts/{artifact_id}/zip",
            follow_redirects=True,
        )
        return resp.content

    def download_artifact_file(self, artifact_id, filename_hint="results.xml"):
        """Download an artifact ZIP and extract a specific file's content."""
        zip_bytes = self.download_artifact(artifact_id)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for name in zf.namelist():
                if name.endswith(filename_hint) or filename_hint in name:
                    return zf.read(name)
            # If exact match not found, return first XML file
            for name in zf.namelist():
                if name.endswith(".xml"):
                    return zf.read(name)
        return None
