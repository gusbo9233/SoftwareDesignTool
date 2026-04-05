import uuid
from datetime import datetime, timezone

from app import db


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    documents = db.relationship("Document", backref="project", cascade="all, delete-orphan")
    diagrams = db.relationship("Diagram", backref="project", cascade="all, delete-orphan")
    api_endpoints = db.relationship("APIEndpoint", backref="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project {self.name}>"
