from datetime import datetime, timezone
import time
from types import SimpleNamespace

import app as _app

try:
    import httpx
except Exception:  # pragma: no cover - dependency should exist in app runtime
    httpx = None


def _parse_dt(s):
    if not s or not isinstance(s, str):
        return s
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        pass
    try:
        from dateutil.parser import parse as dateutil_parse
        return dateutil_parse(s)
    except Exception:
        return s


def _project(d):
    d = dict(d)
    for field in ("created_at", "updated_at"):
        if field in d:
            d[field] = _parse_dt(d[field])
    d.setdefault("documents", [])
    d.setdefault("diagrams", [])
    d.setdefault("api_endpoints", [])
    return SimpleNamespace(**d)


class ProjectServiceUnavailableError(RuntimeError):
    pass


def _is_transient_transport_error(exc):
    if httpx is not None and isinstance(exc, httpx.HTTPError):
        message = str(exc).lower()
        return "server disconnected" in message or "remoteprotocolerror" in message
    message = str(exc).lower()
    return "server disconnected" in message or "remoteprotocolerror" in message


def _execute(builder, operation):
    last_exc = None
    for attempt in range(2):
        try:
            return builder.execute()
        except Exception as exc:
            last_exc = exc
            if not _is_transient_transport_error(exc) or attempt == 1:
                break
            time.sleep(0.2)
    raise ProjectServiceUnavailableError(
        f"Could not reach project storage while trying to {operation}. Please try again."
    ) from last_exc


class ProjectService:
    @staticmethod
    def get_all():
        res = _execute(
            _app.supabase.table("projects").select("*").order("updated_at", desc=True),
            "load projects",
        )
        return [_project(d) for d in res.data]

    @staticmethod
    def get(id):
        res = _execute(
            _app.supabase.table("projects").select("*").eq("id", id).maybe_single(),
            "load the project",
        )
        return _project(res.data) if res.data else None

    @staticmethod
    def create(name, description=""):
        res = _execute(
            _app.supabase.table("projects").insert({"name": name, "description": description}),
            "create the project",
        )
        return _project(res.data[0])

    @staticmethod
    def update(project, name=None, description=None):
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if updates:
            res = _execute(
                _app.supabase.table("projects").update(updates).eq("id", project.id),
                "update the project",
            )
            if res.data:
                normalized = _project(res.data[0])
                for k, v in vars(normalized).items():
                    setattr(project, k, v)
        return project

    @staticmethod
    def delete(project):
        _execute(
            _app.supabase.table("projects").delete().eq("id", project.id),
            "delete the project",
        )
