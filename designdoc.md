# Software Design Tool — Technical Design Document

## 1. Overview

This project is a **single-user software design tool** that helps create, edit, and organize documents and diagrams covering all steps of software design.

- **Backend:** Python (Flask, server-rendered architecture)
- **Frontend:** Native HTML + JavaScript/TypeScript with **React Flow** for diagramming
- **Scope:** End-to-end support for software design workflows
- **Collaboration:** Not supported (single-user, local or self-hosted use)

### Document Types

The tool manages two categories of design artifacts:

1. **Structured Documents** — Fixed-format templates that enforce consistent structure. The user fills in predefined fields rather than writing free-form text. Includes:
   - Project Plan
   - Test Plan
   - Requirements (functional)
   - Non-Functional Requirements
   - User Stories
   - Architecture Decision Records (ADR)
   - Technology Stack
   - Risk Register
   - System Context / Domain Model
   - Acceptance Test Specifications
   - External Resources

2. **Free-Text Documents** — Unstructured documents for open-ended writing. Includes:
   - Research Documents

3. **Diagrams** — Free-form visual artifacts created via a node-edge canvas. Includes:
   - System architecture diagrams
   - UML diagrams (class, sequence, component)
   - Entity-relationship diagrams
   - Workflow / state machine diagrams

All artifacts are **exportable to a structured format optimized for LLM coding agents** (see Section 11).

---

## 2. Core Objectives

- Provide a **unified environment** for software design
- **Enforce structure** on documents via fixed templates and fill-in-the-blank formats
- Support **free-form visual modeling** for diagrams
- Enable **LLM-ready export** of all design artifacts
- Maintain **low complexity** (no real-time sync, no multi-user state)
- Ensure **extensibility** for future collaboration features

---

## 3. High-Level Architecture

```
[ Browser ]
      |
      | HTTP (HTML + JSON)
      v
[ Flask Server ]
      |
      |-- Jinja Templates (SSR pages)
      |-- REST API (JSON endpoints)
      |
      v
[ Application Services ]
      |
      v
[ SQLite / PostgreSQL ]
```

### Key Characteristics

- Server-rendered pages using **Jinja2**
- React Flow embedded inside specific views for diagramming
- REST API used for dynamic updates (save, load, export)
- Stateless HTTP interactions

---

## 4. Technology Stack

### Backend

- Python 3.11+
- Flask
- SQLAlchemy (ORM)
- Flask-Migrate (DB migrations)
- Pydantic (serialization and validation)

### Frontend

- HTML5 (server-rendered templates via Jinja2)
- TypeScript
- Vite (bundler)
- React Flow (diagram engine)

### Database

- SQLite (default)
- PostgreSQL (optional for scaling)

---

## 5. Core Modules

### 5.1 Project Management

- Create, edit, delete projects
- Each project contains all design artifacts (documents + diagrams)

**Entities:**
- Project (name, description, timestamps)

---

### 5.2 Structured Document System

All structured documents use **fixed templates** with predefined fields. The user fills in specific values rather than writing free-form prose. Each document type has its own schema.

#### 5.2.1 User Stories

Template format:

> As a **[type of user]**, I want to **[perform an action]** so that I can **[achieve a goal/benefit]**.

Fields per story:
| Field | Description |
|---|---|
| ID | Auto-generated identifier |
| User Type | Role or persona (e.g., "developer", "admin") |
| Action | What the user wants to do |
| Benefit | Why the user wants to do it |
| Priority | High / Medium / Low |
| Status | Draft / Approved / Implemented |
| Acceptance Criteria | List of verifiable conditions |

#### 5.2.2 Requirements

Table format with fixed columns:

| Field | Description |
|---|---|
| ID | Auto-generated identifier (e.g., REQ-001) |
| Title | Short name |
| Description | Detailed requirement text |
| Type | Functional / Non-functional |
| Category | Performance, Security, Usability, etc. |
| Priority | Must / Should / Could / Won't (MoSCoW) |
| Status | Draft / Approved / Implemented / Verified |
| Rationale | Why this requirement exists |

#### 5.2.3 Project Plan

Fixed sections:
- **Project Name & Description**
- **Goals & Objectives** (numbered list)
- **Scope** — In-scope / Out-of-scope items
- **Milestones** — Table: Name, Target Date, Deliverables, Status
- **Risks** — Table: Risk, Likelihood, Impact, Mitigation

#### 5.2.4 Test Plan

Fixed sections:
- **Test Scope** — What is being tested
- **Test Strategy** — Approach (unit, integration, E2E, manual)
- **Test Cases** — Table: ID, Description, Steps, Expected Result, Status
- **Entry/Exit Criteria** — Conditions to start/complete testing
- **Environment** — Required setup and dependencies

#### 5.2.5 Architecture Decision Records (ADR)

Structured record of a significant design or technology decision.

| Field | Description |
|---|---|
| ID | Auto-generated identifier (e.g., ADR-001) |
| Title | Short name for the decision |
| Status | Proposed / Accepted / Deprecated / Superseded |
| Context | Why this decision was needed; forces at play |
| Decision | What was decided |
| Alternatives Considered | List of alternatives with brief pros/cons per entry |
| Consequences | Positive and negative outcomes of the decision |
| Related ADRs | References to superseding or related ADR IDs |

#### 5.2.6 Technology Stack

One row per technology in use; collectively describes the full stack.

| Field | Description |
|---|---|
| ID | Auto-generated identifier (e.g., TECH-001) |
| Category | Frontend / Backend / Database / Infrastructure / Testing / Other |
| Technology | Name (e.g., "Flask", "PostgreSQL") |
| Version | Pinned version or range |
| Rationale | Why this technology was chosen |
| Alternatives Considered | What was evaluated but rejected |
| ADR Reference | Optional link to the ADR that records the decision |

#### 5.2.7 Non-Functional Requirements

Dedicated table for NFRs. Kept separate from functional requirements because they drive architecture and often have distinct owners and review cycles.

| Field | Description |
|---|---|
| ID | Auto-generated identifier (e.g., NFR-001) |
| Title | Short name |
| Category | Performance / Security / Reliability / Scalability / Privacy / Compliance / Usability |
| Description | Measurable statement of the requirement |
| Rationale | Why this NFR exists |
| Priority | Must / Should / Could / Won't (MoSCoW) |
| Status | Draft / Approved / Verified |
| Verification Method | How compliance is measured or tested |

#### 5.2.8 Risk Register

First-class document for tracking project and technical risks independently from the Project Plan.

| Field | Description |
|---|---|
| ID | Auto-generated identifier (e.g., RISK-001) |
| Title | Short name |
| Description | Full description of the risk |
| Category | Technical / Business / Resource / External |
| Likelihood | High / Medium / Low |
| Impact | High / Medium / Low |
| Status | Open / Mitigating / Accepted / Closed |
| Owner | Person or role responsible |
| Mitigation | Actions taken or planned |
| Review Date | Next scheduled review |
| Notes | Free-text notes |

#### 5.2.9 System Context / Domain Model

Prose + structured hybrid that captures the bounded context, domain language, and external integrations in one place.

Fixed sections:
- **Bounded Context Name & Description** — what is inside and outside this context
- **Major Entities** — table: Name, Description, Key Attributes
- **Domain Language** (Ubiquitous Language) — glossary table: Term, Definition
- **Business Rules** — numbered list of invariants and constraints
- **External Systems** — table: System Name, Type, Integration Description, Owner

#### 5.2.10 Acceptance Test Specifications

Executable acceptance criteria with direct traceability to requirements and user stories. More granular than the Test Plan.

| Field | Description |
|---|---|
| ID | Auto-generated identifier (e.g., ATS-001) |
| Title | Short scenario name |
| Requirement Reference | FK to a Requirement ID (optional) |
| User Story Reference | FK to a User Story ID (optional) |
| Preconditions | State required before executing the test |
| Steps | Ordered list of actions |
| Expected Result | Observable outcome that constitutes a pass |
| Status | Draft / Approved / Pass / Fail / Blocked |
| Notes | Free-text notes |

#### 5.2.11 External Resources

Catalogue of external dependencies — APIs, SDKs, services, documentation — that the system integrates with or relies on.

| Field | Description |
|---|---|
| ID | Auto-generated identifier (e.g., EXT-001) |
| Name | Name of the external resource |
| Type | API / SDK / Service / Library / Documentation |
| URL | Primary reference URL |
| Description | What the resource provides and how it is used |
| Authentication | None / API Key / OAuth / Other |
| Notes | Rate limits, licensing, or other constraints |

#### 5.2.12 Research Documents

Unstructured freetext documents for capturing investigations, spikes, literature reviews, and exploratory notes. No fixed schema — title + Markdown body only.

| Field | Description |
|---|---|
| Title | Document title |
| Body | Freetext content (Markdown) |
| Tags | Optional comma-separated tags |
| Created At | Timestamp |

---

### 5.3 Diagram Editor

Free-form visual editor for all diagram types. Uses **React Flow** as the rendering engine.

Supported diagram types:
- Architecture diagrams (component, system boundary, service relationships)
- UML diagrams (class, sequence, component)
- Entity-relationship diagrams
- Workflow / state machine diagrams

**Implementation:**
- Diagram state stored as JSON (nodes + edges + metadata)
- Nodes/edges rendered and edited via React Flow
- Drag-and-drop node creation
- Custom node types per diagram category

---

### 5.4 API Design

Structured editor for REST API definitions.

Fields per endpoint:

| Field | Description |
|---|---|
| Path | URL path (e.g., `/api/users/{id}`) |
| Method | GET, POST, PUT, DELETE, PATCH |
| Description | What the endpoint does |
| Parameters | Path, query, header params |
| Request Body | JSON schema |
| Response Body | JSON schema |
| Status Codes | Expected responses |

---

## 6. Data Model

### Core Tables

#### Project
| Column | Type |
|---|---|
| id | UUID (PK) |
| name | String |
| description | Text |
| created_at | DateTime |
| updated_at | DateTime |

#### Document
| Column | Type |
|---|---|
| id | UUID (PK) |
| project_id | UUID (FK → Project) |
| type | Enum: user_story, requirement, nfr, project_plan, test_plan, adr, tech_stack, risk_register, domain_model, acceptance_test, external_resource, research |
| data | JSON (schema varies by type) |
| created_at | DateTime |
| updated_at | DateTime |

#### Diagram
| Column | Type |
|---|---|
| id | UUID (PK) |
| project_id | UUID (FK → Project) |
| type | Enum: architecture, uml_class, uml_sequence, uml_component, er, workflow |
| name | String |
| data | JSON (nodes, edges, metadata) |
| created_at | DateTime |
| updated_at | DateTime |

#### APIEndpoint
| Column | Type |
|---|---|
| id | UUID (PK) |
| project_id | UUID (FK → Project) |
| path | String |
| method | String |
| description | Text |
| request_schema | JSON |
| response_schema | JSON |

#### RequirementTestLink
Traceability table connecting requirements and user stories to acceptance test specifications.

| Column | Type |
|---|---|
| id | UUID (PK) |
| requirement_id | UUID (FK → Document, nullable) |
| user_story_id | UUID (FK → Document, nullable) |
| acceptance_test_id | UUID (FK → Document) |

---

## 7. Backend Design

### Flask Structure

```
/app
  /routes          # HTTP request handlers
  /services        # Business logic, validation, transformation
  /models          # SQLAlchemy ORM models
  /schemas         # Pydantic models for validation & serialization
  /templates       # Jinja2 HTML templates
  /static          # CSS, JS bundles, assets
  /export          # LLM export formatters
```

### Key Layers

#### Routes
- Handle HTTP requests
- Return HTML (Jinja2) or JSON (API)

#### Services
- Business logic
- Document template enforcement and validation
- Data transformation

#### Models
- SQLAlchemy ORM models

#### Export
- Convert documents and diagrams to LLM-optimized format

---

### Example Routes

```python
@app.route("/projects/<id>")
def project_detail(id):
    project = ProjectService.get(id)
    return render_template("project.html", project=project)
```

```python
@app.route("/api/diagrams/<id>", methods=["POST"])
def update_diagram(id):
    data = request.json
    DiagramService.update(id, data)
    return {"status": "ok"}
```

```python
@app.route("/api/projects/<id>/export", methods=["GET"])
def export_project(id):
    format = request.args.get("format", "llm")
    result = ExportService.export(id, format)
    return result
```

---

## 8. Frontend Design

### Approach

- Server renders base HTML via Jinja2 templates
- React Flow initialized on diagram editor pages
- TypeScript handles all client-side interactivity
- Structured document editors use form-based UIs with fixed fields

### React Flow Integration

Used for all diagram types. Responsibilities:
- Render nodes and edges
- Handle drag-and-drop
- Emit state updates on change

### State Handling

- Local state in browser during editing
- Persist via API calls on save
- Optimistic UI updates

### Editing Flow

1. User opens a document or diagram
2. Editor loads current state from API
3. User edits (fills fields or manipulates canvas)
4. User clicks "Save" → POST to Flask API → stored as JSON
5. User clicks "Export" → GET export endpoint → download file

---

## 9. UI Structure

### Pages

| Page | Purpose |
|---|---|
| Dashboard | List of all projects |
| Project Overview | All artifacts within a project |
| User Stories Editor | Form-based, fill-in-the-blank template |
| Requirements Editor | Table-based structured editor |
| Project Plan Editor | Section-based form editor |
| Test Plan Editor | Section-based form editor |
| Diagram Editor | React Flow canvas |
| API Designer | Form-based endpoint editor |

### Navigation

- Sidebar per project with section-based navigation
- Breadcrumb trail for context

---

## 10. Storage Strategy

### Documents

Stored as JSON conforming to a schema per document type. Example user story:

```json
{
  "user_type": "developer",
  "action": "generate boilerplate code",
  "benefit": "save time on repetitive tasks",
  "priority": "high",
  "status": "draft",
  "acceptance_criteria": [
    "Code compiles without errors",
    "Follows project style guide"
  ]
}
```

### Diagrams

Stored as JSON compatible with React Flow:

```json
{
  "nodes": [
    { "id": "1", "type": "component", "position": { "x": 100, "y": 200 }, "data": { "label": "Auth Service" } }
  ],
  "edges": [
    { "id": "e1-2", "source": "1", "target": "2", "label": "HTTP" }
  ]
}
```

---

## 11. LLM Export

All documents and diagrams are exportable to a structured format tailored for consumption by LLM coding agents.

### Export Format

A single JSON (or Markdown) file per project containing all artifacts in a machine-readable structure:

```json
{
  "project": "My App",
  "requirements": [
    { "id": "REQ-001", "title": "...", "type": "functional", "priority": "must", "description": "..." }
  ],
  "nfrs": [
    { "id": "NFR-001", "title": "...", "category": "performance", "description": "...", "verification_method": "..." }
  ],
  "user_stories": [
    { "id": "US-001", "as_a": "developer", "i_want_to": "...", "so_that": "...", "acceptance_criteria": ["..."] }
  ],
  "adrs": [
    { "id": "ADR-001", "title": "...", "status": "accepted", "context": "...", "decision": "...", "consequences": "..." }
  ],
  "tech_stack": [
    { "id": "TECH-001", "category": "backend", "technology": "Flask", "version": "3.x", "rationale": "..." }
  ],
  "risk_register": [
    { "id": "RISK-001", "title": "...", "category": "technical", "likelihood": "medium", "impact": "high", "status": "open", "mitigation": "..." }
  ],
  "domain_model": { "bounded_context": "...", "entities": ["..."], "business_rules": ["..."], "external_systems": ["..."] },
  "acceptance_tests": [
    { "id": "ATS-001", "title": "...", "requirement_id": "REQ-001", "steps": ["..."], "expected_result": "..." }
  ],
  "external_resources": [
    { "id": "EXT-001", "name": "...", "type": "api", "url": "...", "description": "..." }
  ],
  "project_plan": { "goals": ["..."], "milestones": ["..."] },
  "test_plan": { "test_cases": ["..."] },
  "diagrams": [
    { "type": "architecture", "name": "System Overview", "nodes": ["..."], "edges": ["..."] }
  ],
  "api_endpoints": [
    { "path": "/api/users", "method": "GET", "description": "...", "response_schema": {} }
  ],
  "traceability": [
    { "requirement_id": "REQ-001", "acceptance_test_ids": ["ATS-001"] }
  ]
}
```

### Design Principles for Export

- Self-contained: no external references needed
- Consistent key naming across all artifact types
- Includes all context an LLM agent needs to begin implementation
- Supports both JSON and Markdown output formats

---

## 12. Non-Functional Requirements

### Performance
- Lightweight frontend; minimal JS outside diagram views
- Fast page loads via server-side rendering

### Maintainability
- Modular backend services
- Clear separation of concerns (routes → services → models)

### Extensibility
- Future support for: collaboration, versioning, PDF/PNG export

---

## 13. Limitations

- No real-time collaboration
- No offline sync
- Limited diagram validation (structural only)
- Single-user access control

---

## 14. Future Enhancements

- Multi-user collaboration
- Role-based access control
- Version history and diffing
- Diagram templates and component libraries
- Code generation from data models and API definitions
- AI-assisted design suggestions

---

## 15. Development Roadmap

This roadmap is written for **AI coding agents**. Each phase is a self-contained unit of work. Complete all tasks in a phase before moving to the next. Each task should be implemented, tested, and committed independently.

### Phase 1 — Project Scaffolding & Data Layer

1. Initialize Flask application with standard project structure (`/app/routes`, `/services`, `/models`, `/schemas`, `/templates`, `/static`, `/export`)
2. Configure SQLAlchemy with SQLite and Flask-Migrate
3. Create ORM models: `Project`, `Document`, `Diagram`, `APIEndpoint`
4. Create Pydantic schemas for all models
5. Implement Project CRUD (routes + service + templates)
6. Add seed data script for development
7. Write unit tests for Project CRUD

### Phase 2 — Structured Document Editors

1. Implement User Stories editor: form UI with fill-in-the-blank fields (`user_type`, `action`, `benefit`, `priority`, `status`, `acceptance_criteria`), CRUD API, Jinja template
2. Implement Requirements editor: table-based UI with fixed columns (`title`, `description`, `type`, `category`, `priority`, `status`, `rationale`), CRUD API, Jinja template
3. Implement Project Plan editor: section-based form (goals, scope, milestones table, risks table), CRUD API, Jinja template
4. Implement Test Plan editor: section-based form (scope, strategy, test cases table, entry/exit criteria, environment), CRUD API, Jinja template
5. Add Pydantic validation for each document type's JSON schema
6. Write tests for all document CRUD operations

### Phase 3 — Diagram Engine

1. Set up Vite + TypeScript build pipeline for frontend assets
2. Integrate React Flow into a diagram editor page
3. Implement custom node types for: architecture components, UML classes, ER entities, workflow states
4. Implement diagram save/load via REST API (JSON serialization)
5. Add diagram type selection and creation flow
6. Write tests for diagram persistence

### Phase 4 — API Designer

1. Implement API endpoint editor: form UI with fields for path, method, description, parameters, request/response schemas
2. CRUD API for API endpoints
3. Jinja template for API overview and detail views
4. Write tests for API endpoint CRUD

### Phase 5 — LLM Export

1. Implement `ExportService` that aggregates all project artifacts into a single JSON structure
2. Implement Markdown export format as alternative
3. Add export route: `GET /api/projects/<id>/export?format=json|markdown`
4. Add "Export for LLM" button to project overview UI
5. Write tests validating export output structure

### Phase 7 — Extended Document Types & Traceability

Implements all document types identified in the second design review. Builds on the editor infrastructure from Phase 2.

1. Implement **Architecture Decision Record (ADR)** editor: form UI with fields for status, context, decision, alternatives (repeating group), consequences, and related-ADR references. CRUD API, Jinja template.
2. Implement **Technology Stack** editor: table-based UI with fields for category, technology, version, rationale, alternatives, and optional ADR reference. CRUD API, Jinja template.
3. Implement **Non-Functional Requirements** editor: table-based UI, same structure as functional requirements but category is drawn from the NFR category enum (Performance, Security, Reliability, Scalability, Privacy, Compliance, Usability). Verification method field added. CRUD API, Jinja template.
4. Implement **Risk Register** editor: table-based UI with fields for category, likelihood, impact, status, owner, mitigation, and review date. CRUD API, Jinja template.
5. Implement **System Context / Domain Model** editor: section-based form with subsections for bounded context description, entities table, ubiquitous language glossary, business rules list, and external systems table. CRUD API, Jinja template.
6. Implement **Acceptance Test Specification** editor: table-based UI with fields for preconditions, ordered steps (repeating group), expected result, status, and optional FK references to requirement IDs and user story IDs. CRUD API, Jinja template.
7. Implement **External Resources** editor: table-based UI with fields for type, URL, description, and authentication method. CRUD API, Jinja template.
8. Implement **Research Documents** editor: title + Markdown body + tags. Freetext (no fixed schema). CRUD API, Jinja template.
9. Create `RequirementTestLink` ORM model and migration. Implement link management UI on the Acceptance Test Specification editor (pick-list to associate one or more requirement or user story IDs). Add corresponding read-only traceability panel on the Requirements and User Stories editors showing linked acceptance tests.
10. Add Pydantic schemas for all new document types.
11. Extend `ExportService` to include all new document types in the LLM export output.
12. Write unit tests for CRUD operations and Pydantic validation for each new document type. Write an integration test for the traceability link (create requirement → create acceptance test → link them → verify export includes the link).

### Phase 6 — Polish & Integration

1. Implement dashboard page listing all projects
2. Add sidebar navigation within projects
3. Add breadcrumb navigation
4. UI styling pass (consistent layout, spacing, typography)
5. Input validation and error handling on all forms
6. End-to-end test: create project → add all artifact types → export

---

## 16. Summary

This system provides a modular, server-rendered software design platform that combines:

- **Flask** for backend simplicity
- **React Flow** for rich free-form diagramming
- **Fixed-format templates** for structured documents (user stories, requirements, NFRs, project plans, test plans, ADRs, technology stack, risk register, domain model, acceptance tests, external resources)
- **Free-text documents** for research and exploratory notes
- **Requirement-to-test traceability** linking requirements and user stories to acceptance test specifications
- **LLM-optimized export** for all design artifacts

The architecture prioritizes simplicity, maintainability, and structured output — ensuring that design work flows directly into implementation by AI coding agents.