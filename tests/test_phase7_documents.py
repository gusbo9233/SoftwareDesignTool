"""Tests for Phase 7 document types: ADR, TechStack, NFR, RiskRegister,
DomainModel, AcceptanceTest, ExternalResource, ResearchDocument."""
import pytest
from pydantic import ValidationError
from app.services.document_service import DocumentService
from app.schemas.document import (
    ADRData,
    TechStackData,
    NFRData,
    RiskRegisterData,
    DomainModelData,
    AcceptanceTestData,
    ExternalResourceData,
    ResearchDocumentData,
)


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------

class TestPhase7DocumentService:
    def test_create_adr(self, project_id):
        doc = DocumentService.create(
            project_id=project_id,
            doc_type="adr",
            data={"title": "Use Flask", "context": "Need a backend", "decision": "Use Flask"},
        )
        assert doc.type == "adr"
        assert doc.data["title"] == "Use Flask"

    def test_create_tech_stack(self, project_id):
        doc = DocumentService.create(
            project_id=project_id,
            doc_type="tech_stack",
            data={"items": [{"category": "backend", "technology": "Flask", "version": "3.x"}]},
        )
        assert doc.type == "tech_stack"
        assert doc.data["items"][0]["technology"] == "Flask"

    def test_create_nfr(self, project_id):
        doc = DocumentService.create(
            project_id=project_id,
            doc_type="nfr",
            data={"title": "Response Time", "category": "performance", "description": "< 200ms"},
        )
        assert doc.type == "nfr"
        assert doc.data["category"] == "performance"

    def test_create_risk_register(self, project_id):
        doc = DocumentService.create(
            project_id=project_id,
            doc_type="risk_register",
            data={"items": [{"title": "DB failure", "likelihood": "low", "impact": "high"}]},
        )
        assert doc.type == "risk_register"
        assert doc.data["items"][0]["title"] == "DB failure"

    def test_create_domain_model(self, project_id):
        doc = DocumentService.create(
            project_id=project_id,
            doc_type="domain_model",
            data={"bounded_context_name": "Auth", "entities": [{"name": "User"}]},
        )
        assert doc.type == "domain_model"
        assert doc.data["bounded_context_name"] == "Auth"

    def test_create_acceptance_test(self, project_id):
        doc = DocumentService.create(
            project_id=project_id,
            doc_type="acceptance_test",
            data={"title": "Login succeeds", "steps": ["Open login page", "Enter credentials"], "expected_result": "User is logged in"},
        )
        assert doc.type == "acceptance_test"
        assert len(doc.data["steps"]) == 2

    def test_create_external_resource(self, project_id):
        doc = DocumentService.create(
            project_id=project_id,
            doc_type="external_resource",
            data={"name": "Stripe API", "type": "api", "authentication": "api_key"},
        )
        assert doc.type == "external_resource"
        assert doc.data["name"] == "Stripe API"

    def test_create_research(self, project_id):
        doc = DocumentService.create(
            project_id=project_id,
            doc_type="research",
            data={"title": "Auth spike", "body": "Investigation notes", "tags": "auth, security"},
        )
        assert doc.type == "research"
        assert doc.data["tags"] == "auth, security"


# ---------------------------------------------------------------------------
# Route tests
# ---------------------------------------------------------------------------

class TestPhase7DocumentRoutes:
    def test_create_adr_get(self, client, project_id):
        response = client.get(f"/projects/{project_id}/documents/new/adr")
        assert response.status_code == 200
        assert b"Architecture Decision Record" in response.data

    def test_create_adr_post(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/documents/new/adr",
            data={
                "title": "Use PostgreSQL",
                "status": "accepted",
                "context": "Need a robust DB",
                "decision": "Chose PostgreSQL over MySQL",
                "consequences": "Better JSON support",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Use PostgreSQL" in response.data

    def test_create_adr_missing_fields(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/documents/new/adr",
            data={"title": "", "context": "", "decision": ""},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"required" in response.data

    def test_create_nfr_get(self, client, project_id):
        response = client.get(f"/projects/{project_id}/documents/new/nfr")
        assert response.status_code == 200
        assert b"Non-Functional" in response.data

    def test_create_nfr_post(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/documents/new/nfr",
            data={
                "title": "99.9% uptime",
                "category": "reliability",
                "description": "System must have 99.9% uptime",
                "priority": "must",
                "status": "draft",
                "verification_method": "Uptime monitoring",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"99.9% uptime" in response.data

    def test_create_tech_stack_post(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/documents/new/tech_stack",
            data={
                "tech_technology": ["Flask", "PostgreSQL"],
                "tech_category": ["backend", "database"],
                "tech_version": ["3.x", "15"],
                "tech_rationale": ["Simple", "Robust"],
                "tech_alternatives": ["FastAPI", "MySQL"],
                "tech_adr_reference": ["ADR-001", ""],
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

    def test_create_risk_register_post(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/documents/new/risk_register",
            data={
                "risk_title": ["DB corruption"],
                "risk_description": [""],
                "risk_category": ["technical"],
                "risk_likelihood": ["low"],
                "risk_impact": ["high"],
                "risk_status": ["open"],
                "risk_owner": ["DBA"],
                "risk_mitigation": ["Daily backups"],
                "risk_review_date": ["2026-05-01"],
                "risk_notes": [""],
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

    def test_create_domain_model_post(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/documents/new/domain_model",
            data={
                "bounded_context_name": "Authentication",
                "bounded_context_description": "Handles user auth",
                "entity_name": ["User"],
                "entity_description": ["A registered user"],
                "entity_key_attributes": ["id, email"],
                "glossary_term": ["Token"],
                "glossary_definition": ["A JWT access token"],
                "business_rules": ["Passwords must be hashed"],
                "ext_name": [],
                "ext_type": [],
                "ext_integration_description": [],
                "ext_owner": [],
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Authentication" in response.data

    def test_create_domain_model_missing_name(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/documents/new/domain_model",
            data={"bounded_context_name": ""},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"required" in response.data

    def test_create_acceptance_test_post(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/documents/new/acceptance_test",
            data={
                "title": "User can log in",
                "preconditions": "User is registered",
                "steps": ["Navigate to login", "Enter valid credentials", "Click submit"],
                "expected_result": "User is redirected to dashboard",
                "status": "approved",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"User can log in" in response.data

    def test_create_acceptance_test_missing_fields(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/documents/new/acceptance_test",
            data={"title": "", "expected_result": ""},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"required" in response.data

    def test_create_external_resource_post(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/documents/new/external_resource",
            data={
                "name": "SendGrid",
                "resource_type": "api",
                "url": "https://sendgrid.com/api",
                "description": "Email delivery service",
                "authentication": "api_key",
                "notes": "10k free emails/month",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"SendGrid" in response.data

    def test_create_research_post(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/documents/new/research",
            data={
                "title": "Auth options spike",
                "body": "Investigated JWT vs session auth...",
                "tags": "auth, security",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Auth options spike" in response.data

    def test_create_research_missing_title(self, client, project_id):
        response = client.post(
            f"/projects/{project_id}/documents/new/research",
            data={"title": "", "body": "Some content"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"required" in response.data


# ---------------------------------------------------------------------------
# Pydantic schema tests
# ---------------------------------------------------------------------------

class TestPhase7Schemas:
    def test_adr_valid(self):
        data = ADRData(title="Use Flask", context="Need backend", decision="Flask chosen")
        assert data.status == "proposed"
        assert data.alternatives == []

    def test_adr_missing_required(self):
        with pytest.raises(ValidationError):
            ADRData(title="", context="ctx", decision="dec")

    def test_adr_invalid_status(self):
        with pytest.raises(ValidationError):
            ADRData(title="T", context="C", decision="D", status="invalid")

    def test_tech_stack_valid(self):
        data = TechStackData(items=[{"category": "backend", "technology": "Flask"}])
        assert len(data.items) == 1

    def test_nfr_valid(self):
        data = NFRData(title="Latency", category="performance", description="< 200ms p99")
        assert data.priority == "should"
        assert data.status == "draft"

    def test_nfr_missing_required(self):
        with pytest.raises(ValidationError):
            NFRData(title="", category="performance", description="desc")

    def test_nfr_invalid_category(self):
        with pytest.raises(ValidationError):
            NFRData(title="T", category="invalid", description="D")

    def test_risk_register_valid(self):
        data = RiskRegisterData(items=[{"title": "Risk A"}])
        assert data.items[0].title == "Risk A"

    def test_domain_model_valid(self):
        data = DomainModelData(bounded_context_name="Auth")
        assert data.entities == []
        assert data.glossary == []

    def test_domain_model_missing_name(self):
        with pytest.raises(ValidationError):
            DomainModelData(bounded_context_name="")

    def test_acceptance_test_valid(self):
        data = AcceptanceTestData(title="Test login", expected_result="User logged in")
        assert data.status == "draft"
        assert data.steps == []

    def test_acceptance_test_missing_required(self):
        with pytest.raises(ValidationError):
            AcceptanceTestData(title="", expected_result="something")

    def test_external_resource_valid(self):
        data = ExternalResourceData(name="Stripe")
        assert data.type == "api"
        assert data.authentication == "none"

    def test_external_resource_missing_name(self):
        with pytest.raises(ValidationError):
            ExternalResourceData(name="")

    def test_research_valid(self):
        data = ResearchDocumentData(title="Spike: OAuth")
        assert data.body == ""
        assert data.tags == ""

    def test_research_missing_title(self):
        with pytest.raises(ValidationError):
            ResearchDocumentData(title="")
