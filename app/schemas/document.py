from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    project_id: str
    type: str = Field(pattern=r"^(user_story|requirement|project_plan|test_plan)$")
    data: dict[str, Any] = {}


class DocumentUpdate(BaseModel):
    type: str | None = Field(default=None, pattern=r"^(user_story|requirement|project_plan|test_plan)$")
    data: dict[str, Any] | None = None


class DocumentResponse(BaseModel):
    id: str
    project_id: str
    type: str
    data: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Type-specific data validation schemas ---

class UserStoryData(BaseModel):
    user_type: str = Field(min_length=1)
    action: str = Field(min_length=1)
    benefit: str = Field(min_length=1)
    priority: str = Field(default="medium", pattern=r"^(high|medium|low)$")
    status: str = Field(default="draft", pattern=r"^(draft|approved|implemented)$")
    acceptance_criteria: list[str] = []


class RequirementData(BaseModel):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    type: str = Field(default="functional", pattern=r"^(functional|non-functional)$")
    category: str = ""
    priority: str = Field(default="should", pattern=r"^(must|should|could|wont)$")
    status: str = Field(default="draft", pattern=r"^(draft|approved|implemented|verified)$")
    rationale: str = ""


class MilestoneData(BaseModel):
    name: str
    target_date: str = ""
    deliverables: str = ""
    status: str = Field(default="planned", pattern=r"^(planned|in_progress|completed)$")


class RiskData(BaseModel):
    description: str
    likelihood: str = Field(default="medium", pattern=r"^(low|medium|high)$")
    impact: str = Field(default="medium", pattern=r"^(low|medium|high)$")
    mitigation: str = ""


class ProjectPlanData(BaseModel):
    project_name: str = Field(min_length=1)
    project_description: str = ""
    goals: list[str] = []
    in_scope: list[str] = []
    out_scope: list[str] = []
    milestones: list[MilestoneData] = []
    risks: list[RiskData] = []


class TestCaseData(BaseModel):
    description: str
    steps: str = ""
    expected_result: str = ""
    status: str = Field(default="not_run", pattern=r"^(not_run|passed|failed|blocked)$")


class TestPlanData(BaseModel):
    test_scope: str = Field(min_length=1)
    test_strategy: str = ""
    test_cases: list[TestCaseData] = []
    entry_criteria: str = ""
    exit_criteria: str = ""
    environment: str = ""


DOCUMENT_DATA_SCHEMAS = {
    "user_story": UserStoryData,
    "requirement": RequirementData,
    "project_plan": ProjectPlanData,
    "test_plan": TestPlanData,
}
