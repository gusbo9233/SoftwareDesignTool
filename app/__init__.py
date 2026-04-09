from flask import Flask

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

    from app.routes.projects import projects_bp
    from app.routes.documents import documents_bp
    from app.routes.diagrams import diagrams_bp
    from app.routes.api_endpoints import api_endpoints_bp
    from app.routes.github import github_bp
    from app.routes.screens import screens_bp
    from app.routes.modules import modules_bp
    app.register_blueprint(projects_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(diagrams_bp)
    app.register_blueprint(api_endpoints_bp)
    app.register_blueprint(github_bp)
    app.register_blueprint(screens_bp)
    app.register_blueprint(modules_bp)

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
            return {"sidebar_modules": ModuleService.get_tree_for_project(project_id)}
        except Exception:
            return {"sidebar_modules": []}

    return app
