from datetime import datetime
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


def _screen(d):
    d = dict(d)
    for field in ("created_at", "updated_at"):
        if field in d:
            d[field] = _parse_dt(d[field])
    return SimpleNamespace(**d)


class ScreenService:
    @staticmethod
    def get_all_for_project(project_id):
        res = (
            _app.supabase.table("screens")
            .select("*")
            .eq("project_id", project_id)
            .order("updated_at", desc=True)
            .execute()
        )
        return [_screen(d) for d in res.data]

    @staticmethod
    def get(id):
        res = _app.supabase.table("screens").select("*").eq("id", id).maybe_single().execute()
        if not res or not getattr(res, "data", None):
            return None
        return _screen(res.data)

    @staticmethod
    def create(project_id, name, device_type="desktop", description="", data=None):
        res = _app.supabase.table("screens").insert({
            "project_id": project_id,
            "name": name,
            "device_type": device_type,
            "description": description,
            "data": data or {},
        }).execute()
        return _screen(res.data[0])

    @staticmethod
    def update(screen, name=None, device_type=None, description=None, data=None):
        updates = {}
        if name is not None:
            updates["name"] = name
        if device_type is not None:
            updates["device_type"] = device_type
        if description is not None:
            updates["description"] = description
        if data is not None:
            updates["data"] = data
        if updates:
            res = _app.supabase.table("screens").update(updates).eq("id", screen.id).execute()
            if res.data:
                for k, v in res.data[0].items():
                    setattr(screen, k, v)
        return screen

    @staticmethod
    def update_data(screen_id, data):
        res = (
            _app.supabase.table("screens")
            .update({"data": data})
            .eq("id", screen_id)
            .execute()
        )
        return _screen(res.data[0]) if res.data else None

    @staticmethod
    def delete(screen):
        _app.supabase.table("screens").delete().eq("id", screen.id).execute()
