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


def _doc(d):
    d = dict(d)
    for field in ("created_at", "updated_at"):
        if field in d:
            d[field] = _parse_dt(d[field])
    return SimpleNamespace(**d)


class DocumentService:
    @staticmethod
    def get_all_for_project(project_id, doc_type=None):
        query = _app.supabase.table("documents").select("*").eq("project_id", project_id)
        if doc_type:
            query = query.eq("type", doc_type)
        res = query.order("updated_at", desc=True).execute()
        return [_doc(d) for d in res.data]

    @staticmethod
    def get(id):
        res = _app.supabase.table("documents").select("*").eq("id", id).maybe_single().execute()
        return _doc(res.data) if res.data else None

    @staticmethod
    def create(project_id, doc_type, data=None):
        res = _app.supabase.table("documents").insert({
            "project_id": project_id,
            "type": doc_type,
            "data": data or {},
        }).execute()
        return SimpleNamespace(**res.data[0])

    @staticmethod
    def update(doc, data=None, doc_type=None):
        updates = {}
        if data is not None:
            updates["data"] = data
        if doc_type is not None:
            updates["type"] = doc_type
        if updates:
            res = _app.supabase.table("documents").update(updates).eq("id", doc.id).execute()
            if res.data:
                for k, v in res.data[0].items():
                    setattr(doc, k, v)
        return doc

    @staticmethod
    def delete(doc):
        _app.supabase.table("documents").delete().eq("id", doc.id).execute()
