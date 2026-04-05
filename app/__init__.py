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
    app.register_blueprint(projects_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(diagrams_bp)
    app.register_blueprint(api_endpoints_bp)

    return app
