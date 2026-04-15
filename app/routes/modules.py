from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.services.project_service import ProjectService
from app.services.module_service import ModuleService, ModuleStorageUnavailableError

modules_bp = Blueprint("modules", __name__)


def _get_project_or_redirect(project_id):
    project = ProjectService.get(project_id)
    if not project:
        flash("Project not found.", "error")
        return None
    return project


@modules_bp.route("/projects/<project_id>/modules/new", methods=["GET", "POST"])
def create(project_id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))

    all_modules = ModuleService.get_all_for_project(project_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        parent_id = request.form.get("parent_id", "").strip() or None
        if not name:
            flash("Module name is required.", "error")
            return render_template(
                "modules/form.html",
                project=project,
                module=None,
                all_modules=all_modules,
            )
        try:
            ModuleService.create(
                project_id=project_id,
                name=name,
                description=description,
                parent_id=parent_id,
            )
        except ModuleStorageUnavailableError as exc:
            flash(str(exc), "error")
            return redirect(url_for("documents.index", project_id=project_id))
        flash(f'Module "{name}" created.', "success")
        return redirect(url_for("documents.index", project_id=project_id))

    return render_template(
        "modules/form.html",
        project=project,
        module=None,
        all_modules=all_modules,
    )


@modules_bp.route("/projects/<project_id>/modules/<module_id>/edit", methods=["GET", "POST"])
def edit(project_id, module_id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))

    module = ModuleService.get(module_id)
    if not module:
        flash("Module not found.", "error")
        return redirect(url_for("documents.index", project_id=project_id))

    all_modules = [m for m in ModuleService.get_all_for_project(project_id) if m.id != module_id]

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        parent_id = request.form.get("parent_id", "").strip() or None
        if not name:
            flash("Module name is required.", "error")
            return render_template(
                "modules/form.html",
                project=project,
                module=module,
                all_modules=all_modules,
            )
        try:
            ModuleService.update(
                module,
                name=name,
                description=description,
                parent_id=parent_id if parent_id else "",
            )
        except ModuleStorageUnavailableError as exc:
            flash(str(exc), "error")
            return redirect(url_for("documents.index", project_id=project_id))
        flash(f'Module "{name}" updated.', "success")
        return redirect(url_for("documents.index", project_id=project_id))

    return render_template(
        "modules/form.html",
        project=project,
        module=module,
        all_modules=all_modules,
    )


@modules_bp.route("/projects/<project_id>/modules/<module_id>/delete", methods=["POST"])
def delete(project_id, module_id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))

    module = ModuleService.get(module_id)
    if not module:
        flash("Module not found.", "error")
        return redirect(url_for("documents.index", project_id=project_id))

    name = module.name
    try:
        ModuleService.delete(module)
    except ModuleStorageUnavailableError as exc:
        flash(str(exc), "error")
        return redirect(url_for("documents.index", project_id=project_id))
    flash(f'Module "{name}" deleted. Its documents are now unassigned.', "success")
    return redirect(url_for("documents.index", project_id=project_id))
