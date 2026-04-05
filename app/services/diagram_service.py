from app import db
from app.models.diagram import Diagram


class DiagramService:
    @staticmethod
    def get_all_for_project(project_id):
        return (
            Diagram.query.filter_by(project_id=project_id)
            .order_by(Diagram.updated_at.desc())
            .all()
        )

    @staticmethod
    def get(id):
        return db.session.get(Diagram, id)

    @staticmethod
    def create(project_id, diagram_type, name, data=None):
        diagram = Diagram(
            project_id=project_id,
            type=diagram_type,
            name=name,
            data=data or {"nodes": [], "edges": []},
        )
        db.session.add(diagram)
        db.session.commit()
        return diagram

    @staticmethod
    def update(diagram, name=None, data=None):
        if name is not None:
            diagram.name = name
        if data is not None:
            diagram.data = data
        db.session.commit()
        return diagram

    @staticmethod
    def delete(diagram):
        db.session.delete(diagram)
        db.session.commit()
