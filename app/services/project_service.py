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
    d.setdefault("template_key", "generic")
    d.setdefault("user_id", None)
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
    def _active_user_id():
        try:
            from app.services.auth_service import AuthService
            return AuthService.current_user_id()
        except Exception:
            return None

    @staticmethod
    def _is_missing_column_error(exc, column_name):
        current = exc
        while current is not None:
            message = str(current).lower()
            if column_name.lower() in message and (
                "column" in message or "schema cache" in message or "could not find" in message
            ):
                return True
            current = getattr(current, "__cause__", None)
        return False

    @staticmethod
    def _ownership_storage_message():
        return (
            "Project ownership storage is not ready yet. Apply the users/project ownership migration first."
        )

    @staticmethod
    def get_all(user_id=None):
        active_user_id = user_id if user_id is not None else ProjectService._active_user_id()
        query = _app.supabase.table("projects").select("*")
        if active_user_id:
            query = query.eq("user_id", active_user_id)
        try:
            res = _execute(
                query.order("updated_at", desc=True),
                "load projects",
            )
        except ProjectServiceUnavailableError as exc:
            if active_user_id and ProjectService._is_missing_column_error(exc, "user_id"):
                raise ProjectServiceUnavailableError(ProjectService._ownership_storage_message()) from exc
            raise
        return [_project(d) for d in res.data]

    @staticmethod
    def get(id, user_id=None):
        active_user_id = user_id if user_id is not None else ProjectService._active_user_id()
        query = _app.supabase.table("projects").select("*").eq("id", id)
        if active_user_id:
            query = query.eq("user_id", active_user_id)
        try:
            res = _execute(
                query.maybe_single(),
                "load the project",
            )
        except ProjectServiceUnavailableError as exc:
            if active_user_id and ProjectService._is_missing_column_error(exc, "user_id"):
                raise ProjectServiceUnavailableError(ProjectService._ownership_storage_message()) from exc
            raise
        return _project(res.data) if res.data else None

    @staticmethod
    def create(name, description="", template_key="generic", user_id=None):
        active_user_id = user_id if user_id is not None else ProjectService._active_user_id()
        payload = {"name": name, "description": description, "template_key": template_key}
        if active_user_id:
            payload["user_id"] = active_user_id
        try:
            res = _execute(
                _app.supabase.table("projects").insert(payload),
                "create the project",
            )
        except ProjectServiceUnavailableError as exc:
            if ProjectService._is_missing_column_error(exc, "template_key") or ProjectService._is_missing_column_error(exc, "user_id"):
                fallback_payload = {"name": name, "description": description}
                if active_user_id and not ProjectService._is_missing_column_error(exc, "user_id"):
                    fallback_payload["user_id"] = active_user_id
                res = _execute(
                    _app.supabase.table("projects").insert(fallback_payload),
                    "create the project",
                )
            else:
                raise
        return _project(res.data[0])

    @staticmethod
    def update(project, name=None, description=None, template_key=None, user_id=None):
        active_user_id = user_id if user_id is not None else ProjectService._active_user_id()
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if template_key is not None:
            updates["template_key"] = template_key
        if updates:
            try:
                query = _app.supabase.table("projects").update(updates).eq("id", project.id)
                if active_user_id:
                    query = query.eq("user_id", active_user_id)
                res = _execute(
                    query,
                    "update the project",
                )
            except ProjectServiceUnavailableError as exc:
                if "template_key" in updates and ProjectService._is_missing_column_error(exc, "template_key"):
                    fallback_updates = dict(updates)
                    fallback_updates.pop("template_key", None)
                    if not fallback_updates:
                        return project
                    query = _app.supabase.table("projects").update(fallback_updates).eq("id", project.id)
                    if active_user_id:
                        query = query.eq("user_id", active_user_id)
                    res = _execute(
                        query,
                        "update the project",
                    )
                else:
                    if active_user_id and ProjectService._is_missing_column_error(exc, "user_id"):
                        raise ProjectServiceUnavailableError(ProjectService._ownership_storage_message()) from exc
                    raise
            if res.data:
                normalized = _project(res.data[0])
                for k, v in vars(normalized).items():
                    setattr(project, k, v)
        return project

    @staticmethod
    def delete(project, user_id=None):
        active_user_id = user_id if user_id is not None else ProjectService._active_user_id()
        query = _app.supabase.table("projects").delete().eq("id", project.id)
        if active_user_id:
            query = query.eq("user_id", active_user_id)
        _execute(
            query,
            "delete the project",
        )
