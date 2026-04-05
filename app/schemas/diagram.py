from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class DiagramCreate(BaseModel):
    project_id: str
    type: str = Field(
        pattern=r"^(architecture|uml_class|uml_sequence|uml_component|er|workflow)$"
    )
    name: str = Field(min_length=1, max_length=200)
    data: dict[str, Any] = {"nodes": [], "edges": []}


class DiagramUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    data: dict[str, Any] | None = None


class DiagramResponse(BaseModel):
    id: str
    project_id: str
    type: str
    name: str
    data: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
