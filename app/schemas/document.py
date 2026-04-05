from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

_TYPE_PATTERN = (
    r"^(user_story|requirement|project_plan|test_plan|"
    r"adr|tech_stack|nfr|risk_register|domain_model|acceptance_test|external_resource|research)$"
)


class DocumentCreate(BaseModel):
    project_id: str
    type: str = Field(pattern=_TYPE_PATTERN)
    data: dict[str, Any] = {}


class DocumentUpdate(BaseModel):
    type: str | None = Field(default=None, pattern=_TYPE_PATTERN)
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


# --- Phase 7: Extended document types ---

class ADRAlternativeData(BaseModel):
    name: str
    pros: str = ""
    cons: str = ""


class ADRData(BaseModel):
    title: str = Field(min_length=1)
    status: str = Field(default="proposed", pattern=r"^(proposed|accepted|deprecated|superseded)$")
    context: str = Field(min_length=1)
    decision: str = Field(min_length=1)
    alternatives: list[ADRAlternativeData] = []
    consequences: str = ""
    related_adrs: list[str] = []


class TechStackItemData(BaseModel):
    category: str
    technology: str
    version: str = ""
    rationale: str = ""
    alternatives_considered: str = ""
    adr_reference: str = ""


class TechStackData(BaseModel):
    items: list[TechStackItemData] = []


class NFRData(BaseModel):
    title: str = Field(min_length=1)
    category: str = Field(
        default="performance",
        pattern=r"^(performance|security|reliability|scalability|privacy|compliance|usability)$",
    )
    description: str = Field(min_length=1)
    rationale: str = ""
    priority: str = Field(default="should", pattern=r"^(must|should|could|wont)$")
    status: str = Field(default="draft", pattern=r"^(draft|approved|verified)$")
    verification_method: str = ""


class RiskRegisterItemData(BaseModel):
    title: str
    description: str = ""
    category: str = Field(default="technical", pattern=r"^(technical|business|resource|external)$")
    likelihood: str = Field(default="medium", pattern=r"^(low|medium|high)$")
    impact: str = Field(default="medium", pattern=r"^(low|medium|high)$")
    status: str = Field(default="open", pattern=r"^(open|mitigating|accepted|closed)$")
    owner: str = ""
    mitigation: str = ""
    review_date: str = ""
    notes: str = ""


class RiskRegisterData(BaseModel):
    items: list[RiskRegisterItemData] = []


class DomainModelEntityData(BaseModel):
    name: str
    description: str = ""
    key_attributes: str = ""


class DomainModelGlossaryTermData(BaseModel):
    term: str
    definition: str = ""


class DomainModelExternalSystemData(BaseModel):
    name: str
    system_type: str = ""
    integration_description: str = ""
    owner: str = ""


class DomainModelData(BaseModel):
    bounded_context_name: str = Field(min_length=1)
    bounded_context_description: str = ""
    entities: list[DomainModelEntityData] = []
    glossary: list[DomainModelGlossaryTermData] = []
    business_rules: list[str] = []
    external_systems: list[DomainModelExternalSystemData] = []


class AcceptanceTestData(BaseModel):
    title: str = Field(min_length=1)
    requirement_reference: str = ""
    user_story_reference: str = ""
    preconditions: str = ""
    steps: list[str] = []
    expected_result: str = Field(min_length=1)
    status: str = Field(default="draft", pattern=r"^(draft|approved|pass|fail|blocked)$")
    notes: str = ""


class ExternalResourceData(BaseModel):
    name: str = Field(min_length=1)
    type: str = Field(
        default="api",
        pattern=r"^(api|sdk|service|library|documentation|other)$",
    )
    url: str = ""
    description: str = ""
    authentication: str = Field(default="none", pattern=r"^(none|api_key|oauth|other)$")
    notes: str = ""


class ResearchDocumentData(BaseModel):
    title: str = Field(min_length=1)
    body: str = ""
    tags: str = ""


DOCUMENT_DATA_SCHEMAS = {
    "user_story": UserStoryData,
    "requirement": RequirementData,
    "project_plan": ProjectPlanData,
    "test_plan": TestPlanData,
    "adr": ADRData,
    "tech_stack": TechStackData,
    "nfr": NFRData,
    "risk_register": RiskRegisterData,
    "domain_model": DomainModelData,
    "acceptance_test": AcceptanceTestData,
    "external_resource": ExternalResourceData,
    "research": ResearchDocumentData,
}
