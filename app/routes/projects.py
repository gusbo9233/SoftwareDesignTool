from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response

from app.services.project_service import ProjectService, ProjectServiceUnavailableError
from app.services.document_service import DocumentService
from app.services.project_template_service import ProjectTemplateService
from app.export.export_service import ExportService

projects_bp = Blueprint("projects", __name__)


@projects_bp.route("/")
def index():
    try:
        projects = ProjectService.get_all()
    except ProjectServiceUnavailableError as exc:
        flash(str(exc), "error")
        projects = []
    return render_template("dashboard.html", projects=projects)


@projects_bp.route("/projects/new", methods=["GET", "POST"])
def create():
    available_templates = ProjectTemplateService.list_templates()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        template_key = ProjectTemplateService.normalize_template_key(request.form.get("template_key"))
        if not name:
            flash("Project name is required.", "error")
            return render_template(
                "project_form.html",
                project=None,
                available_templates=available_templates,
                selected_template=template_key,
            )
        try:
            project = ProjectService.create(name=name, description=description, template_key=template_key)
            ProjectTemplateService.seed_project_template(project, template_key)
        except ProjectServiceUnavailableError as exc:
            flash(str(exc), "error")
            return render_template(
                "project_form.html",
                project=None,
                available_templates=available_templates,
                selected_template=template_key,
            )
        return redirect(url_for("projects.detail", id=project.id))
    return render_template(
        "project_form.html",
        project=None,
        available_templates=available_templates,
        selected_template=ProjectTemplateService.normalize_template_key(None),
    )


@projects_bp.route("/projects/<id>")
def detail(id):
    try:
        project = ProjectService.get(id)
    except ProjectServiceUnavailableError as exc:
        flash(str(exc), "error")
        return redirect(url_for("projects.index"))
    if not project:
        flash("Project not found.", "error")
        return redirect(url_for("projects.index"))
    documents = DocumentService.get_all_for_project(project.id)
    if ProjectTemplateService.ensure_project_template(project, documents=documents):
        documents = DocumentService.get_all_for_project(project.id)
    project_template = ProjectTemplateService.as_view_model(project=project, documents=documents)
    return render_template("project_detail.html", project=project, project_template=project_template)


@projects_bp.route("/projects/<id>/edit", methods=["GET", "POST"])
def edit(id):
    available_templates = ProjectTemplateService.list_templates()
    try:
        project = ProjectService.get(id)
    except ProjectServiceUnavailableError as exc:
        flash(str(exc), "error")
        return redirect(url_for("projects.index"))
    if not project:
        flash("Project not found.", "error")
        return redirect(url_for("projects.index"))
    documents = DocumentService.get_all_for_project(project.id)
    if ProjectTemplateService.ensure_project_template(project, documents=documents):
        documents = DocumentService.get_all_for_project(project.id)
    selected_template = ProjectTemplateService.resolve_template_key(project=project, documents=documents)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        template_key = ProjectTemplateService.normalize_template_key(request.form.get("template_key"))
        if not name:
            flash("Project name is required.", "error")
            return render_template(
                "project_form.html",
                project=project,
                available_templates=available_templates,
                selected_template=template_key,
            )
        try:
            ProjectService.update(project, name=name, description=description, template_key=template_key)
            ProjectTemplateService.seed_project_template(project, template_key)
        except ProjectServiceUnavailableError as exc:
            flash(str(exc), "error")
            return render_template(
                "project_form.html",
                project=project,
                available_templates=available_templates,
                selected_template=template_key,
            )
        return redirect(url_for("projects.detail", id=project.id))
    return render_template(
        "project_form.html",
        project=project,
        available_templates=available_templates,
        selected_template=selected_template,
    )


@projects_bp.route("/projects/<id>/delete", methods=["POST"])
def delete(id):
    try:
        project = ProjectService.get(id)
    except ProjectServiceUnavailableError as exc:
        flash(str(exc), "error")
        return redirect(url_for("projects.index"))
    if project:
        try:
            ProjectService.delete(project)
        except ProjectServiceUnavailableError as exc:
            flash(str(exc), "error")
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
