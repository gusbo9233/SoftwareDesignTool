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


def _module(d):
    d = dict(d)
    for field in ("created_at", "updated_at"):
        if field in d:
            d[field] = _parse_dt(d[field])
    d.setdefault("parent_id", None)
    d.setdefault("description", "")
    d.setdefault("position", 0)
    return SimpleNamespace(**d)


class ModuleService:
    @staticmethod
    def get_all_for_project(project_id):
        res = (
            _app.supabase.table("modules")
            .select("*")
            .eq("project_id", project_id)
            .order("position")
            .execute()
        )
        return [_module(d) for d in res.data]

    @staticmethod
    def get(id):
        res = (
            _app.supabase.table("modules")
            .select("*")
            .eq("id", id)
            .maybe_single()
            .execute()
        )
        return _module(res.data) if res.data else None

    @staticmethod
    def get_tree_for_project(project_id):
        """Build a nested tree from the flat list of modules."""
        modules = ModuleService.get_all_for_project(project_id)
        by_id = {m.id: m for m in modules}
        roots = []
        for m in modules:
            m.children = []
            m.documents = []
        for m in modules:
            if m.parent_id and m.parent_id in by_id:
                by_id[m.parent_id].children.append(m)
            else:
                roots.append(m)
        return roots

    @staticmethod
    def create(project_id, name, description="", parent_id=None, position=0):
        payload = {
            "project_id": project_id,
            "name": name,
            "description": description,
            "parent_id": parent_id or None,
            "position": position,
        }
        res = _app.supabase.table("modules").insert(payload).execute()
        return _module(res.data[0])

    @staticmethod
    def update(module, name=None, description=None, parent_id=None, position=None):
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if parent_id is not None:
            updates["parent_id"] = parent_id if parent_id != "" else None
        if position is not None:
            updates["position"] = position
        if updates:
            res = (
                _app.supabase.table("modules")
                .update(updates)
                .eq("id", module.id)
                .execute()
            )
            if res.data:
                updated = _module(res.data[0])
                for k, v in vars(updated).items():
                    setattr(module, k, v)
        return module

    @staticmethod
    def delete(module):
        """Delete a module. Documents belonging to it get module_id set to None."""
        from app.services.document_service import DocumentService
        docs = DocumentService.get_all_for_project(module.project_id, module_id=module.id)
        for doc in docs:
            DocumentService.update(doc, module_id="")
        # Re-parent children to this module's parent
        children = (
            _app.supabase.table("modules")
            .select("*")
            .eq("parent_id", module.id)
            .execute()
        )
        for child_data in children.data:
            _app.supabase.table("modules").update(
                {"parent_id": module.parent_id}
            ).eq("id", child_data["id"]).execute()
        _app.supabase.table("modules").delete().eq("id", module.id).execute()

    @staticmethod
    def count_documents(module_id, documents):
        """Count documents belonging to a module (including descendants), given a flat doc list."""
        return sum(1 for d in documents if getattr(d, "module_id", None) == module_id)
