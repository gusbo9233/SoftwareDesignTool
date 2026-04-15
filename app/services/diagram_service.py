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


def _diagram(d):
    d = dict(d)
    for field in ("created_at", "updated_at"):
        if field in d:
            d[field] = _parse_dt(d[field])
    return SimpleNamespace(**d)


class DiagramService:
    @staticmethod
    def get_all_for_project(project_id, module_id=None):
        query = _app.supabase.table("diagrams").select("*").eq("project_id", project_id)
        if module_id is not None:
            query = query.eq("module_id", module_id)
        res = query.order("updated_at", desc=True).execute()
        return [_diagram(d) for d in res.data]

    @staticmethod
    def get(id):
        res = _app.supabase.table("diagrams").select("*").eq("id", id).maybe_single().execute()
        return _diagram(res.data) if res.data else None

    @staticmethod
    def create(project_id, diagram_type, name, data=None, module_id=None):
        payload = {
            "project_id": project_id,
            "type": diagram_type,
            "name": name,
            "data": data or {"nodes": [], "edges": []},
        }
        if module_id:
            payload["module_id"] = module_id
        res = _app.supabase.table("diagrams").insert(payload).execute()
        return _diagram(res.data[0])

    @staticmethod
    def update(diagram, name=None, data=None, module_id=None):
        updates = {}
        if name is not None:
            updates["name"] = name
        if data is not None:
            updates["data"] = data
        if module_id is not None:
            updates["module_id"] = module_id if module_id != "" else None
        if updates:
            res = _app.supabase.table("diagrams").update(updates).eq("id", diagram.id).execute()
            if res.data:
                parsed = _diagram(res.data[0])
                for k, v in vars(parsed).items():
                    setattr(diagram, k, v)
        return diagram

    @staticmethod
    def delete(diagram):
        _app.supabase.table("diagrams").delete().eq("id", diagram.id).execute()
