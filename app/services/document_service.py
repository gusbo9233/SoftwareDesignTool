from app import db
from app.models.document import Document


class DocumentService:
    @staticmethod
    def get_all_for_project(project_id, doc_type=None):
        query = Document.query.filter_by(project_id=project_id)
        if doc_type:
            query = query.filter_by(type=doc_type)
        return query.order_by(Document.updated_at.desc()).all()

    @staticmethod
    def get(id):
        return db.session.get(Document, id)

    @staticmethod
    def create(project_id, doc_type, data=None):
        doc = Document(project_id=project_id, type=doc_type, data=data or {})
        db.session.add(doc)
        db.session.commit()
        return doc

    @staticmethod
    def update(doc, data=None, doc_type=None):
        if data is not None:
            doc.data = data
        if doc_type is not None:
            doc.type = doc_type
        db.session.commit()
        return doc

    @staticmethod
    def delete(doc):
        db.session.delete(doc)
        db.session.commit()
