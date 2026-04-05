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


def _endpoint(d):
    d = dict(d)
    for field in ("created_at", "updated_at"):
        if field in d:
            d[field] = _parse_dt(d[field])
    return SimpleNamespace(**d)


class APIEndpointService:
    @staticmethod
    def get_all_for_project(project_id):
        res = (
            _app.supabase.table("api_endpoints")
            .select("*")
            .eq("project_id", project_id)
            .order("updated_at", desc=True)
            .execute()
        )
        return [_endpoint(d) for d in res.data]

    @staticmethod
    def get(id):
        res = _app.supabase.table("api_endpoints").select("*").eq("id", id).maybe_single().execute()
        return _endpoint(res.data) if res.data else None

    @staticmethod
    def create(project_id, path, method, description="",
               request_schema=None, response_schema=None, **_):
        res = _app.supabase.table("api_endpoints").insert({
            "project_id": project_id,
            "path": path,
            "method": method,
            "description": description,
            "request_schema": request_schema or {},
            "response_schema": response_schema or {},
        }).execute()
        return SimpleNamespace(**res.data[0])

    @staticmethod
    def update(endpoint, path=None, method=None, description=None,
               request_schema=None, response_schema=None):
        updates = {}
        if path is not None:
            updates["path"] = path
        if method is not None:
            updates["method"] = method
        if description is not None:
            updates["description"] = description
        if request_schema is not None:
            updates["request_schema"] = request_schema
        if response_schema is not None:
            updates["response_schema"] = response_schema
        if updates:
            res = _app.supabase.table("api_endpoints").update(updates).eq("id", endpoint.id).execute()
            if res.data:
                for k, v in res.data[0].items():
                    setattr(endpoint, k, v)
        return endpoint

    @staticmethod
    def delete(endpoint):
        _app.supabase.table("api_endpoints").delete().eq("id", endpoint.id).execute()
