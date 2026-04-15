from datetime import datetime

from flask import Flask, jsonify, redirect, request, url_for

supabase = None  # initialized in create_app()


def create_app(config_name="default"):
    global supabase
    app = Flask(__name__)

    from app.config import config
    app.config.from_object(config[config_name])

    # Only create a real Supabase client if one hasn't been injected already
    # (tests inject a mock before calling create_app)
    if supabase is None:
        from supabase import create_client
        supabase = create_client(
            app.config["SUPABASE_URL"],
            app.config["SUPABASE_SERVICE_KEY"],
        )

    @app.template_filter("format_datetime")
    def format_datetime(value, fmt="%Y-%m-%d %H:%M"):
        if value is None:
            return ""
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return value[:16].replace("T", " ")
        return value.strftime(fmt)

    from app.routes.projects import projects_bp
    from app.routes.auth import auth_bp
    from app.routes.documents import documents_bp
    from app.routes.diagrams import diagrams_bp
    from app.routes.api_endpoints import api_endpoints_bp
    from app.routes.github import github_bp
    from app.routes.screens import screens_bp
    from app.routes.modules import modules_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(diagrams_bp)
    app.register_blueprint(api_endpoints_bp)
    app.register_blueprint(github_bp)
    app.register_blueprint(screens_bp)
    app.register_blueprint(modules_bp)

    @app.before_request
    def require_login():
        allowed_endpoints = {
            "auth.login",
            "auth.signup",
            "auth.google_login",
            "auth.google_callback",
            "auth.logout",
            "static",
        }
        if request.endpoint in allowed_endpoints or request.endpoint is None:
            return None

        from app.services.auth_service import AuthService

        if AuthService.current_user():
            return None

        if request.path.startswith("/api/"):
            return jsonify({"error": "Authentication required"}), 401

        return redirect(url_for("auth.login", next=request.full_path if request.query_string else request.path))

    @app.context_processor
    def inject_sidebar_modules():
        """Make module tree available in all templates for the sidebar."""
        from flask import request as _req
        view_args = _req.view_args or {}
        project_id = view_args.get("project_id")
        if not project_id:
            return {}
        try:
            from app.services.module_service import ModuleService
            from app.services.auth_service import AuthService
            return {
                "sidebar_modules": ModuleService.get_tree_for_project(project_id),
                "current_user": AuthService.current_user(),
            }
        except Exception:
            from app.services.auth_service import AuthService
            return {"sidebar_modules": [], "current_user": AuthService.current_user()}

    @app.context_processor
    def inject_current_user():
        from app.services.auth_service import AuthService
        return {"current_user": AuthService.current_user()}

    return app
