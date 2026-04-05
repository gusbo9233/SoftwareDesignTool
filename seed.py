"""Seed the database with sample data for development."""

from app import create_app, db
from app.models import Project, Document, Diagram, APIEndpoint

app = create_app()

SEED_DATA = [
    {
        "name": "Task Manager API",
        "description": "A REST API for managing tasks and projects, with user authentication and role-based access.",
        "documents": [
            {
                "type": "user_story",
                "data": {
                    "user_type": "team lead",
                    "action": "assign tasks to team members",
                    "benefit": "track workload distribution",
                    "priority": "high",
                    "status": "approved",
                    "acceptance_criteria": [
                        "Can select a team member from a dropdown",
                        "Assigned user receives a notification",
                        "Task appears in assignee's dashboard",
                    ],
                },
            },
            {
                "type": "requirement",
                "data": {
                    "title": "Authentication",
                    "description": "The system must support JWT-based authentication for all API endpoints.",
                    "type": "functional",
                    "category": "Security",
                    "priority": "must",
                    "status": "approved",
                    "rationale": "API must be secured for multi-tenant usage.",
                },
            },
        ],
        "diagrams": [
            {
                "type": "architecture",
                "name": "System Overview",
                "data": {
                    "nodes": [
                        {"id": "1", "type": "component", "position": {"x": 100, "y": 100}, "data": {"label": "API Gateway"}},
                        {"id": "2", "type": "component", "position": {"x": 300, "y": 100}, "data": {"label": "Auth Service"}},
                        {"id": "3", "type": "component", "position": {"x": 300, "y": 250}, "data": {"label": "Task Service"}},
                        {"id": "4", "type": "component", "position": {"x": 500, "y": 175}, "data": {"label": "PostgreSQL"}},
                    ],
                    "edges": [
                        {"id": "e1-2", "source": "1", "target": "2", "label": "JWT"},
                        {"id": "e1-3", "source": "1", "target": "3", "label": "REST"},
                        {"id": "e2-4", "source": "2", "target": "4"},
                        {"id": "e3-4", "source": "3", "target": "4"},
                    ],
                },
            },
        ],
        "api_endpoints": [
            {
                "path": "/api/tasks",
                "method": "GET",
                "description": "List all tasks for the authenticated user.",
                "request_schema": {},
                "response_schema": {
                    "type": "array",
                    "items": {"type": "object", "properties": {"id": {"type": "string"}, "title": {"type": "string"}, "status": {"type": "string"}}},
                },
            },
            {
                "path": "/api/tasks",
                "method": "POST",
                "description": "Create a new task.",
                "request_schema": {
                    "type": "object",
                    "properties": {"title": {"type": "string"}, "description": {"type": "string"}, "assignee_id": {"type": "string"}},
                    "required": ["title"],
                },
                "response_schema": {"type": "object", "properties": {"id": {"type": "string"}, "title": {"type": "string"}}},
            },
        ],
    },
    {
        "name": "E-Commerce Platform",
        "description": "Online marketplace with product catalog, shopping cart, and checkout flow.",
    },
    {
        "name": "Weather Dashboard",
        "description": "A dashboard that displays weather data from multiple sources with historical charts.",
    },
]


def seed():
    with app.app_context():
        # Clear existing data
        db.session.query(APIEndpoint).delete()
        db.session.query(Diagram).delete()
        db.session.query(Document).delete()
        db.session.query(Project).delete()
        db.session.commit()

        for project_data in SEED_DATA:
            project = Project(
                name=project_data["name"],
                description=project_data.get("description", ""),
            )
            db.session.add(project)
            db.session.flush()

            for doc in project_data.get("documents", []):
                db.session.add(Document(project_id=project.id, type=doc["type"], data=doc["data"]))

            for diag in project_data.get("diagrams", []):
                db.session.add(Diagram(project_id=project.id, type=diag["type"], name=diag["name"], data=diag["data"]))

            for ep in project_data.get("api_endpoints", []):
                db.session.add(APIEndpoint(project_id=project.id, **ep))

        db.session.commit()
        print(f"Seeded {len(SEED_DATA)} projects.")


if __name__ == "__main__":
    seed()
