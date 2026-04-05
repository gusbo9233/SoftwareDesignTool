from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify

from app.services.project_service import ProjectService
from app.services.api_endpoint_service import APIEndpointService

api_endpoints_bp = Blueprint("api_endpoints", __name__)

HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH"]

PARAM_LOCATIONS = ["path", "query", "header"]


def _get_project_or_redirect(project_id):
    project = ProjectService.get(project_id)
    if not project:
        flash("Project not found.", "error")
        return None
    return project


def _parse_parameters(form):
    names = form.getlist("param_name")
    locations = form.getlist("param_location")
    types = form.getlist("param_type")
    requireds = form.getlist("param_required")
    descriptions = form.getlist("param_description")
    params = []
    for i in range(len(names)):
        name = names[i].strip() if i < len(names) else ""
        if name:
            params.append({
                "name": name,
                "location": locations[i] if i < len(locations) else "query",
                "type": types[i] if i < len(types) else "string",
                "required": str(i) in requireds,
                "description": descriptions[i].strip() if i < len(descriptions) else "",
            })
    return params


def _parse_status_codes(form):
    codes = form.getlist("status_code")
    descs = form.getlist("status_description")
    result = []
    for i in range(len(codes)):
        code = codes[i].strip() if i < len(codes) else ""
        if code:
            result.append({
                "code": code,
                "description": descs[i].strip() if i < len(descs) else "",
            })
    return result


def _parse_endpoint_form(form):
    parameters = _parse_parameters(form)
    status_codes = _parse_status_codes(form)
    return {
        "path": form.get("path", "").strip(),
        "method": form.get("method", "GET"),
        "description": form.get("description", "").strip(),
        "parameters": parameters,
        "request_body": form.get("request_body", "").strip(),
        "response_body": form.get("response_body", "").strip(),
        "status_codes": status_codes,
    }


# --- Page routes ---

@api_endpoints_bp.route("/projects/<project_id>/api-endpoints")
def index(project_id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))
    endpoints = APIEndpointService.get_all_for_project(project_id)
    return render_template(
        "api_endpoints/index.html",
        project=project,
        endpoints=endpoints,
    )


@api_endpoints_bp.route("/projects/<project_id>/api-endpoints/new", methods=["GET", "POST"])
def create(project_id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))

    if request.method == "POST":
        data = _parse_endpoint_form(request.form)
        if not data["path"]:
            flash("Path is required.", "error")
            return render_template(
                "api_endpoints/form.html", project=project, endpoint=None,
                data=data, methods=HTTP_METHODS, param_locations=PARAM_LOCATIONS,
            )
        if data["method"] not in HTTP_METHODS:
            flash("Invalid HTTP method.", "error")
            return render_template(
                "api_endpoints/form.html", project=project, endpoint=None,
                data=data, methods=HTTP_METHODS, param_locations=PARAM_LOCATIONS,
            )

        request_schema = {
            "parameters": data["parameters"],
            "body": data["request_body"],
        }
        response_schema = {
            "body": data["response_body"],
            "status_codes": data["status_codes"],
        }

        ep = APIEndpointService.create(
            project_id=project_id,
            path=data["path"],
            method=data["method"],
            description=data["description"],
            request_schema=request_schema,
            response_schema=response_schema,
        )
        flash("API endpoint created.", "success")
        return redirect(url_for("api_endpoints.detail", project_id=project_id, id=ep.id))

    return render_template(
        "api_endpoints/form.html", project=project, endpoint=None,
        data={}, methods=HTTP_METHODS, param_locations=PARAM_LOCATIONS,
    )


@api_endpoints_bp.route("/projects/<project_id>/api-endpoints/<id>")
def detail(project_id, id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))
    ep = APIEndpointService.get(id)
    if not ep or ep.project_id != project_id:
        flash("API endpoint not found.", "error")
        return redirect(url_for("api_endpoints.index", project_id=project_id))
    return render_template(
        "api_endpoints/detail.html", project=project, endpoint=ep,
    )


@api_endpoints_bp.route("/projects/<project_id>/api-endpoints/<id>/edit", methods=["GET", "POST"])
def edit(project_id, id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))
    ep = APIEndpointService.get(id)
    if not ep or ep.project_id != project_id:
        flash("API endpoint not found.", "error")
        return redirect(url_for("api_endpoints.index", project_id=project_id))

    if request.method == "POST":
        data = _parse_endpoint_form(request.form)
        if not data["path"]:
            flash("Path is required.", "error")
            return render_template(
                "api_endpoints/form.html", project=project, endpoint=ep,
                data=data, methods=HTTP_METHODS, param_locations=PARAM_LOCATIONS,
            )
        if data["method"] not in HTTP_METHODS:
            flash("Invalid HTTP method.", "error")
            return render_template(
                "api_endpoints/form.html", project=project, endpoint=ep,
                data=data, methods=HTTP_METHODS, param_locations=PARAM_LOCATIONS,
            )

        request_schema = {
            "parameters": data["parameters"],
            "body": data["request_body"],
        }
        response_schema = {
            "body": data["response_body"],
            "status_codes": data["status_codes"],
        }

        APIEndpointService.update(
            ep,
            path=data["path"],
            method=data["method"],
            description=data["description"],
            request_schema=request_schema,
            response_schema=response_schema,
        )
        flash("API endpoint updated.", "success")
        return redirect(url_for("api_endpoints.detail", project_id=project_id, id=ep.id))

    # Pre-populate form data from existing endpoint
    data = {
        "path": ep.path,
        "method": ep.method,
        "description": ep.description,
        "parameters": ep.request_schema.get("parameters", []),
        "request_body": ep.request_schema.get("body", ""),
        "response_body": ep.response_schema.get("body", ""),
        "status_codes": ep.response_schema.get("status_codes", []),
    }
    return render_template(
        "api_endpoints/form.html", project=project, endpoint=ep,
        data=data, methods=HTTP_METHODS, param_locations=PARAM_LOCATIONS,
    )


@api_endpoints_bp.route("/projects/<project_id>/api-endpoints/<id>/delete", methods=["POST"])
def delete(project_id, id):
    ep = APIEndpointService.get(id)
    if ep and ep.project_id == project_id:
        APIEndpointService.delete(ep)
        flash("API endpoint deleted.", "success")
    return redirect(url_for("api_endpoints.index", project_id=project_id))
