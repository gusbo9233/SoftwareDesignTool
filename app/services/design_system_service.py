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


def _design_system(d):
    d = dict(d)
    for field in ("created_at", "updated_at"):
        if field in d:
            d[field] = _parse_dt(d[field])
    return SimpleNamespace(**d)


class DesignSystemService:
    @staticmethod
    def get_for_project(project_id):
        res = (
            _app.supabase.table("design_systems")
            .select("*")
            .eq("project_id", project_id)
            .execute()
        )
        if res.data:
            return _design_system(res.data[0])
        return None

    @staticmethod
    def get(id):
        res = _app.supabase.table("design_systems").select("*").eq("id", id).maybe_single().execute()
        return _design_system(res.data) if res.data else None

    @staticmethod
    def create(project_id, name, data=None):
        res = _app.supabase.table("design_systems").insert({
            "project_id": project_id,
            "name": name,
            "data": data or {},
        }).execute()
        return _design_system(res.data[0])

    @staticmethod
    def update(design_system, name=None, data=None):
        updates = {}
        if name is not None:
            updates["name"] = name
        if data is not None:
            updates["data"] = data
        if updates:
            res = _app.supabase.table("design_systems").update(updates).eq("id", design_system.id).execute()
            if res.data:
                for k, v in res.data[0].items():
                    setattr(design_system, k, v)
        return design_system

    @staticmethod
    def delete(design_system):
        _app.supabase.table("design_systems").delete().eq("id", design_system.id).execute()
