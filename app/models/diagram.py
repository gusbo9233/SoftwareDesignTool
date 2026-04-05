import uuid
from datetime import datetime, timezone

from app import db


class Diagram(db.Model):
    __tablename__ = "diagrams"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = db.Column(db.String(36), db.ForeignKey("projects.id"), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # architecture, uml_class, uml_sequence, uml_component, er, workflow
    name = db.Column(db.String(200), nullable=False)
    data = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return f"<Diagram {self.name} ({self.type})>"
