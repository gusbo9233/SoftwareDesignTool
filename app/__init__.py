from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()


def create_app(config_name="default"):
    app = Flask(__name__)

    from app.config import config
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)

    from app.routes.projects import projects_bp
    from app.routes.documents import documents_bp
    from app.routes.diagrams import diagrams_bp
    from app.routes.api_endpoints import api_endpoints_bp
    app.register_blueprint(projects_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(diagrams_bp)
    app.register_blueprint(api_endpoints_bp)

    return app
