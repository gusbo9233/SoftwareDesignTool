from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class APIEndpointCreate(BaseModel):
    project_id: str
    path: str = Field(min_length=1, max_length=500)
    method: str = Field(pattern=r"^(GET|POST|PUT|DELETE|PATCH)$")
    description: str = ""
    request_schema: dict[str, Any] = {}
    response_schema: dict[str, Any] = {}


class APIEndpointUpdate(BaseModel):
    path: str | None = Field(default=None, min_length=1, max_length=500)
    method: str | None = Field(default=None, pattern=r"^(GET|POST|PUT|DELETE|PATCH)$")
    description: str | None = None
    request_schema: dict[str, Any] | None = None
    response_schema: dict[str, Any] | None = None


class APIEndpointResponse(BaseModel):
    id: str
    project_id: str
    path: str
    method: str
    description: str
    request_schema: dict[str, Any]
    response_schema: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
