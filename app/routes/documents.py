from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.services.project_service import ProjectService
from app.services.document_service import DocumentService
from app.services.traceability_service import TraceabilityService

documents_bp = Blueprint("documents", __name__)

DOCUMENT_TYPES = {
    "user_story": "User Story",
    "requirement": "Requirement",
    "project_plan": "Project Plan",
    "test_plan": "Test Plan",
    "adr": "Architecture Decision Record",
    "tech_stack": "Technology Stack",
    "nfr": "Non-Functional Requirement",
    "risk_register": "Risk Register",
    "domain_model": "Domain Model",
    "acceptance_test": "Acceptance Test",
    "external_resource": "External Resource",
    "research": "Research Document",
}

TEMPLATE_MAP = {
    "user_story": "documents/user_story_form.html",
    "requirement": "documents/requirement_form.html",
    "project_plan": "documents/project_plan_form.html",
    "test_plan": "documents/test_plan_form.html",
    "adr": "documents/adr_form.html",
    "tech_stack": "documents/tech_stack_form.html",
    "nfr": "documents/nfr_form.html",
    "risk_register": "documents/risk_register_form.html",
    "domain_model": "documents/domain_model_form.html",
    "acceptance_test": "documents/acceptance_test_form.html",
    "external_resource": "documents/external_resource_form.html",
    "research": "documents/research_form.html",
}


def _get_project_or_redirect(project_id):
    project = ProjectService.get(project_id)
    if not project:
        flash("Project not found.", "error")
        return None
    return project


# --- Parsers ---

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


def _parse_adr(form):
    alt_names = form.getlist("alt_name")
    alt_pros = form.getlist("alt_pros")
    alt_cons = form.getlist("alt_cons")
    alternatives = []
    for i in range(len(alt_names)):
        name = alt_names[i].strip() if i < len(alt_names) else ""
        if name:
            alternatives.append({
                "name": name,
                "pros": alt_pros[i].strip() if i < len(alt_pros) else "",
                "cons": alt_cons[i].strip() if i < len(alt_cons) else "",
            })
    related_adrs = [r.strip() for r in form.getlist("related_adrs") if r.strip()]
    return {
        "title": form.get("title", "").strip(),
        "status": form.get("status", "proposed"),
        "context": form.get("context", "").strip(),
        "decision": form.get("decision", "").strip(),
        "alternatives": alternatives,
        "consequences": form.get("consequences", "").strip(),
        "related_adrs": related_adrs,
    }


def _parse_tech_stack(form):
    categories = form.getlist("tech_category")
    technologies = form.getlist("tech_technology")
    versions = form.getlist("tech_version")
    rationales = form.getlist("tech_rationale")
    alternatives = form.getlist("tech_alternatives")
    adr_refs = form.getlist("tech_adr_reference")
    items = []
    for i in range(len(technologies)):
        tech = technologies[i].strip() if i < len(technologies) else ""
        if tech:
            items.append({
                "category": categories[i].strip() if i < len(categories) else "",
                "technology": tech,
                "version": versions[i].strip() if i < len(versions) else "",
                "rationale": rationales[i].strip() if i < len(rationales) else "",
                "alternatives_considered": alternatives[i].strip() if i < len(alternatives) else "",
                "adr_reference": adr_refs[i].strip() if i < len(adr_refs) else "",
            })
    return {"items": items}


def _parse_nfr(form):
    return {
        "title": form.get("title", "").strip(),
        "category": form.get("category", "performance"),
        "description": form.get("description", "").strip(),
        "rationale": form.get("rationale", "").strip(),
        "priority": form.get("priority", "should"),
        "status": form.get("status", "draft"),
        "verification_method": form.get("verification_method", "").strip(),
    }


def _parse_risk_register(form):
    titles = form.getlist("risk_title")
    descriptions = form.getlist("risk_description")
    categories = form.getlist("risk_category")
    likelihoods = form.getlist("risk_likelihood")
    impacts = form.getlist("risk_impact")
    statuses = form.getlist("risk_status")
    owners = form.getlist("risk_owner")
    mitigations = form.getlist("risk_mitigation")
    review_dates = form.getlist("risk_review_date")
    notes_list = form.getlist("risk_notes")
    items = []
    for i in range(len(titles)):
        title = titles[i].strip() if i < len(titles) else ""
        if title:
            items.append({
                "title": title,
                "description": descriptions[i].strip() if i < len(descriptions) else "",
                "category": categories[i].strip() if i < len(categories) else "technical",
                "likelihood": likelihoods[i].strip() if i < len(likelihoods) else "medium",
                "impact": impacts[i].strip() if i < len(impacts) else "medium",
                "status": statuses[i].strip() if i < len(statuses) else "open",
                "owner": owners[i].strip() if i < len(owners) else "",
                "mitigation": mitigations[i].strip() if i < len(mitigations) else "",
                "review_date": review_dates[i].strip() if i < len(review_dates) else "",
                "notes": notes_list[i].strip() if i < len(notes_list) else "",
            })
    return {"items": items}


def _parse_domain_model(form):
    entity_names = form.getlist("entity_name")
    entity_descriptions = form.getlist("entity_description")
    entity_attributes = form.getlist("entity_key_attributes")
    entities = []
    for i in range(len(entity_names)):
        name = entity_names[i].strip() if i < len(entity_names) else ""
        if name:
            entities.append({
                "name": name,
                "description": entity_descriptions[i].strip() if i < len(entity_descriptions) else "",
                "key_attributes": entity_attributes[i].strip() if i < len(entity_attributes) else "",
            })

    glossary_terms = form.getlist("glossary_term")
    glossary_defs = form.getlist("glossary_definition")
    glossary = []
    for i in range(len(glossary_terms)):
        term = glossary_terms[i].strip() if i < len(glossary_terms) else ""
        if term:
            glossary.append({
                "term": term,
                "definition": glossary_defs[i].strip() if i < len(glossary_defs) else "",
            })

    business_rules = [r.strip() for r in form.getlist("business_rules") if r.strip()]

    ext_names = form.getlist("ext_name")
    ext_types = form.getlist("ext_type")
    ext_integrations = form.getlist("ext_integration_description")
    ext_owners = form.getlist("ext_owner")
    external_systems = []
    for i in range(len(ext_names)):
        name = ext_names[i].strip() if i < len(ext_names) else ""
        if name:
            external_systems.append({
                "name": name,
                "system_type": ext_types[i].strip() if i < len(ext_types) else "",
                "integration_description": ext_integrations[i].strip() if i < len(ext_integrations) else "",
                "owner": ext_owners[i].strip() if i < len(ext_owners) else "",
            })

    return {
        "bounded_context_name": form.get("bounded_context_name", "").strip(),
        "bounded_context_description": form.get("bounded_context_description", "").strip(),
        "entities": entities,
        "glossary": glossary,
        "business_rules": business_rules,
        "external_systems": external_systems,
    }


def _parse_acceptance_test(form):
    steps = [s.strip() for s in form.getlist("steps") if s.strip()]
    return {
        "title": form.get("title", "").strip(),
        "requirement_reference": form.get("requirement_reference", "").strip(),
        "user_story_reference": form.get("user_story_reference", "").strip(),
        "preconditions": form.get("preconditions", "").strip(),
        "steps": steps,
        "expected_result": form.get("expected_result", "").strip(),
        "status": form.get("status", "draft"),
        "notes": form.get("notes", "").strip(),
    }


def _parse_external_resource(form):
    return {
        "name": form.get("name", "").strip(),
        "type": form.get("resource_type", "api"),
        "url": form.get("url", "").strip(),
        "description": form.get("description", "").strip(),
        "authentication": form.get("authentication", "none"),
        "notes": form.get("notes", "").strip(),
    }


def _parse_research(form):
    return {
        "title": form.get("title", "").strip(),
        "body": form.get("body", "").strip(),
        "tags": form.get("tags", "").strip(),
    }


PARSERS = {
    "user_story": _parse_user_story,
    "requirement": _parse_requirement,
    "project_plan": _parse_project_plan,
    "test_plan": _parse_test_plan,
    "adr": _parse_adr,
    "tech_stack": _parse_tech_stack,
    "nfr": _parse_nfr,
    "risk_register": _parse_risk_register,
    "domain_model": _parse_domain_model,
    "acceptance_test": _parse_acceptance_test,
    "external_resource": _parse_external_resource,
    "research": _parse_research,
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
    elif doc_type == "adr":
        if not data.get("title") or not data.get("context") or not data.get("decision"):
            return "Title, context, and decision are required."
    elif doc_type == "nfr":
        if not data.get("title") or not data.get("description"):
            return "Title and description are required."
    elif doc_type == "domain_model":
        if not data.get("bounded_context_name"):
            return "Bounded context name is required."
    elif doc_type == "acceptance_test":
        if not data.get("title") or not data.get("expected_result"):
            return "Title and expected result are required."
    elif doc_type == "external_resource":
        if not data.get("name"):
            return "Name is required."
    elif doc_type == "research":
        if not data.get("title"):
            return "Title is required."
    return None


# --- Routes ---

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

    extra = {}
    if doc.type == "acceptance_test":
        links = TraceabilityService.get_links_for_acceptance_test(doc.id)
        linked_docs = []
        for link in links:
            if link.requirement_id:
                req = DocumentService.get(link.requirement_id)
                if req:
                    linked_docs.append({"link_id": link.id, "doc": req, "source_type": "requirement"})
            if link.user_story_id:
                us = DocumentService.get(link.user_story_id)
                if us:
                    linked_docs.append({"link_id": link.id, "doc": us, "source_type": "user_story"})
        requirements = DocumentService.get_all_for_project(project_id, doc_type="requirement")
        user_stories = DocumentService.get_all_for_project(project_id, doc_type="user_story")
        extra = {
            "linked_docs": linked_docs,
            "requirements": requirements,
            "user_stories": user_stories,
        }
    elif doc.type == "requirement":
        links = TraceabilityService.get_links_for_requirement(doc.id)
        linked_tests = []
        for link in links:
            at = DocumentService.get(link.acceptance_test_id)
            if at:
                linked_tests.append({"link_id": link.id, "doc": at})
        extra = {"linked_tests": linked_tests}
    elif doc.type == "user_story":
        links = TraceabilityService.get_links_for_user_story(doc.id)
        linked_tests = []
        for link in links:
            at = DocumentService.get(link.acceptance_test_id)
            if at:
                linked_tests.append({"link_id": link.id, "doc": at})
        extra = {"linked_tests": linked_tests}

    return render_template(
        f"documents/{doc.type}_detail.html",
        project=project, document=doc, data=doc.data, type_label=DOCUMENT_TYPES[doc.type],
        **extra,
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


# --- Traceability routes ---

@documents_bp.route("/projects/<project_id>/traceability", methods=["POST"])
def add_traceability_link(project_id):
    acceptance_test_id = request.form.get("acceptance_test_id", "").strip()
    requirement_id = request.form.get("requirement_id", "").strip() or None
    user_story_id = request.form.get("user_story_id", "").strip() or None

    if not acceptance_test_id or (not requirement_id and not user_story_id):
        flash("Select at least one requirement or user story to link.", "error")
        return redirect(url_for("documents.index", project_id=project_id))

    TraceabilityService.create_link(
        acceptance_test_id=acceptance_test_id,
        requirement_id=requirement_id,
        user_story_id=user_story_id,
    )
    flash("Traceability link added.", "success")
    return redirect(url_for("documents.detail", project_id=project_id, id=acceptance_test_id))


@documents_bp.route("/projects/<project_id>/traceability/<link_id>/delete", methods=["POST"])
def delete_traceability_link(project_id, link_id):
    link = TraceabilityService.get_link(link_id)
    at_id = None
    if link:
        at_id = link.acceptance_test_id
        TraceabilityService.delete_link(link)
        flash("Traceability link removed.", "success")
    if at_id:
        return redirect(url_for("documents.detail", project_id=project_id, id=at_id))
    return redirect(url_for("documents.index", project_id=project_id))
