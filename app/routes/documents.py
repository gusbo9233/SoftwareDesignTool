from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.services.project_service import ProjectService
from app.services.document_service import DocumentService

documents_bp = Blueprint("documents", __name__)

DOCUMENT_TYPES = {
    "user_story": "User Story",
    "requirement": "Requirement",
    "project_plan": "Project Plan",
    "test_plan": "Test Plan",
}

TEMPLATE_MAP = {
    "user_story": "documents/user_story_form.html",
    "requirement": "documents/requirement_form.html",
    "project_plan": "documents/project_plan_form.html",
    "test_plan": "documents/test_plan_form.html",
}


def _get_project_or_redirect(project_id):
    project = ProjectService.get(project_id)
    if not project:
        flash("Project not found.", "error")
        return None
    return project


def _parse_user_story(form):
    criteria = [c.strip() for c in form.getlist("acceptance_criteria") if c.strip()]
    return {
        "user_type": form.get("user_type", "").strip(),
        "action": form.get("action", "").strip(),
        "benefit": form.get("benefit", "").strip(),
        "priority": form.get("priority", "medium"),
        "status": form.get("status", "draft"),
        "acceptance_criteria": criteria,
    }


def _parse_requirement(form):
    return {
        "title": form.get("title", "").strip(),
        "description": form.get("description", "").strip(),
        "type": form.get("req_type", "functional"),
        "category": form.get("category", "").strip(),
        "priority": form.get("priority", "should"),
        "status": form.get("status", "draft"),
        "rationale": form.get("rationale", "").strip(),
    }


def _parse_project_plan(form):
    goals = [g.strip() for g in form.getlist("goals") if g.strip()]
    in_scope = [s.strip() for s in form.getlist("in_scope") if s.strip()]
    out_scope = [s.strip() for s in form.getlist("out_scope") if s.strip()]

    milestone_names = form.getlist("milestone_name")
    milestone_dates = form.getlist("milestone_date")
    milestone_deliverables = form.getlist("milestone_deliverables")
    milestone_statuses = form.getlist("milestone_status")
    milestones = []
    for i in range(len(milestone_names)):
        name = milestone_names[i].strip() if i < len(milestone_names) else ""
        if name:
            milestones.append({
                "name": name,
                "target_date": milestone_dates[i].strip() if i < len(milestone_dates) else "",
                "deliverables": milestone_deliverables[i].strip() if i < len(milestone_deliverables) else "",
                "status": milestone_statuses[i].strip() if i < len(milestone_statuses) else "planned",
            })

    risk_descs = form.getlist("risk_description")
    risk_likelihoods = form.getlist("risk_likelihood")
    risk_impacts = form.getlist("risk_impact")
    risk_mitigations = form.getlist("risk_mitigation")
    risks = []
    for i in range(len(risk_descs)):
        desc = risk_descs[i].strip() if i < len(risk_descs) else ""
        if desc:
            risks.append({
                "description": desc,
                "likelihood": risk_likelihoods[i].strip() if i < len(risk_likelihoods) else "medium",
                "impact": risk_impacts[i].strip() if i < len(risk_impacts) else "medium",
                "mitigation": risk_mitigations[i].strip() if i < len(risk_mitigations) else "",
            })

    return {
        "project_name": form.get("project_name", "").strip(),
        "project_description": form.get("project_description", "").strip(),
        "goals": goals,
        "in_scope": in_scope,
        "out_scope": out_scope,
        "milestones": milestones,
        "risks": risks,
    }


def _parse_test_plan(form):
    case_descs = form.getlist("case_description")
    case_steps = form.getlist("case_steps")
    case_expected = form.getlist("case_expected")
    case_statuses = form.getlist("case_status")
    test_cases = []
    for i in range(len(case_descs)):
        desc = case_descs[i].strip() if i < len(case_descs) else ""
        if desc:
            test_cases.append({
                "description": desc,
                "steps": case_steps[i].strip() if i < len(case_steps) else "",
                "expected_result": case_expected[i].strip() if i < len(case_expected) else "",
                "status": case_statuses[i].strip() if i < len(case_statuses) else "not_run",
            })

    return {
        "test_scope": form.get("test_scope", "").strip(),
        "test_strategy": form.get("test_strategy", "").strip(),
        "test_cases": test_cases,
        "entry_criteria": form.get("entry_criteria", "").strip(),
        "exit_criteria": form.get("exit_criteria", "").strip(),
        "environment": form.get("environment", "").strip(),
    }


PARSERS = {
    "user_story": _parse_user_story,
    "requirement": _parse_requirement,
    "project_plan": _parse_project_plan,
    "test_plan": _parse_test_plan,
}


def _validate_document_data(doc_type, data):
    """Return error message if validation fails, else None."""
    if doc_type == "user_story":
        if not data.get("user_type") or not data.get("action") or not data.get("benefit"):
            return "User type, action, and benefit are required."
    elif doc_type == "requirement":
        if not data.get("title") or not data.get("description"):
            return "Title and description are required."
    elif doc_type == "project_plan":
        if not data.get("project_name"):
            return "Project name is required."
    elif doc_type == "test_plan":
        if not data.get("test_scope"):
            return "Test scope is required."
    return None


@documents_bp.route("/projects/<project_id>/documents")
def index(project_id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))
    documents = DocumentService.get_all_for_project(project_id)
    return render_template("documents/index.html", project=project, documents=documents, type_labels=DOCUMENT_TYPES)


@documents_bp.route("/projects/<project_id>/documents/new/<doc_type>", methods=["GET", "POST"])
def create(project_id, doc_type):
    if doc_type not in DOCUMENT_TYPES:
        flash("Invalid document type.", "error")
        return redirect(url_for("documents.index", project_id=project_id))

    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))

    if request.method == "POST":
        parser = PARSERS[doc_type]
        data = parser(request.form)
        error = _validate_document_data(doc_type, data)
        if error:
            flash(error, "error")
            return render_template(TEMPLATE_MAP[doc_type], project=project, document=None, data=data)
        doc = DocumentService.create(project_id=project_id, doc_type=doc_type, data=data)
        flash(f"{DOCUMENT_TYPES[doc_type]} created.", "success")
        return redirect(url_for("documents.detail", project_id=project_id, id=doc.id))

    return render_template(TEMPLATE_MAP[doc_type], project=project, document=None, data={})


@documents_bp.route("/projects/<project_id>/documents/<id>")
def detail(project_id, id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))
    doc = DocumentService.get(id)
    if not doc or doc.project_id != project_id:
        flash("Document not found.", "error")
        return redirect(url_for("documents.index", project_id=project_id))
    return render_template(
        f"documents/{doc.type}_detail.html",
        project=project, document=doc, data=doc.data, type_label=DOCUMENT_TYPES[doc.type],
    )


@documents_bp.route("/projects/<project_id>/documents/<id>/edit", methods=["GET", "POST"])
def edit(project_id, id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))
    doc = DocumentService.get(id)
    if not doc or doc.project_id != project_id:
        flash("Document not found.", "error")
        return redirect(url_for("documents.index", project_id=project_id))

    if request.method == "POST":
        parser = PARSERS[doc.type]
        data = parser(request.form)
        error = _validate_document_data(doc.type, data)
        if error:
            flash(error, "error")
            return render_template(TEMPLATE_MAP[doc.type], project=project, document=doc, data=data)
        DocumentService.update(doc, data=data)
        flash(f"{DOCUMENT_TYPES[doc.type]} updated.", "success")
        return redirect(url_for("documents.detail", project_id=project_id, id=doc.id))

    return render_template(TEMPLATE_MAP[doc.type], project=project, document=doc, data=doc.data)


@documents_bp.route("/projects/<project_id>/documents/<id>/delete", methods=["POST"])
def delete(project_id, id):
    doc = DocumentService.get(id)
    if doc and doc.project_id == project_id:
        DocumentService.delete(doc)
        flash("Document deleted.", "success")
    return redirect(url_for("documents.index", project_id=project_id))
