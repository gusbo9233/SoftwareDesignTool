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


class ModuleStorageUnavailableError(RuntimeError):
    """Raised when the backing modules table is not available in Supabase."""


def _error_payload(exc):
    payload = {}
    if hasattr(exc, "code"):
        payload["code"] = getattr(exc, "code", None)
    if hasattr(exc, "message"):
        payload["message"] = getattr(exc, "message", None)
    if hasattr(exc, "details"):
        payload["details"] = getattr(exc, "details", None)
    if payload:
        return payload
    if hasattr(exc, "args") and exc.args:
        first = exc.args[0]
        if isinstance(first, dict):
            return first
    if isinstance(exc, dict):
        return exc
    return {}


def _is_missing_modules_table_error(exc):
    payload = _error_payload(exc)
    message = str(payload.get("message", ""))
    code = payload.get("code")
    return code == "PGRST205" and "public.modules" in message


def _missing_modules_table_message():
    return "Modules are unavailable because the database schema is missing the modules table."


class ModuleService:
    @staticmethod
    def get_all_for_project(project_id):
        try:
            res = (
                _app.supabase.table("modules")
                .select("*")
                .eq("project_id", project_id)
                .order("position")
                .execute()
            )
        except Exception as exc:
            if _is_missing_modules_table_error(exc):
                return []
            raise
        return [_module(d) for d in res.data]

    @staticmethod
    def get(id):
        try:
            res = (
                _app.supabase.table("modules")
                .select("*")
                .eq("id", id)
                .maybe_single()
                .execute()
            )
        except Exception as exc:
            if _is_missing_modules_table_error(exc):
                return None
            raise
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
        try:
            res = _app.supabase.table("modules").insert(payload).execute()
        except Exception as exc:
            if _is_missing_modules_table_error(exc):
                raise ModuleStorageUnavailableError(_missing_modules_table_message()) from exc
            raise
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
            try:
                res = (
                    _app.supabase.table("modules")
                    .update(updates)
                    .eq("id", module.id)
                    .execute()
                )
            except Exception as exc:
                if _is_missing_modules_table_error(exc):
                    raise ModuleStorageUnavailableError(_missing_modules_table_message()) from exc
                raise
            if res.data:
                updated = _module(res.data[0])
                for k, v in vars(updated).items():
                    setattr(module, k, v)
        return module

    @staticmethod
    def delete(module):
        """Delete a module. Related documents and diagrams get module_id set to None."""
        from app.services.document_service import DocumentService
        from app.services.diagram_service import DiagramService
        docs = DocumentService.get_all_for_project(module.project_id, module_id=module.id)
        for doc in docs:
            DocumentService.update(doc, module_id="")
        diagrams = DiagramService.get_all_for_project(module.project_id, module_id=module.id)
        for diagram in diagrams:
            DiagramService.update(diagram, module_id="")
        # Re-parent children to this module's parent
        try:
            children = (
                _app.supabase.table("modules")
                .select("*")
                .eq("parent_id", module.id)
                .execute()
            )
        except Exception as exc:
            if _is_missing_modules_table_error(exc):
                raise ModuleStorageUnavailableError(_missing_modules_table_message()) from exc
            raise
        for child_data in children.data:
            try:
                _app.supabase.table("modules").update(
                    {"parent_id": module.parent_id}
                ).eq("id", child_data["id"]).execute()
            except Exception as exc:
                if _is_missing_modules_table_error(exc):
                    raise ModuleStorageUnavailableError(_missing_modules_table_message()) from exc
                raise
        try:
            _app.supabase.table("modules").delete().eq("id", module.id).execute()
        except Exception as exc:
            if _is_missing_modules_table_error(exc):
                raise ModuleStorageUnavailableError(_missing_modules_table_message()) from exc
            raise

    @staticmethod
    def count_documents(module_id, documents):
        """Count documents belonging to a module (including descendants), given a flat doc list."""
        return sum(1 for d in documents if getattr(d, "module_id", None) == module_id)
