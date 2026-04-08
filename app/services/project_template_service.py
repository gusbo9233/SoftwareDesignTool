from types import SimpleNamespace

from app.services.diagram_service import DiagramService
from app.services.document_service import DocumentService


DEFAULT_TEMPLATE_KEY = "generic"


PROJECT_TEMPLATES = {
    "generic": {
        "key": "generic",
        "label": "General Software Project",
        "summary": "A blank project workspace you can shape into any stack or architecture.",
        "focus": "No starter architecture is enforced.",
        "layers": [],
        "starter_outputs": [],
    },
    "aspnetcore_clean_architecture": {
        "key": "aspnetcore_clean_architecture",
        "label": "ASP.NET Core Clean Architecture",
        "summary": "A CleanArchitecture-template-aligned ASP.NET Core solution with the same top-level solution shape and a ready-to-grow set of application folders.",
        "focus": "Based on jasontaylordev/CleanArchitecture, with fixed core projects and nested starter folders for common clean architecture workflows.",
        "layers": [
            "Domain for entities, enums, and core business rules",
            "Application for use cases, DTOs, validation, and interfaces",
            "Infrastructure for EF Core, repositories, external services, and persistence",
            "Web/AppHost/Shared projects to match the CleanArchitecture template layout",
        ],
        "starter_outputs": [
            "Technology Stack document with recommended packages and responsibilities",
            "Project Plan seeded around clean architecture milestones",
            "ADR describing why the layered structure was chosen",
            "Folder Structure designer with a fixed clean architecture core",
            "Architecture diagram showing the dependency flow between layers",
        ],
    },
    "mvc": {
        "key": "mvc",
        "label": "Model View Controller",
        "summary": "A classic MVC project layout with clear separation between domain state, UI rendering, and request handling.",
        "focus": "Designed for server-rendered apps and CRUD-heavy products that benefit from explicit controllers, views, and models.",
        "layers": [
            "Models for domain state, validation, and business-facing data structures",
            "Views for templates, shared layouts, and user-facing rendering",
            "Controllers for request orchestration and navigation flow",
            "Supporting services, static assets, and tests around the MVC surface",
        ],
        "starter_outputs": [
            "Technology Stack document tailored to an MVC delivery model",
            "Project Plan seeded around MVC milestones and UI flow delivery",
            "ADR describing why MVC was chosen",
            "Folder Structure designer with a fixed MVC core",
            "Architecture diagram showing controller, model, and view responsibilities",
        ],
    },
}


def _template_marker(data):
    if not isinstance(data, dict):
        return None
    return data.get("_template_key")


class ProjectTemplateService:
    @staticmethod
    def _template_documents(project_id):
        docs = DocumentService.get_all_for_project(project_id)
        by_type = {doc.type: doc for doc in docs if _template_marker(getattr(doc, "data", None))}
        return docs, by_type

    @staticmethod
    def list_templates():
        return list(PROJECT_TEMPLATES.values())

    @staticmethod
    def normalize_template_key(template_key):
        if template_key in PROJECT_TEMPLATES:
            return template_key
        return DEFAULT_TEMPLATE_KEY

    @staticmethod
    def get_template(template_key):
        return PROJECT_TEMPLATES[ProjectTemplateService.normalize_template_key(template_key)]

    @staticmethod
    def resolve_template_key(project=None, documents=None):
        project_key = getattr(project, "template_key", None)
        if project_key in PROJECT_TEMPLATES:
            return project_key

        for doc in documents or []:
            template_key = _template_marker(getattr(doc, "data", None))
            if template_key in PROJECT_TEMPLATES:
                return template_key

        return DEFAULT_TEMPLATE_KEY

    @staticmethod
    def resolve_template(project=None, documents=None):
        return ProjectTemplateService.get_template(
            ProjectTemplateService.resolve_template_key(project=project, documents=documents)
        )

    @staticmethod
    def _project_plan(project_name, description, template_key):
        is_mvc = template_key == "mvc"
        return {
            "_template_key": template_key,
            "project_name": project_name,
            "project_description": description or (
                "Build a Model View Controller application with clear request handling, view rendering, and domain boundaries."
                if is_mvc else
                "Build an ASP.NET Core solution using Clean Architecture boundaries and delivery milestones."
            ),
            "goals": [
                "Establish a clear separation between controllers, models, and views",
                "Define the core user flows and renderable screens early",
                "Structure reusable services and persistence concerns cleanly",
                "Ship a testable web application with predictable routing and UI behavior",
            ] if is_mvc else [
                "Establish a cleanly layered solution structure",
                "Define domain rules and application use cases early",
                "Wire persistence through Infrastructure with EF Core",
                "Ship a testable API surface with clear dependency boundaries",
            ],
            "in_scope": [
                "Controller, model, and view boundaries",
                "Routing, view composition, and shared layouts",
                "Service layer and persistence setup",
                "Unit and integration testing strategy for request flows",
            ] if is_mvc else [
                "Domain, Application, Infrastructure, and API project boundaries",
                "Dependency injection and service registration",
                "EF Core persistence setup",
                "Unit and integration testing strategy",
            ],
            "out_scope": [
                "SPA frontend rewrite",
                "Deployment-specific cloud infrastructure",
            ],
            "milestones": [
                {
                    "name": "MVC Skeleton" if is_mvc else "Solution Skeleton",
                    "target_date": "",
                    "deliverables": "Controllers, models, views, routing, and folder conventions" if is_mvc else "Projects, references, and folder conventions",
                    "status": "planned",
                },
                {
                    "name": "Core User Flows" if is_mvc else "Application Core",
                    "target_date": "",
                    "deliverables": "Primary controllers, view models, validation, and reusable views" if is_mvc else "Use cases, interfaces, validation, and domain entities",
                    "status": "planned",
                },
                {
                    "name": "Persistence + Delivery" if is_mvc else "Infrastructure + API",
                    "target_date": "",
                    "deliverables": "Persistence, services, static assets, and integration testing" if is_mvc else "DbContext, repositories, DI wiring, controllers, and health endpoints",
                    "status": "planned",
                },
            ],
            "risks": [
                {
                    "description": (
                        "Controllers can become overloaded if presentation logic, validation, and business rules are not separated early."
                        if is_mvc else
                        "Layer boundaries erode if API or Infrastructure starts owning business logic"
                    ),
                    "likelihood": "medium",
                    "impact": "high",
                    "mitigation": (
                        "Keep controllers thin, introduce services/view models, and review responsibilities regularly."
                        if is_mvc else
                        "Keep business rules in Domain/Application and review project references early"
                    ),
                }
            ],
        }

    @staticmethod
    def _tech_stack(template_key):
        if template_key == "mvc":
            return {
                "_template_key": template_key,
                "items": [
                    {
                        "category": "Architecture",
                        "technology": "Model View Controller",
                        "version": "",
                        "rationale": "Provides a clear split between request handling, view rendering, and domain data",
                        "alternatives_considered": "Clean Architecture, SPA frontend with API backend",
                        "adr_reference": "ADR: MVC baseline",
                    },
                    {
                        "category": "Presentation",
                        "technology": "Server-rendered templates",
                        "version": "",
                        "rationale": "Supports fast delivery of navigable screens and form-driven flows",
                        "alternatives_considered": "Client-rendered SPA",
                        "adr_reference": "ADR: MVC baseline",
                    },
                    {
                        "category": "Application",
                        "technology": "Service layer",
                        "version": "",
                        "rationale": "Keeps controllers thin and moves reusable business logic out of the view layer",
                        "alternatives_considered": "Fat controllers",
                        "adr_reference": "ADR: MVC baseline",
                    },
                    {
                        "category": "Testing",
                        "technology": "Unit + integration tests",
                        "version": "",
                        "rationale": "Covers controllers, view models, and end-to-end request flows",
                        "alternatives_considered": "Manual QA only",
                        "adr_reference": "",
                    },
                ],
            }
        return {
            "_template_key": template_key,
            "items": [
                {
                    "category": "Runtime",
                    "technology": "ASP.NET Core Web API",
                    "version": ".NET 8+",
                    "rationale": "Primary HTTP API host and dependency injection container",
                    "alternatives_considered": "Minimal APIs",
                    "adr_reference": "ADR: Clean Architecture baseline",
                },
                {
                    "category": "Architecture",
                    "technology": "Clean Architecture",
                    "version": "",
                    "rationale": "Separates use cases, domain rules, infrastructure concerns, and delivery",
                    "alternatives_considered": "Layered monolith without explicit boundaries",
                    "adr_reference": "ADR: Clean Architecture baseline",
                },
                {
                    "category": "Persistence",
                    "technology": "Entity Framework Core",
                    "version": "",
                    "rationale": "DbContext, migrations, and persistence integration in Infrastructure",
                    "alternatives_considered": "Dapper",
                    "adr_reference": "ADR: Clean Architecture baseline",
                },
                {
                    "category": "Testing",
                    "technology": "xUnit / NUnit + Moq",
                    "version": "",
                    "rationale": "Supports use-case level unit tests and integration coverage",
                    "alternatives_considered": "MSTest",
                    "adr_reference": "",
                },
            ],
        }

    @staticmethod
    def _adr(template_key):
        if template_key == "mvc":
            return {
                "_template_key": template_key,
                "title": "MVC baseline",
                "status": "accepted",
                "context": (
                    "The project needs a predictable, server-rendered application structure with clear separation "
                    "between request orchestration, domain data, and UI rendering."
                ),
                "decision": (
                    "Adopt a Model View Controller structure with controllers handling request flow, models "
                    "representing domain and view data, and views responsible for rendering."
                ),
                "alternatives": [
                    {
                        "name": "Single-layer web application",
                        "pros": "Minimal upfront structure",
                        "cons": "Controllers and templates become harder to maintain as the app grows",
                    }
                ],
                "consequences": (
                    "The codebase starts with more explicit structure, but user flows, screen rendering, and "
                    "form handling are easier to reason about and test."
                ),
                "related_adrs": [],
            }
        return {
            "_template_key": template_key,
            "title": "Clean Architecture baseline",
            "status": "accepted",
            "context": (
                "The project needs a scalable ASP.NET Core structure that keeps business rules isolated "
                "from frameworks and persistence details."
            ),
            "decision": (
                "Adopt a Clean Architecture layout with Domain, Application, Infrastructure, and API "
                "projects, enforcing inward dependencies."
            ),
            "alternatives": [
                {
                    "name": "Single project Web API",
                    "pros": "Fastest initial setup",
                    "cons": "Business logic and infrastructure concerns tend to mix over time",
                }
            ],
            "consequences": (
                "There is more upfront structure, but testing and long-term maintainability improve as the "
                "solution grows."
            ),
            "related_adrs": [],
        }

    @staticmethod
    def _architecture_diagram():
        return {
            "_template_key": "aspnetcore_clean_architecture",
            "nodes": [
                {
                    "id": "api",
                    "type": "component",
                    "position": {"x": 40, "y": 40},
                    "data": {"label": "API"},
                },
                {
                    "id": "application",
                    "type": "component",
                    "position": {"x": 300, "y": 40},
                    "data": {"label": "Application"},
                },
                {
                    "id": "domain",
                    "type": "component",
                    "position": {"x": 560, "y": 40},
                    "data": {"label": "Domain"},
                },
                {
                    "id": "infrastructure",
                    "type": "component",
                    "position": {"x": 300, "y": 220},
                    "data": {"label": "Infrastructure"},
                },
            ],
            "edges": [
                {"id": "api-application", "source": "api", "target": "application", "label": "Calls use cases"},
                {"id": "application-domain", "source": "application", "target": "domain", "label": "Business rules"},
                {"id": "infrastructure-application", "source": "infrastructure", "target": "application", "label": "Implements interfaces"},
                {"id": "infrastructure-domain", "source": "infrastructure", "target": "domain", "label": "Persists entities"},
            ],
        }

    @staticmethod
    def _mvc_architecture_diagram():
        return {
            "_template_key": "mvc",
            "nodes": [
                {
                    "id": "browser",
                    "type": "component",
                    "position": {"x": 40, "y": 120},
                    "data": {"label": "Browser"},
                },
                {
                    "id": "controllers",
                    "type": "component",
                    "position": {"x": 260, "y": 120},
                    "data": {"label": "Controllers"},
                },
                {
                    "id": "models",
                    "type": "component",
                    "position": {"x": 500, "y": 40},
                    "data": {"label": "Models"},
                },
                {
                    "id": "views",
                    "type": "component",
                    "position": {"x": 500, "y": 200},
                    "data": {"label": "Views"},
                },
                {
                    "id": "services",
                    "type": "component",
                    "position": {"x": 740, "y": 120},
                    "data": {"label": "Services / Persistence"},
                },
            ],
            "edges": [
                {"id": "browser-controllers", "source": "browser", "target": "controllers", "label": "Requests"},
                {"id": "controllers-models", "source": "controllers", "target": "models", "label": "Shapes data"},
                {"id": "controllers-views", "source": "controllers", "target": "views", "label": "Chooses view"},
                {"id": "controllers-services", "source": "controllers", "target": "services", "label": "Uses services"},
            ],
        }

    @staticmethod
    def get_fixed_folder_structure(project_name, template_key="aspnetcore_clean_architecture"):
        safe_name = project_name or "MyApp"
        if template_key == "mvc":
            return [
                {
                    "path": safe_name,
                    "kind": "solution",
                    "purpose": "Application root for the MVC project",
                    "is_fixed": True,
                },
                {
                    "path": "Controllers/",
                    "kind": "folder",
                    "purpose": "Request handlers and navigation flow",
                    "is_fixed": True,
                },
                {
                    "path": "Controllers/HomeController",
                    "kind": "file",
                    "purpose": "Starter controller for the main entry flow",
                    "is_fixed": True,
                },
                {
                    "path": "Models/",
                    "kind": "folder",
                    "purpose": "Domain models and view models",
                    "is_fixed": True,
                },
                {
                    "path": "Models/ViewModels/",
                    "kind": "folder",
                    "purpose": "Models tailored to view rendering needs",
                    "is_fixed": True,
                },
                {
                    "path": "Views/",
                    "kind": "folder",
                    "purpose": "Templates rendered by controllers",
                    "is_fixed": True,
                },
                {
                    "path": "Views/Shared/",
                    "kind": "folder",
                    "purpose": "Shared layouts, partials, and UI fragments",
                    "is_fixed": True,
                },
                {
                    "path": "Views/Home/",
                    "kind": "folder",
                    "purpose": "Views owned by HomeController",
                    "is_fixed": True,
                },
                {
                    "path": "Services/",
                    "kind": "folder",
                    "purpose": "Business services and orchestration helpers",
                    "is_fixed": True,
                },
                {
                    "path": "Data/",
                    "kind": "folder",
                    "purpose": "Persistence and repository concerns",
                    "is_fixed": True,
                },
                {
                    "path": "wwwroot/",
                    "kind": "folder",
                    "purpose": "Static assets such as CSS, JS, and images",
                    "is_fixed": True,
                },
                {
                    "path": "wwwroot/css/",
                    "kind": "folder",
                    "purpose": "Application stylesheets",
                    "is_fixed": True,
                },
                {
                    "path": "wwwroot/js/",
                    "kind": "folder",
                    "purpose": "Page-level and shared scripts",
                    "is_fixed": True,
                },
                {
                    "path": "Tests/",
                    "kind": "folder",
                    "purpose": "Tests for controllers, services, and rendered flows",
                    "is_fixed": True,
                },
            ]
        return [
            {
                "path": f"{safe_name}.slnx",
                "kind": "solution",
                "purpose": "Solution file aligned with the CleanArchitecture template layout",
                "is_fixed": True,
            },
            {
                "path": ".github/",
                "kind": "folder",
                "purpose": "GitHub automation and CI workflows",
                "is_fixed": True,
            },
            {
                "path": ".github/workflows/",
                "kind": "folder",
                "purpose": "Build and validation pipelines",
                "is_fixed": True,
            },
            {
                "path": "build/",
                "kind": "folder",
                "purpose": "Build scripts and supporting automation",
                "is_fixed": True,
            },
            {
                "path": "docs/",
                "kind": "folder",
                "purpose": "Project documentation root",
                "is_fixed": True,
            },
            {
                "path": "docs/decisions/",
                "kind": "folder",
                "purpose": "Architecture Decision Records",
                "is_fixed": True,
            },
            {
                "path": "src/",
                "kind": "folder",
                "purpose": "Application source root",
                "is_fixed": True,
            },
            {
                "path": "src/AppHost/",
                "kind": "folder",
                "purpose": "Aspire host project used to run and compose the solution",
                "is_fixed": True,
            },
            {
                "path": "src/ServiceDefaults/",
                "kind": "folder",
                "purpose": "Shared Aspire and service defaults",
                "is_fixed": True,
            },
            {
                "path": "src/Shared/",
                "kind": "folder",
                "purpose": "Shared cross-project contracts and reusable building blocks",
                "is_fixed": True,
            },
            {
                "path": "src/Shared/Models/",
                "kind": "folder",
                "purpose": "Shared DTOs and supporting models",
                "is_fixed": True,
            },
            {
                "path": "src/Application/",
                "kind": "folder",
                "purpose": "Use cases, validation, mappings, and application boundaries",
                "is_fixed": True,
            },
            {
                "path": "src/Application/Common/",
                "kind": "folder",
                "purpose": "Cross-cutting application abstractions and behaviors",
                "is_fixed": True,
            },
            {
                "path": "src/Application/Common/Behaviours/",
                "kind": "folder",
                "purpose": "Pipeline behaviors such as validation and logging",
                "is_fixed": True,
            },
            {
                "path": "src/Application/Common/Exceptions/",
                "kind": "folder",
                "purpose": "Application-specific exception types",
                "is_fixed": True,
            },
            {
                "path": "src/Application/Common/Interfaces/",
                "kind": "folder",
                "purpose": "Interfaces implemented by Infrastructure",
                "is_fixed": True,
            },
            {
                "path": "src/Application/Common/Mappings/",
                "kind": "folder",
                "purpose": "Mapping profiles and shared projection helpers",
                "is_fixed": True,
            },
            {
                "path": "src/Application/Common/Models/",
                "kind": "folder",
                "purpose": "Application-level models and wrappers",
                "is_fixed": True,
            },
            {
                "path": "src/Application/TodoLists/",
                "kind": "folder",
                "purpose": "Example feature slice following the template style",
                "is_fixed": True,
            },
            {
                "path": "src/Application/TodoLists/Commands/",
                "kind": "folder",
                "purpose": "Commands that mutate TodoLists state",
                "is_fixed": True,
            },
            {
                "path": "src/Application/TodoLists/Queries/",
                "kind": "folder",
                "purpose": "Queries that read TodoLists state",
                "is_fixed": True,
            },
            {
                "path": "src/Application/TodoItems/",
                "kind": "folder",
                "purpose": "Example item-focused feature slice",
                "is_fixed": True,
            },
            {
                "path": "src/Application/TodoItems/Commands/",
                "kind": "folder",
                "purpose": "Commands that mutate TodoItems state",
                "is_fixed": True,
            },
            {
                "path": "src/Domain/",
                "kind": "folder",
                "purpose": "Core domain model and business rules",
                "is_fixed": True,
            },
            {
                "path": "src/Domain/Common/",
                "kind": "folder",
                "purpose": "Base domain abstractions",
                "is_fixed": True,
            },
            {
                "path": "src/Domain/Entities/",
                "kind": "folder",
                "purpose": "Entities, value objects, enums, and core business rules",
                "is_fixed": True,
            },
            {
                "path": "src/Domain/Events/",
                "kind": "folder",
                "purpose": "Domain events emitted by aggregate changes",
                "is_fixed": True,
            },
            {
                "path": "src/Domain/Enums/",
                "kind": "folder",
                "purpose": "Domain enums and constants",
                "is_fixed": True,
            },
            {
                "path": "src/Domain/ValueObjects/",
                "kind": "folder",
                "purpose": "Immutable value object types",
                "is_fixed": True,
            },
            {
                "path": "src/Infrastructure/",
                "kind": "folder",
                "purpose": "EF Core, repositories, external adapters, and persistence",
                "is_fixed": True,
            },
            {
                "path": "src/Infrastructure/Data/",
                "kind": "folder",
                "purpose": "DbContext, interceptors, and persistence setup",
                "is_fixed": True,
            },
            {
                "path": "src/Infrastructure/Data/Interceptors/",
                "kind": "folder",
                "purpose": "EF Core save and query interceptors",
                "is_fixed": True,
            },
            {
                "path": "src/Infrastructure/Identity/",
                "kind": "folder",
                "purpose": "Identity and authentication integration",
                "is_fixed": True,
            },
            {
                "path": "src/Infrastructure/Services/",
                "kind": "folder",
                "purpose": "Concrete service implementations for application interfaces",
                "is_fixed": True,
            },
            {
                "path": "src/Web/",
                "kind": "folder",
                "purpose": "ASP.NET Core presentation layer used by the template",
                "is_fixed": True,
            },
            {
                "path": "src/Web/Endpoints/",
                "kind": "folder",
                "purpose": "HTTP endpoints grouped by feature",
                "is_fixed": True,
            },
            {
                "path": "src/Web/Infrastructure/",
                "kind": "folder",
                "purpose": "Web project bootstrapping and middleware configuration",
                "is_fixed": True,
            },
            {
                "path": "src/Web/Resources/",
                "kind": "folder",
                "purpose": "Localization and presentation resources",
                "is_fixed": True,
            },
            {
                "path": "tests/",
                "kind": "folder",
                "purpose": "Automated test projects",
                "is_fixed": True,
            },
            {
                "path": "tests/Application.UnitTests/",
                "kind": "folder",
                "purpose": "Unit tests for application services and handlers",
                "is_fixed": True,
            },
            {
                "path": "tests/Application.UnitTests/Common/",
                "kind": "folder",
                "purpose": "Shared test fixtures and helpers",
                "is_fixed": True,
            },
            {
                "path": "tests/Application.FunctionalTests/",
                "kind": "folder",
                "purpose": "Feature-level functional tests mirroring use cases",
                "is_fixed": True,
            },
            {
                "path": "tests/Application.FunctionalTests/TodoLists/",
                "kind": "folder",
                "purpose": "Functional coverage for TodoLists flows",
                "is_fixed": True,
            },
            {
                "path": "tests/Application.FunctionalTests/TodoItems/",
                "kind": "folder",
                "purpose": "Functional coverage for TodoItems flows",
                "is_fixed": True,
            },
            {
                "path": "tests/Application.IntegrationTests/",
                "kind": "folder",
                "purpose": "End-to-end persistence and API integration tests",
                "is_fixed": True,
            },
        ]

    @staticmethod
    def merge_folder_structure_items(project_template_key, project_name, custom_items=None):
        merged = []
        if project_template_key in {"aspnetcore_clean_architecture", "mvc"}:
            merged.extend(ProjectTemplateService.get_fixed_folder_structure(project_name, project_template_key))

        for item in custom_items or []:
            path = (item.get("path") or "").strip()
            if not path:
                continue
            merged.append({
                "path": path,
                "kind": (item.get("kind") or "folder").strip() or "folder",
                "purpose": (item.get("purpose") or "").strip(),
                "is_fixed": False,
            })

        return merged

    @staticmethod
    def _folder_structure(project_name, template_key):
        project_display = project_name or "Project"
        return {
            "_template_key": template_key,
            "title": "Folder Structure",
            "root_name": project_display if template_key == "mvc" else f"{project_display}.slnx",
            "notes": (
                "The core MVC layout is fixed for this template. Add feature-specific controllers, views, models, or assets as custom entries."
                if template_key == "mvc" else
                "The core clean architecture layout is fixed for this template. "
                "Add feature folders, shared contracts, or deployment assets as custom entries."
            ),
            "items": ProjectTemplateService.merge_folder_structure_items(
                project_template_key=template_key,
                project_name=project_name,
                custom_items=[],
            ),
        }

    @staticmethod
    def seed_project_template(project, template_key):
        normalized = ProjectTemplateService.normalize_template_key(template_key)
        if normalized == DEFAULT_TEMPLATE_KEY:
            return False

        if normalized in {"aspnetcore_clean_architecture", "mvc"}:
            created_any = False
            existing_documents, template_docs = ProjectTemplateService._template_documents(project.id)

            if "tech_stack" not in template_docs:
                DocumentService.create(
                    project_id=project.id,
                    doc_type="tech_stack",
                    data=ProjectTemplateService._tech_stack(normalized),
                )
                created_any = True

            if "project_plan" not in template_docs:
                DocumentService.create(
                    project_id=project.id,
                    doc_type="project_plan",
                    data=ProjectTemplateService._project_plan(project.name, project.description, normalized),
                )
                created_any = True

            if "adr" not in template_docs:
                DocumentService.create(
                    project_id=project.id,
                    doc_type="adr",
                    data=ProjectTemplateService._adr(normalized),
                )
                created_any = True

            if "folder_structure" not in template_docs:
                DocumentService.create(
                    project_id=project.id,
                    doc_type="folder_structure",
                    data=ProjectTemplateService._folder_structure(project.name, normalized),
                )
                created_any = True

            diagrams = DiagramService.get_all_for_project(project.id)
            diagram_name = "MVC Overview" if normalized == "mvc" else "Clean Architecture Overview"
            diagram_data = (
                ProjectTemplateService._mvc_architecture_diagram()
                if normalized == "mvc"
                else ProjectTemplateService._architecture_diagram()
            )
            if not any(
                d.name == diagram_name
                and _template_marker(getattr(d, "data", None)) == normalized
                for d in diagrams
            ):
                DiagramService.create(
                    project_id=project.id,
                    diagram_type="architecture",
                    name=diagram_name,
                    data=diagram_data,
                )
                created_any = True

            return created_any

        return False

    @staticmethod
    def ensure_project_template(project, documents=None):
        template_key = ProjectTemplateService.resolve_template_key(project=project, documents=documents)
        if template_key == DEFAULT_TEMPLATE_KEY:
            return False
        return ProjectTemplateService.seed_project_template(project, template_key)

    @staticmethod
    def as_export_payload(project=None, documents=None):
        template = ProjectTemplateService.resolve_template(project=project, documents=documents)
        return {
            "key": template["key"],
            "label": template["label"],
            "summary": template["summary"],
            "focus": template["focus"],
            "layers": list(template["layers"]),
            "starter_outputs": list(template["starter_outputs"]),
        }

    @staticmethod
    def as_view_model(project=None, documents=None):
        return SimpleNamespace(**ProjectTemplateService.as_export_payload(project=project, documents=documents))
