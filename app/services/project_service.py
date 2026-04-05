from app import db
from app.models.project import Project


class ProjectService:
    @staticmethod
    def get_all():
        return Project.query.order_by(Project.updated_at.desc()).all()

    @staticmethod
    def get(id):
        return db.session.get(Project, id)

    @staticmethod
    def create(name, description=""):
        project = Project(name=name, description=description)
        db.session.add(project)
        db.session.commit()
        return project

    @staticmethod
    def update(project, name=None, description=None):
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        db.session.commit()
        return project

    @staticmethod
    def delete(project):
        db.session.delete(project)
        db.session.commit()
