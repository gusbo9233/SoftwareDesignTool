import uuid
from datetime import datetime, timezone

from app import db


class APIEndpoint(db.Model):
    __tablename__ = "api_endpoints"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = db.Column(db.String(36), db.ForeignKey("projects.id"), nullable=False)
    path = db.Column(db.String(500), nullable=False)
    method = db.Column(db.String(10), nullable=False)  # GET, POST, PUT, DELETE, PATCH
    description = db.Column(db.Text, default="")
    request_schema = db.Column(db.JSON, default=dict)
    response_schema = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return f"<APIEndpoint {self.method} {self.path}>"
