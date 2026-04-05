from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify

from app.services.project_service import ProjectService
from app.services.diagram_service import DiagramService

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

@diagrams_bp.route("/projects/<project_id>/diagrams")
def index(project_id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))
    diagrams = DiagramService.get_all_for_project(project_id)
    return render_template(
        "diagrams/index.html",
        project=project,
        diagrams=diagrams,
        type_labels=DIAGRAM_TYPES,
    )


@diagrams_bp.route("/projects/<project_id>/diagrams/new", methods=["GET", "POST"])
def create(project_id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        diagram_type = request.form.get("type", "")
        if not name:
            flash("Diagram name is required.", "error")
            return render_template(
                "diagrams/new.html", project=project, type_labels=DIAGRAM_TYPES
            )
        if diagram_type not in DIAGRAM_TYPES:
            flash("Invalid diagram type.", "error")
            return render_template(
                "diagrams/new.html", project=project, type_labels=DIAGRAM_TYPES
            )
        diagram = DiagramService.create(
            project_id=project_id, diagram_type=diagram_type, name=name
        )
        return redirect(
            url_for("diagrams.editor", project_id=project_id, id=diagram.id)
        )

    return render_template(
        "diagrams/new.html", project=project, type_labels=DIAGRAM_TYPES
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
    return render_template(
        "diagrams/editor.html",
        project=project,
        diagram=diagram,
        type_label=DIAGRAM_TYPES.get(diagram.type, diagram.type),
    )


@diagrams_bp.route("/projects/<project_id>/diagrams/<id>/delete", methods=["POST"])
def delete(project_id, id):
    diagram = DiagramService.get(id)
    if diagram and diagram.project_id == project_id:
        DiagramService.delete(diagram)
        flash("Diagram deleted.", "success")
    return redirect(url_for("diagrams.index", project_id=project_id))


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
