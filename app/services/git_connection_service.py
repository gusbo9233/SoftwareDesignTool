"""CRUD service for git_connections table via Supabase."""
from datetime import datetime
from types import SimpleNamespace

import app as _app


def _parse_dt(s):
    if not s or not isinstance(s, str):
        return s
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return s


def _conn(d):
    d = dict(d)
    for field in ("created_at", "last_synced_at"):
        if field in d:
            d[field] = _parse_dt(d[field])
    return SimpleNamespace(**d)


class GitConnectionService:
    @staticmethod
    def get_for_project(project_id):
        res = (
            _app.supabase.table("git_connections")
            .select("*")
            .eq("project_id", project_id)
            .maybe_single()
            .execute()
        )
        if res is None or res.data is None:
            return None
        return _conn(res.data)

    @staticmethod
    def create(project_id, repo_owner, repo_name, auth_token_encrypted,
               default_branch="main", webhook_secret=None, polling_enabled=True):
        res = _app.supabase.table("git_connections").insert({
            "project_id": project_id,
            "repo_owner": repo_owner,
            "repo_name": repo_name,
            "auth_token_encrypted": auth_token_encrypted,
            "default_branch": default_branch,
            "webhook_secret": webhook_secret,
            "polling_enabled": polling_enabled,
        }).execute()
        return _conn(res.data[0])

    @staticmethod
    def update(connection, **kwargs):
        allowed = {"repo_owner", "repo_name", "default_branch",
                   "auth_token_encrypted", "webhook_secret", "polling_enabled",
                   "last_synced_at"}
        updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if updates:
            res = (
                _app.supabase.table("git_connections")
                .update(updates)
                .eq("id", connection.id)
                .execute()
            )
            if res.data:
                return _conn(res.data[0])
        return connection

    @staticmethod
    def delete(connection):
        _app.supabase.table("git_connections").delete().eq("id", connection.id).execute()

    @staticmethod
    def touch_synced(connection):
        """Update last_synced_at to now."""
        from datetime import timezone
        now = datetime.now(timezone.utc).isoformat()
        return GitConnectionService.update(connection, last_synced_at=now)
