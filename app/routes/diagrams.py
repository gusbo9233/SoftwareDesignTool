from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, Response
from werkzeug.utils import secure_filename

from app.services.project_service import ProjectService
from app.services.diagram_service import DiagramService
from app.services.module_service import ModuleService, ModuleStorageUnavailableError
from app.export.export_service import ExportService

diagrams_bp = Blueprint("diagrams", __name__)

DIAGRAM_TYPES = {
    "architecture": "Architecture",
    "uml_class": "UML Class",
    "uml_sequence": "UML Sequence",
    "uml_component": "UML Component",
    "er": "Entity-Relationship",
    "workflow": "Workflow",
}


def _get_project_or_redirect(project_id):
    project = ProjectService.get(project_id)
    if not project:
        flash("Project not found.", "error")
        return None
    return project


# --- Page routes ---

def _get_active_module_ids(project_id):
    session_key = f"module_filter_{project_id}"
    selected = session.get(session_key, "")
    if not selected:
        return None
    modules_flat = ModuleService.get_all_for_project(project_id)
    by_id = {m.id: m for m in modules_flat}
    if selected not in by_id:
        return None
    for m in modules_flat:
        m.children = []
    for m in modules_flat:
        if m.parent_id and m.parent_id in by_id:
            by_id[m.parent_id].children.append(m)
    def _collect(node):
        ids = {node.id}
        for child in node.children:
            ids |= _collect(child)
        return ids
    return _collect(by_id[selected])


@diagrams_bp.route("/projects/<project_id>/diagrams")
def index(project_id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))

    session_key = f"module_filter_{project_id}"
    if "module_id" in request.args:
        selected_module_id = request.args["module_id"]
        if selected_module_id:
            session[session_key] = selected_module_id
        else:
            session.pop(session_key, None)
    else:
        selected_module_id = session.get(session_key, "")

    diagrams = DiagramService.get_all_for_project(project_id)
    modules_flat = ModuleService.get_all_for_project(project_id)
    active_module_ids = _get_active_module_ids(project_id)
    if active_module_ids is not None:
        diagrams = [d for d in diagrams if getattr(d, "module_id", None) in active_module_ids]
    return render_template(
        "diagrams/index.html",
        project=project,
        diagrams=diagrams,
        modules_flat=modules_flat,
        selected_module_id=selected_module_id,
        type_labels=DIAGRAM_TYPES,
    )


@diagrams_bp.route("/projects/<project_id>/diagrams/new", methods=["GET", "POST"])
def create(project_id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))

    modules = ModuleService.get_all_for_project(project_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        diagram_type = request.form.get("type", "")
        module_id = request.form.get("module_id", "").strip() or None
        if not name:
            flash("Diagram name is required.", "error")
            return render_template(
                "diagrams/new.html", project=project, type_labels=DIAGRAM_TYPES, modules=modules
            )
        if diagram_type not in DIAGRAM_TYPES:
            flash("Invalid diagram type.", "error")
            return render_template(
                "diagrams/new.html", project=project, type_labels=DIAGRAM_TYPES, modules=modules
            )
        try:
            diagram = DiagramService.create(
                project_id=project_id, diagram_type=diagram_type, name=name, module_id=module_id
            )
        except ModuleStorageUnavailableError as exc:
            flash(str(exc), "error")
            return render_template(
                "diagrams/new.html",
                project=project,
                type_labels=DIAGRAM_TYPES,
                modules=[],
                selected_module_id=None,
            )
        return redirect(
            url_for("diagrams.editor", project_id=project_id, id=diagram.id)
        )

    return render_template(
        "diagrams/new.html",
        project=project,
        type_labels=DIAGRAM_TYPES,
        modules=modules,
        selected_module_id=None,
    )


@diagrams_bp.route("/projects/<project_id>/diagrams/<id>")
def editor(project_id, id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))
    diagram = DiagramService.get(id)
    if not diagram or diagram.project_id != project_id:
        flash("Diagram not found.", "error")
        return redirect(url_for("diagrams.index", project_id=project_id))
    modules = ModuleService.get_all_for_project(project_id)
    return render_template(
        "diagrams/editor.html",
        project=project,
        diagram=diagram,
        modules=modules,
        selected_module_id=getattr(diagram, "module_id", None),
        type_label=DIAGRAM_TYPES.get(diagram.type, diagram.type),
    )


@diagrams_bp.route("/projects/<project_id>/diagrams/<id>/module", methods=["POST"])
def update_module(project_id, id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))
    diagram = DiagramService.get(id)
    if not diagram or diagram.project_id != project_id:
        flash("Diagram not found.", "error")
        return redirect(url_for("diagrams.index", project_id=project_id))
    module_id = request.form.get("module_id", "").strip()
    DiagramService.update(diagram, module_id=module_id if module_id else "")
    flash("Module updated.", "success")
    return redirect(url_for("diagrams.editor", project_id=project_id, id=id))


@diagrams_bp.route("/projects/<project_id>/diagrams/<id>/delete", methods=["POST"])
def delete(project_id, id):
    diagram = DiagramService.get(id)
    if diagram and diagram.project_id == project_id:
        DiagramService.delete(diagram)
        flash("Diagram deleted.", "success")
    return redirect(url_for("diagrams.index", project_id=project_id))


@diagrams_bp.route("/projects/<project_id>/diagrams/<id>/export")
def export(project_id, id):
    diagram = DiagramService.get(id)
    if not diagram or diagram.project_id != project_id:
        flash("Diagram not found.", "error")
        return redirect(url_for("diagrams.index", project_id=project_id))

    fmt = request.args.get("format", "json")
    filename_root = secure_filename(diagram.name or "diagram") or "diagram"

    if fmt == "markdown":
        result = ExportService.export_diagram_markdown(project_id, id)
        if result is None:
            return jsonify({"error": "Diagram not found"}), 404
        return Response(
            result,
            mimetype="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={filename_root}.md"},
        )

    result = ExportService.export_diagram_json(project_id, id)
    if result is None:
        return jsonify({"error": "Diagram not found"}), 404
    return Response(
        jsonify(result).get_data(as_text=True),
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename_root}.json"},
    )


# --- JSON API routes (used by React Flow frontend) ---

@diagrams_bp.route("/api/diagrams/<id>", methods=["GET"])
def api_get(id):
    diagram = DiagramService.get(id)
    if not diagram:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "id": diagram.id,
        "project_id": diagram.project_id,
        "type": diagram.type,
        "name": diagram.name,
        "module_id": getattr(diagram, "module_id", None),
        "data": diagram.data,
    })


@diagrams_bp.route("/api/diagrams/<id>", methods=["PUT"])
def api_update(id):
    diagram = DiagramService.get(id)
    if not diagram:
        return jsonify({"error": "not found"}), 404
    body = request.get_json()
    if not body:
        return jsonify({"error": "invalid JSON"}), 400
    DiagramService.update(
        diagram,
        name=body.get("name"),
        data=body.get("data"),
    )
    return jsonify({"status": "ok"})
