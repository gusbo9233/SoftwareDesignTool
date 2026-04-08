from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.services.project_service import ProjectService
from app.services.document_service import DocumentService
from app.services.project_template_service import ProjectTemplateService
from app.services.traceability_service import TraceabilityService
from app.services.test_result_service import TestResultService, generate_test_uid
from app.services.git_connection_service import GitConnectionService
from app.services.github_service import GitHubService, GitHubAPIError

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
    "folder_structure": "Folder Structure",
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
    "folder_structure": "documents/folder_structure_form.html",
}

CREATE_DOCUMENT_TYPES = {
    key: value for key, value in DOCUMENT_TYPES.items()
    if key != "folder_structure"
}


def _apply_test_id_fields(form, data):
    """Inject test_name / test_uid into any document's data dict."""
    test_name = form.get("test_name", "").strip()
    if test_name:
        data["test_name"] = test_name
        data["test_uid"] = generate_test_uid(test_name)
    else:
        data.pop("test_name", None)
        data.pop("test_uid", None)


def _normalize_user_story_data(data):
    normalized = dict(data or {})
    stories = []

    for story in normalized.get("stories", []):
        normalized_story = {
            "user_type": (story.get("user_type") or "").strip(),
            "action": (story.get("action") or "").strip(),
            "benefit": (story.get("benefit") or "").strip(),
            "priority": (story.get("priority") or "medium").strip() or "medium",
            "status": (story.get("status") or "draft").strip() or "draft",
            "acceptance_criteria": [
                criterion.strip()
                for criterion in (story.get("acceptance_criteria") or [])
                if isinstance(criterion, str) and criterion.strip()
            ],
        }
        if any(normalized_story[field] for field in ("user_type", "action", "benefit")):
            stories.append(normalized_story)

    if not stories:
        legacy_story = {
            "user_type": (normalized.get("user_type") or "").strip(),
            "action": (normalized.get("action") or "").strip(),
            "benefit": (normalized.get("benefit") or "").strip(),
            "priority": (normalized.get("priority") or "medium").strip() or "medium",
            "status": (normalized.get("status") or "draft").strip() or "draft",
            "acceptance_criteria": [
                criterion.strip()
                for criterion in (normalized.get("acceptance_criteria") or [])
                if isinstance(criterion, str) and criterion.strip()
            ],
        }
        if legacy_story["user_type"] or legacy_story["action"] or legacy_story["benefit"]:
            stories.append(legacy_story)

    normalized["stories"] = stories
    if stories:
        primary_story = stories[0]
        normalized["user_type"] = primary_story["user_type"]
        normalized["action"] = primary_story["action"]
        normalized["benefit"] = primary_story["benefit"]
        normalized["priority"] = primary_story["priority"]
        normalized["status"] = primary_story["status"]
        normalized["acceptance_criteria"] = primary_story["acceptance_criteria"]
    else:
        normalized["priority"] = "medium"
        normalized["status"] = "draft"
        normalized["acceptance_criteria"] = []
    return normalized


def _merge_user_story_documents(primary_doc, docs_to_merge):
    merged_data = _normalize_user_story_data(primary_doc.data)
    merged_stories = list(merged_data.get("stories", []))

    for doc in docs_to_merge:
        normalized = _normalize_user_story_data(doc.data)
        merged_stories.extend(normalized.get("stories", []))
        TraceabilityService.reassign_user_story_links(doc.id, primary_doc.id)
        DocumentService.delete(doc)

    merged_data["stories"] = merged_stories
    merged_data = _normalize_user_story_data(merged_data)
    DocumentService.update(primary_doc, data=merged_data)
    return primary_doc


def _get_or_consolidate_user_story_document(project_id):
    user_story_docs = DocumentService.get_all_for_project(project_id, doc_type="user_story")
    if not user_story_docs:
        return None

    primary_doc = user_story_docs[0]
    if len(user_story_docs) > 1:
        primary_doc = _merge_user_story_documents(primary_doc, user_story_docs[1:])
    else:
        normalized = _normalize_user_story_data(primary_doc.data)
        if normalized != (primary_doc.data or {}):
            DocumentService.update(primary_doc, data=normalized)
    return primary_doc


def _append_story_to_document(doc, story):
    data = _normalize_user_story_data(doc.data)
    stories = list(data.get("stories", []))
    stories.append({
        "user_type": (story.get("user_type") or "").strip(),
        "action": (story.get("action") or "").strip(),
        "benefit": (story.get("benefit") or "").strip(),
        "priority": "medium",
        "status": "draft",
        "acceptance_criteria": [
            criterion.strip()
            for criterion in (story.get("acceptance_criteria") or [])
            if isinstance(criterion, str) and criterion.strip()
        ],
    })
    data["stories"] = stories
    return DocumentService.update(doc, data=_normalize_user_story_data(data))


def _get_project_or_redirect(project_id):
    project = ProjectService.get(project_id)
    if not project:
        flash("Project not found.", "error")
        return None
    existing_documents = DocumentService.get_all_for_project(project.id)
    ProjectTemplateService.ensure_project_template(project, documents=existing_documents)
    return project


# --- Parsers ---

def _parse_user_story(form):
    user_types = form.getlist("story_user_type")
    actions = form.getlist("story_action")
    benefits = form.getlist("story_benefit")
    priorities = form.getlist("story_priority")
    statuses = form.getlist("story_status")
    criteria_groups = form.getlist("story_acceptance_criteria")

    if not any((user_types, actions, benefits, priorities, statuses, criteria_groups)):
        return _normalize_user_story_data({
            "user_type": form.get("user_type", "").strip(),
            "action": form.get("action", "").strip(),
            "benefit": form.get("benefit", "").strip(),
            "priority": form.get("priority", "medium"),
            "status": form.get("status", "draft"),
            "acceptance_criteria": [c.strip() for c in form.getlist("acceptance_criteria") if c.strip()],
        })

    row_count = max(
        len(user_types),
        len(actions),
        len(benefits),
        len(priorities),
        len(statuses),
        len(criteria_groups),
    )
    stories = []
    for i in range(row_count):
        story = {
            "user_type": user_types[i].strip() if i < len(user_types) else "",
            "action": actions[i].strip() if i < len(actions) else "",
            "benefit": benefits[i].strip() if i < len(benefits) else "",
            "priority": priorities[i].strip() if i < len(priorities) and priorities[i].strip() else "medium",
            "status": statuses[i].strip() if i < len(statuses) and statuses[i].strip() else "draft",
            "acceptance_criteria": [],
        }
        criteria_blob = criteria_groups[i] if i < len(criteria_groups) else ""
        story["acceptance_criteria"] = [
            criterion.strip()
            for criterion in criteria_blob.splitlines()
            if criterion.strip()
        ]
        if any(story[field] for field in ("user_type", "action", "benefit")):
            stories.append(story)

    return {"stories": stories}


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
    tags = []
    for tag in form.getlist("tags"):
        normalized = tag.strip().lower()
        if normalized and normalized not in tags:
            tags.append(normalized)
    for tag in form.get("custom_tags", "").split(","):
        normalized = tag.strip().lower()
        if normalized and normalized not in tags:
            tags.append(normalized)

    case_descs = form.getlist("case_description")
    case_test_names = form.getlist("case_test_name")
    case_steps = form.getlist("case_steps")
    case_expected = form.getlist("case_expected")
    case_statuses = form.getlist("case_status")
    test_cases = []
    row_count = max(len(case_descs), len(case_test_names), len(case_steps), len(case_expected), len(case_statuses))
    for i in range(row_count):
        desc = case_descs[i].strip() if i < len(case_descs) else ""
        test_name = case_test_names[i].strip() if i < len(case_test_names) else ""
        steps = case_steps[i].strip() if i < len(case_steps) else ""
        expected = case_expected[i].strip() if i < len(case_expected) else ""
        status = case_statuses[i].strip() if i < len(case_statuses) else "not_run"
        if any([desc, test_name, steps, expected]):
            test_cases.append({
                "description": desc,
                "test_name": test_name,
                "test_uid": generate_test_uid(test_name) if test_name else "",
                "steps": steps,
                "expected_result": expected,
                "status": status,
            })

    return {
        "test_scope": form.get("test_scope", "").strip(),
        "tags": tags,
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


def _parse_folder_structure(form):
    paths = form.getlist("item_path")
    kinds = form.getlist("item_kind")
    purposes = form.getlist("item_purpose")
    fixed_flags = form.getlist("item_is_fixed")
    items = []
    for i in range(len(paths)):
        path = paths[i].strip() if i < len(paths) else ""
        if path:
            items.append({
                "path": path,
                "kind": kinds[i].strip() if i < len(kinds) and kinds[i].strip() else "folder",
                "purpose": purposes[i].strip() if i < len(purposes) else "",
                "is_fixed": (fixed_flags[i].strip().lower() == "true") if i < len(fixed_flags) else False,
            })

    return {
        "title": form.get("title", "").strip(),
        "root_name": form.get("root_name", "").strip(),
        "notes": form.get("notes", "").strip(),
        "items": items,
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
    "folder_structure": _parse_folder_structure,
}


def _validate_document_data(doc_type, data):
    """Return error message if validation fails, else None."""
    if doc_type == "user_story":
        stories = _normalize_user_story_data(data).get("stories", [])
        if not stories:
            return "At least one user story is required."
        for story in stories:
            if not story.get("user_type") or not story.get("action") or not story.get("benefit"):
                return "Each user story needs a user type, action, and benefit."
    elif doc_type == "requirement":
        if not data.get("title") or not data.get("description"):
            return "Title and description are required."
    elif doc_type == "project_plan":
        if not data.get("project_name"):
            return "Project name is required."
    elif doc_type == "test_plan":
        if not data.get("test_scope"):
            return "Test scope is required."
        for tc in data.get("test_cases", []):
            if not tc.get("test_name"):
                return "Each test case requires a test name."
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
    elif doc_type == "folder_structure":
        if not data.get("title"):
            return "Title is required."
    return None


def _document_template_context(project, data=None):
    existing_docs = DocumentService.get_all_for_project(project.id)
    temp_docs = list(existing_docs)
    if data:
        temp_docs.append(type("DocLike", (), {"data": data})())
    project_template = ProjectTemplateService.resolve_template(project=project, documents=temp_docs)
    fixed_items = []
    if project_template["key"] in {"aspnetcore_clean_architecture", "mvc"}:
        fixed_items = ProjectTemplateService.get_fixed_folder_structure(project.name, project_template["key"])
    custom_items = []
    for item in (data or {}).get("items", []):
        if not item.get("is_fixed"):
            custom_items.append(item)
    return {
        "project_template": project_template,
        "fixed_structure_items": fixed_items,
        "custom_structure_items": custom_items or [{}],
    }


def _parse_document_form(doc_type, form, project):
    data = PARSERS[doc_type](form)
    if doc_type == "user_story":
        data = _normalize_user_story_data(data)
    if doc_type == "folder_structure":
        existing_docs = DocumentService.get_all_for_project(project.id)
        template_key = ProjectTemplateService.resolve_template_key(project=project, documents=existing_docs)
        data["items"] = ProjectTemplateService.merge_folder_structure_items(
            project_template_key=template_key,
            project_name=project.name,
            custom_items=[item for item in data.get("items", []) if not item.get("is_fixed")],
        )
    return data


def _generate_folder_structure_child_path(existing_items, parent_path, item_kind):
    normalized_parent = (parent_path or "").strip()
    if normalized_parent and not normalized_parent.endswith("/"):
        normalized_parent = f"{normalized_parent}/"

    base_name = "NewFolder" if item_kind == "folder" else "NewFile"
    extension = "/" if item_kind == "folder" else ""
    counter = 1
    existing_paths = {item.get("path", "") for item in existing_items}

    while True:
        suffix = "" if counter == 1 else str(counter)
        candidate = f"{normalized_parent}{base_name}{suffix}{extension}"
        if candidate not in existing_paths:
            return candidate
        counter += 1


def _folder_structure_delete_custom_items(items, target_path):
    normalized_target = (target_path or "").strip()
    if not normalized_target:
        return items

    normalized_folder_prefix = normalized_target if normalized_target.endswith("/") else f"{normalized_target}/"
    remaining = []
    for item in items:
        path = item.get("path", "")
        if item.get("is_fixed"):
            remaining.append(item)
            continue
        if path == normalized_target or path.startswith(normalized_folder_prefix):
            continue
        remaining.append(item)
    return remaining


def _github_tree_to_folder_structure_items(tree_response):
    items = []
    seen = set()
    for entry in (tree_response or {}).get("tree", []):
        path = (entry.get("path") or "").strip()
        entry_type = entry.get("type")
        if not path or entry_type not in {"tree", "blob"}:
            continue
        normalized = f"{path}/" if entry_type == "tree" else path
        if normalized in seen:
            continue
        seen.add(normalized)
        items.append({
            "path": normalized,
            "kind": "folder" if entry_type == "tree" else "file",
            "purpose": "",
            "is_fixed": False,
        })
    return items


def _truncate_text(value, max_chars=50000):
    if not isinstance(value, str):
        return value
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars]}\n\n... truncated ..."


# --- Routes ---

@documents_bp.route("/projects/<project_id>/documents")
def index(project_id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))
    documents = DocumentService.get_all_for_project(project_id)
    user_story_doc = _get_or_consolidate_user_story_document(project_id)
    non_user_story_docs = [doc for doc in documents if doc.type != "user_story"]
    if user_story_doc:
        documents = [user_story_doc] + non_user_story_docs
    else:
        documents = non_user_story_docs
    return render_template(
        "documents/index.html",
        project=project,
        documents=documents,
        type_labels=DOCUMENT_TYPES,
        create_type_labels=CREATE_DOCUMENT_TYPES,
    )


@documents_bp.route("/projects/<project_id>/documents/new/<doc_type>", methods=["GET", "POST"])
def create(project_id, doc_type):
    if doc_type not in DOCUMENT_TYPES:
        flash("Invalid document type.", "error")
        return redirect(url_for("documents.index", project_id=project_id))

    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))

    existing_user_story_doc = None
    if doc_type == "user_story":
        existing_user_story_doc = _get_or_consolidate_user_story_document(project_id)
        if request.method == "GET":
            if existing_user_story_doc:
                return redirect(url_for("documents.detail", project_id=project_id, id=existing_user_story_doc.id))
            doc = DocumentService.create(
                project_id=project_id,
                doc_type="user_story",
                data=_normalize_user_story_data({}),
            )
            return redirect(url_for("documents.detail", project_id=project_id, id=doc.id))

    if request.method == "POST":
        data = _parse_document_form(doc_type, request.form, project)
        _apply_test_id_fields(request.form, data)
        error = _validate_document_data(doc_type, data)
        if error:
            flash(error, "error")
            return render_template(
                TEMPLATE_MAP[doc_type],
                project=project,
                document=None,
                data=_normalize_user_story_data(data) if doc_type == "user_story" else data,
                **_document_template_context(project, data),
            )
        if doc_type == "user_story" and existing_user_story_doc:
            existing_data = _normalize_user_story_data(existing_user_story_doc.data)
            merged_data = dict(existing_data)
            merged_data["stories"] = existing_data.get("stories", []) + data.get("stories", [])
            if data.get("test_name"):
                merged_data["test_name"] = data["test_name"]
                merged_data["test_uid"] = data.get("test_uid", "")
            doc = DocumentService.update(existing_user_story_doc, data=_normalize_user_story_data(merged_data))
        else:
            doc = DocumentService.create(project_id=project_id, doc_type=doc_type, data=data)
        flash(f"{DOCUMENT_TYPES[doc_type]} created.", "success")
        return redirect(url_for("documents.detail", project_id=project_id, id=doc.id))

    return render_template(
        TEMPLATE_MAP[doc_type],
        project=project,
        document=None,
        data=_normalize_user_story_data({}) if doc_type == "user_story" else {},
        **_document_template_context(project),
    )


@documents_bp.route("/projects/<project_id>/documents/<id>")
def detail(project_id, id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))
    doc = DocumentService.get(id)
    if not doc or doc.project_id != project_id:
        flash("Document not found.", "error")
        return redirect(url_for("documents.index", project_id=project_id))
    if doc.type == "user_story":
        canonical_doc = _get_or_consolidate_user_story_document(project_id)
        if canonical_doc and canonical_doc.id != doc.id:
            return redirect(url_for("documents.detail", project_id=project_id, id=canonical_doc.id))
        doc = canonical_doc or doc

    extra = {}
    current_view = request.args.get("view", "designed").strip().lower()
    if current_view not in {"designed", "github"}:
        current_view = "designed"
    git_connection = GitConnectionService.get_for_project(project_id)
    github_items = []
    github_error = None
    github_file = None
    github_selected_path = request.args.get("path", "").strip()
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
    elif doc.type == "test_plan":
        case_names = [tc.get("test_name", "") for tc in (doc.data or {}).get("test_cases", [])]
        extra = {"case_results": TestResultService.get_latest_results_for_test_names(project_id, case_names)}
    elif doc.type == "folder_structure":
        if current_view == "github":
            if not git_connection:
                github_error = "Connect a GitHub repository to view the repository structure."
            else:
                gh = GitHubService(
                    token=git_connection.auth_token_encrypted,
                    repo_owner=git_connection.repo_owner,
                    repo_name=git_connection.repo_name,
                )
                try:
                    tree = gh.get_tree(ref=git_connection.default_branch, recursive=True)
                    github_items = _github_tree_to_folder_structure_items(tree)
                    if github_selected_path:
                        selected_item = next(
                            (
                                item for item in github_items
                                if item.get("path") == github_selected_path and item.get("kind") == "file"
                            ),
                            None,
                        )
                        if selected_item:
                            github_file = gh.get_file_content(
                                path=github_selected_path,
                                ref=git_connection.default_branch,
                            )
                            github_file["content"] = _truncate_text(github_file.get("content", ""))
                        else:
                            github_error = "Selected file was not found in the repository tree."
                except GitHubAPIError as e:
                    github_error = f"Failed to fetch repository tree: {e.message}"

    return render_template(
        f"documents/{doc.type}_detail.html",
        project=project,
        document=doc,
        data=_normalize_user_story_data(doc.data) if doc.type == "user_story" else doc.data,
        type_label=DOCUMENT_TYPES[doc.type],
        **_document_template_context(project, doc.data),
        git_connection=git_connection,
        current_view=current_view,
        github_items=github_items,
        github_error=github_error,
        github_file=github_file,
        github_selected_path=github_selected_path,
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
    if doc.type == "user_story":
        canonical_doc = _get_or_consolidate_user_story_document(project_id)
        if canonical_doc and canonical_doc.id != doc.id:
            return redirect(url_for("documents.edit", project_id=project_id, id=canonical_doc.id))
        doc = canonical_doc or doc

    if request.method == "POST":
        data = _parse_document_form(doc.type, request.form, project)
        _apply_test_id_fields(request.form, data)
        error = _validate_document_data(doc.type, data)
        if error:
            flash(error, "error")
            return render_template(
                TEMPLATE_MAP[doc.type],
                project=project,
                document=doc,
                data=_normalize_user_story_data(data) if doc.type == "user_story" else data,
                **_document_template_context(project, data),
            )
        DocumentService.update(doc, data=data)
        flash(f"{DOCUMENT_TYPES[doc.type]} updated.", "success")
        return redirect(url_for("documents.detail", project_id=project_id, id=doc.id))

    return render_template(
        TEMPLATE_MAP[doc.type],
        project=project,
        document=doc,
        data=_normalize_user_story_data(doc.data) if doc.type == "user_story" else doc.data,
        **_document_template_context(project, doc.data),
    )


@documents_bp.route("/projects/<project_id>/documents/<id>/user-stories/add", methods=["POST"])
def add_user_story(project_id, id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))

    doc = DocumentService.get(id)
    if not doc or doc.project_id != project_id or doc.type != "user_story":
        flash("User story document not found.", "error")
        return redirect(url_for("documents.index", project_id=project_id))

    story = {
        "user_type": request.form.get("user_type", "").strip(),
        "action": request.form.get("action", "").strip(),
        "benefit": request.form.get("benefit", "").strip(),
        "acceptance_criteria": [
            criterion.strip()
            for criterion in request.form.get("acceptance_criteria", "").splitlines()
            if criterion.strip()
        ],
    }
    if not story["user_type"] or not story["action"] or not story["benefit"]:
        flash("User type, action, and benefit are required.", "error")
        return redirect(url_for("documents.detail", project_id=project_id, id=id))

    _append_story_to_document(doc, story)
    flash("User story added.", "success")
    return redirect(url_for("documents.detail", project_id=project_id, id=id))


@documents_bp.route("/projects/<project_id>/documents/<id>/delete", methods=["POST"])
def delete(project_id, id):
    doc = DocumentService.get(id)
    if doc and doc.project_id == project_id:
        DocumentService.delete(doc)
        flash("Document deleted.", "success")
    return redirect(url_for("documents.index", project_id=project_id))


@documents_bp.route("/projects/<project_id>/documents/<id>/folder-structure/add", methods=["POST"])
def add_folder_structure_item(project_id, id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))

    doc = DocumentService.get(id)
    if not doc or doc.project_id != project_id or doc.type != "folder_structure":
        flash("Folder structure not found.", "error")
        return redirect(url_for("documents.index", project_id=project_id))

    item_kind = request.form.get("item_kind", "folder").strip()
    if item_kind not in {"folder", "file"}:
        item_kind = "folder"
    parent_path = request.form.get("parent_path", "").strip()

    data = dict(doc.data or {})
    existing_items = list(data.get("items", []))
    fixed_items = [item for item in existing_items if item.get("is_fixed")]
    custom_items = [item for item in existing_items if not item.get("is_fixed")]

    custom_items.append({
        "path": _generate_folder_structure_child_path(existing_items, parent_path, item_kind),
        "kind": item_kind,
        "purpose": "",
        "is_fixed": False,
    })

    template_key = ProjectTemplateService.resolve_template_key(project=project, documents=[doc])
    data["items"] = ProjectTemplateService.merge_folder_structure_items(
        project_template_key=template_key,
        project_name=project.name,
        custom_items=custom_items,
    )
    if fixed_items and not any(item.get("is_fixed") for item in data["items"]):
        data["items"] = fixed_items + custom_items
    DocumentService.update(doc, data=data)
    flash(f"{'Folder' if item_kind == 'folder' else 'File'} added.", "success")
    return redirect(url_for("documents.detail", project_id=project_id, id=doc.id))


@documents_bp.route("/projects/<project_id>/documents/<id>/folder-structure/delete-item", methods=["POST"])
def delete_folder_structure_item(project_id, id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))

    doc = DocumentService.get(id)
    if not doc or doc.project_id != project_id or doc.type != "folder_structure":
        flash("Folder structure not found.", "error")
        return redirect(url_for("documents.index", project_id=project_id))

    target_path = request.form.get("target_path", "").strip()
    if not target_path:
        flash("No file or folder selected.", "error")
        return redirect(url_for("documents.detail", project_id=project_id, id=doc.id))

    data = dict(doc.data or {})
    existing_items = list(data.get("items", []))
    target = next((item for item in existing_items if item.get("path") == target_path), None)
    if not target:
        flash("Item not found.", "error")
        return redirect(url_for("documents.detail", project_id=project_id, id=doc.id))
    if target.get("is_fixed"):
        flash("Fixed template items cannot be deleted.", "error")
        return redirect(url_for("documents.detail", project_id=project_id, id=doc.id))

    data["items"] = _folder_structure_delete_custom_items(existing_items, target_path)
    DocumentService.update(doc, data=data)
    flash("Item deleted.", "success")
    return redirect(url_for("documents.detail", project_id=project_id, id=doc.id))


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
