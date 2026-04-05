from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response

from app.services.project_service import ProjectService
from app.export.export_service import ExportService

projects_bp = Blueprint("projects", __name__)


@projects_bp.route("/")
def index():
    projects = ProjectService.get_all()
    return render_template("dashboard.html", projects=projects)


@projects_bp.route("/projects/new", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        if not name:
            flash("Project name is required.", "error")
            return render_template("project_form.html", project=None)
        project = ProjectService.create(name=name, description=description)
        return redirect(url_for("projects.detail", id=project.id))
    return render_template("project_form.html", project=None)


@projects_bp.route("/projects/<id>")
def detail(id):
    project = ProjectService.get(id)
    if not project:
        flash("Project not found.", "error")
        return redirect(url_for("projects.index"))
    return render_template("project_detail.html", project=project)


@projects_bp.route("/projects/<id>/edit", methods=["GET", "POST"])
def edit(id):
    project = ProjectService.get(id)
    if not project:
        flash("Project not found.", "error")
        return redirect(url_for("projects.index"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        if not name:
            flash("Project name is required.", "error")
            return render_template("project_form.html", project=project)
        ProjectService.update(project, name=name, description=description)
        return redirect(url_for("projects.detail", id=project.id))
    return render_template("project_form.html", project=project)


@projects_bp.route("/projects/<id>/delete", methods=["POST"])
def delete(id):
    project = ProjectService.get(id)
    if project:
        ProjectService.delete(project)
    return redirect(url_for("projects.index"))


@projects_bp.route("/api/projects/<id>/export")
def export(id):
    fmt = request.args.get("format", "json")
    if fmt == "markdown":
        result = ExportService.export_markdown(id)
        if result is None:
            return jsonify({"error": "Project not found"}), 404
        return Response(result, mimetype="text/markdown",
                        headers={"Content-Disposition": "attachment; filename=export.md"})
    else:
        result = ExportService.export_json(id)
        if result is None:
            return jsonify({"error": "Project not found"}), 404
        return jsonify(result)
