import uuid
from datetime import datetime, timezone

from app import db


class RequirementTestLink(db.Model):
    __tablename__ = "requirement_test_links"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    requirement_id = db.Column(db.String(36), db.ForeignKey("documents.id"), nullable=True)
    user_story_id = db.Column(db.String(36), db.ForeignKey("documents.id"), nullable=True)
    acceptance_test_id = db.Column(db.String(36), db.ForeignKey("documents.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<RequirementTestLink {self.id}>"
