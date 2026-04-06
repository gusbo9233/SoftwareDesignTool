from datetime import datetime, timezone
from types import SimpleNamespace

import app as _app


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


class ProjectService:
    @staticmethod
    def get_all():
        res = _app.supabase.table("projects").select("*").order("updated_at", desc=True).execute()
        return [_project(d) for d in res.data]

    @staticmethod
    def get(id):
        res = _app.supabase.table("projects").select("*").eq("id", id).maybe_single().execute()
        return _project(res.data) if res.data else None

    @staticmethod
    def create(name, description=""):
        res = _app.supabase.table("projects").insert({"name": name, "description": description}).execute()
        return _project(res.data[0])

    @staticmethod
    def update(project, name=None, description=None):
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if updates:
            res = _app.supabase.table("projects").update(updates).eq("id", project.id).execute()
            if res.data:
                normalized = _project(res.data[0])
                for k, v in vars(normalized).items():
                    setattr(project, k, v)
        return project

    @staticmethod
    def delete(project):
        _app.supabase.table("projects").delete().eq("id", project.id).execute()
