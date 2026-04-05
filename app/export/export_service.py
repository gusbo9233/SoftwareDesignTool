from app.services.project_service import ProjectService
from app.services.document_service import DocumentService
from app.services.diagram_service import DiagramService
from app.services.api_endpoint_service import APIEndpointService
from app.services.traceability_service import TraceabilityService
from app.services.test_result_service import TestResultService
from app.services.git_connection_service import GitConnectionService


class ExportService:
    @staticmethod
    def export_json(project_id):
        """Export all project artifacts as a single JSON-serializable dict."""
        project = ProjectService.get(project_id)
        if not project:
            return None

        documents = DocumentService.get_all_for_project(project_id)
        diagrams = DiagramService.get_all_for_project(project_id)
        endpoints = APIEndpointService.get_all_for_project(project_id)

        user_stories = []
        requirements = []
        project_plans = []
        test_plans = []
        adrs = []
        tech_stacks = []
        nfrs = []
        risk_registers = []
        domain_models = []
        acceptance_tests = []
        external_resources = []
        research_docs = []

        for doc in documents:
            data = doc.data or {}
            if doc.type == "user_story":
                user_stories.append({
                    "id": doc.id,
                    "as_a": data.get("user_type", ""),
                    "i_want_to": data.get("action", ""),
                    "so_that": data.get("benefit", ""),
                    "priority": data.get("priority", ""),
                    "status": data.get("status", ""),
                    "acceptance_criteria": data.get("acceptance_criteria", []),
                })
            elif doc.type == "requirement":
                requirements.append({
                    "id": doc.id,
                    "title": data.get("title", ""),
                    "description": data.get("description", ""),
                    "type": data.get("type", ""),
                    "category": data.get("category", ""),
                    "priority": data.get("priority", ""),
                    "status": data.get("status", ""),
                    "rationale": data.get("rationale", ""),
                })
            elif doc.type == "project_plan":
                project_plans.append({
                    "id": doc.id,
                    "project_name": data.get("project_name", ""),
                    "project_description": data.get("project_description", ""),
                    "goals": data.get("goals", []),
                    "in_scope": data.get("in_scope", []),
                    "out_scope": data.get("out_scope", []),
                    "milestones": data.get("milestones", []),
                    "risks": data.get("risks", []),
                })
            elif doc.type == "test_plan":
                test_plans.append({
                    "id": doc.id,
                    "test_scope": data.get("test_scope", ""),
                    "test_strategy": data.get("test_strategy", ""),
                    "test_cases": data.get("test_cases", []),
                    "entry_criteria": data.get("entry_criteria", ""),
                    "exit_criteria": data.get("exit_criteria", ""),
                    "environment": data.get("environment", ""),
                })
            elif doc.type == "adr":
                adrs.append({
                    "id": doc.id,
                    "title": data.get("title", ""),
                    "status": data.get("status", ""),
                    "context": data.get("context", ""),
                    "decision": data.get("decision", ""),
                    "alternatives": data.get("alternatives", []),
                    "consequences": data.get("consequences", ""),
                    "related_adrs": data.get("related_adrs", []),
                })
            elif doc.type == "tech_stack":
                tech_stacks.append({
                    "id": doc.id,
                    "items": data.get("items", []),
                })
            elif doc.type == "nfr":
                nfrs.append({
                    "id": doc.id,
                    "title": data.get("title", ""),
                    "category": data.get("category", ""),
                    "description": data.get("description", ""),
                    "rationale": data.get("rationale", ""),
                    "priority": data.get("priority", ""),
                    "status": data.get("status", ""),
                    "verification_method": data.get("verification_method", ""),
                })
            elif doc.type == "risk_register":
                risk_registers.append({
                    "id": doc.id,
                    "items": data.get("items", []),
                })
            elif doc.type == "domain_model":
                domain_models.append({
                    "id": doc.id,
                    "bounded_context_name": data.get("bounded_context_name", ""),
                    "bounded_context_description": data.get("bounded_context_description", ""),
                    "entities": data.get("entities", []),
                    "glossary": data.get("glossary", []),
                    "business_rules": data.get("business_rules", []),
                    "external_systems": data.get("external_systems", []),
                })
            elif doc.type == "acceptance_test":
                acceptance_tests.append({
                    "id": doc.id,
                    "title": data.get("title", ""),
                    "requirement_reference": data.get("requirement_reference", ""),
                    "user_story_reference": data.get("user_story_reference", ""),
                    "preconditions": data.get("preconditions", ""),
                    "steps": data.get("steps", []),
                    "expected_result": data.get("expected_result", ""),
                    "status": data.get("status", ""),
                    "notes": data.get("notes", ""),
                })
            elif doc.type == "external_resource":
                external_resources.append({
                    "id": doc.id,
                    "name": data.get("name", ""),
                    "type": data.get("type", ""),
                    "url": data.get("url", ""),
                    "description": data.get("description", ""),
                    "authentication": data.get("authentication", ""),
                    "notes": data.get("notes", ""),
                })
            elif doc.type == "research":
                research_docs.append({
                    "id": doc.id,
                    "title": data.get("title", ""),
                    "body": data.get("body", ""),
                    "tags": data.get("tags", ""),
                })

        diagram_list = []
        for d in diagrams:
            diagram_data = d.data or {}
            diagram_list.append({
                "id": d.id,
                "type": d.type,
                "name": d.name,
                "nodes": diagram_data.get("nodes", []),
                "edges": diagram_data.get("edges", []),
            })

        api_list = []
        for ep in endpoints:
            api_list.append({
                "id": ep.id,
                "path": ep.path,
                "method": ep.method,
                "description": ep.description or "",
                "parameters": (ep.request_schema or {}).get("parameters", []),
                "request_body": (ep.request_schema or {}).get("body", ""),
                "response_body": (ep.response_schema or {}).get("body", ""),
                "status_codes": (ep.response_schema or {}).get("status_codes", []),
            })

        traceability = TraceabilityService.get_traceability_map(project_id)

        # CI status from GitHub integration
        ci_status = None
        git_conn = GitConnectionService.get_for_project(project_id)
        if git_conn:
            runs = TestResultService.get_runs_for_project(project_id, limit=1)
            if runs:
                latest = runs[0]
                ci_status = {
                    "repo": f"{git_conn.repo_owner}/{git_conn.repo_name}",
                    "branch": latest.branch,
                    "last_run_conclusion": latest.conclusion,
                    "last_run_date": str(latest.created_at) if latest.created_at else None,
                    "total_tests": latest.total_tests,
                    "passed": latest.passed,
                    "failed": latest.failed,
                    "skipped": latest.skipped,
                }

        return {
            "project": project.name,
            "description": project.description or "",
            "requirements": requirements,
            "nfrs": nfrs,
            "user_stories": user_stories,
            "adrs": adrs,
            "tech_stack": tech_stacks,
            "risk_register": risk_registers,
            "domain_models": domain_models,
            "acceptance_tests": acceptance_tests,
            "external_resources": external_resources,
            "research": research_docs,
            "project_plans": project_plans,
            "test_plans": test_plans,
            "diagrams": diagram_list,
            "api_endpoints": api_list,
            "traceability": traceability,
            "ci_status": ci_status,
        }

    @staticmethod
    def export_markdown(project_id):
        """Export all project artifacts as a Markdown string."""
        data = ExportService.export_json(project_id)
        if data is None:
            return None

        lines = []
        lines.append(f"# {data['project']}")
        if data["description"]:
            lines.append(f"\n{data['description']}")

        # Requirements
        if data["requirements"]:
            lines.append("\n## Requirements\n")
            for req in data["requirements"]:
                lines.append(f"### {req['title']}")
                lines.append(f"- **Type:** {req['type']}")
                lines.append(f"- **Category:** {req['category']}" if req["category"] else "")
                lines.append(f"- **Priority:** {req['priority']}")
                lines.append(f"- **Status:** {req['status']}")
                lines.append(f"\n{req['description']}")
                if req["rationale"]:
                    lines.append(f"\n**Rationale:** {req['rationale']}")
                lines.append("")

        # Non-Functional Requirements
        if data["nfrs"]:
            lines.append("\n## Non-Functional Requirements\n")
            for nfr in data["nfrs"]:
                lines.append(f"### {nfr['title']}")
                lines.append(f"- **Category:** {nfr['category']}")
                lines.append(f"- **Priority:** {nfr['priority']}")
                lines.append(f"- **Status:** {nfr['status']}")
                if nfr["verification_method"]:
                    lines.append(f"- **Verification:** {nfr['verification_method']}")
                lines.append(f"\n{nfr['description']}")
                if nfr["rationale"]:
                    lines.append(f"\n**Rationale:** {nfr['rationale']}")
                lines.append("")

        # User Stories
        if data["user_stories"]:
            lines.append("\n## User Stories\n")
            for story in data["user_stories"]:
                lines.append(f"### User Story")
                lines.append(f"\n> As a **{story['as_a']}**, I want to **{story['i_want_to']}** so that **{story['so_that']}**.\n")
                lines.append(f"- **Priority:** {story['priority']}")
                lines.append(f"- **Status:** {story['status']}")
                if story["acceptance_criteria"]:
                    lines.append("\n**Acceptance Criteria:**")
                    for ac in story["acceptance_criteria"]:
                        lines.append(f"- [ ] {ac}")
                lines.append("")

        # Architecture Decision Records
        if data["adrs"]:
            lines.append("\n## Architecture Decision Records\n")
            for adr in data["adrs"]:
                lines.append(f"### ADR: {adr['title']}")
                lines.append(f"- **Status:** {adr['status']}")
                lines.append(f"\n**Context:** {adr['context']}")
                lines.append(f"\n**Decision:** {adr['decision']}")
                if adr["alternatives"]:
                    lines.append("\n**Alternatives Considered:**\n")
                    lines.append("| Alternative | Pros | Cons |")
                    lines.append("|---|---|---|")
                    for alt in adr["alternatives"]:
                        lines.append(f"| {alt.get('name', '')} | {alt.get('pros', '')} | {alt.get('cons', '')} |")
                if adr["consequences"]:
                    lines.append(f"\n**Consequences:** {adr['consequences']}")
                if adr["related_adrs"]:
                    lines.append(f"\n**Related ADRs:** {', '.join(adr['related_adrs'])}")
                lines.append("")

        # Technology Stack
        if data["tech_stack"]:
            for ts in data["tech_stack"]:
                if ts["items"]:
                    lines.append("\n## Technology Stack\n")
                    lines.append("| Category | Technology | Version | Rationale | Alternatives | ADR Ref |")
                    lines.append("|---|---|---|---|---|---|")
                    for item in ts["items"]:
                        lines.append(
                            f"| {item.get('category', '')} | {item.get('technology', '')} | "
                            f"{item.get('version', '')} | {item.get('rationale', '')} | "
                            f"{item.get('alternatives_considered', '')} | {item.get('adr_reference', '')} |"
                        )
                    lines.append("")

        # Risk Register
        if data["risk_register"]:
            for rr in data["risk_register"]:
                if rr["items"]:
                    lines.append("\n## Risk Register\n")
                    lines.append("| Title | Category | Likelihood | Impact | Status | Owner | Mitigation |")
                    lines.append("|---|---|---|---|---|---|---|")
                    for risk in rr["items"]:
                        lines.append(
                            f"| {risk.get('title', '')} | {risk.get('category', '')} | "
                            f"{risk.get('likelihood', '')} | {risk.get('impact', '')} | "
                            f"{risk.get('status', '')} | {risk.get('owner', '')} | {risk.get('mitigation', '')} |"
                        )
                    lines.append("")

        # Domain Models
        if data["domain_models"]:
            lines.append("\n## Domain Models\n")
            for dm in data["domain_models"]:
                lines.append(f"### {dm['bounded_context_name']}")
                if dm["bounded_context_description"]:
                    lines.append(f"\n{dm['bounded_context_description']}")
                if dm["entities"]:
                    lines.append("\n**Entities:**\n")
                    lines.append("| Name | Description | Key Attributes |")
                    lines.append("|---|---|---|")
                    for entity in dm["entities"]:
                        lines.append(f"| {entity.get('name', '')} | {entity.get('description', '')} | {entity.get('key_attributes', '')} |")
                if dm["glossary"]:
                    lines.append("\n**Domain Language:**\n")
                    lines.append("| Term | Definition |")
                    lines.append("|---|---|")
                    for term in dm["glossary"]:
                        lines.append(f"| {term.get('term', '')} | {term.get('definition', '')} |")
                if dm["business_rules"]:
                    lines.append("\n**Business Rules:**")
                    for i, rule in enumerate(dm["business_rules"], 1):
                        lines.append(f"{i}. {rule}")
                if dm["external_systems"]:
                    lines.append("\n**External Systems:**\n")
                    lines.append("| System | Type | Integration | Owner |")
                    lines.append("|---|---|---|---|")
                    for sys in dm["external_systems"]:
                        lines.append(f"| {sys.get('name', '')} | {sys.get('system_type', '')} | {sys.get('integration_description', '')} | {sys.get('owner', '')} |")
                lines.append("")

        # Acceptance Tests
        if data["acceptance_tests"]:
            lines.append("\n## Acceptance Tests\n")
            for at in data["acceptance_tests"]:
                lines.append(f"### {at['title']}")
                lines.append(f"- **Status:** {at['status']}")
                if at["requirement_reference"]:
                    lines.append(f"- **Requirement:** {at['requirement_reference']}")
                if at["user_story_reference"]:
                    lines.append(f"- **User Story:** {at['user_story_reference']}")
                if at["preconditions"]:
                    lines.append(f"\n**Preconditions:** {at['preconditions']}")
                if at["steps"]:
                    lines.append("\n**Steps:**")
                    for i, step in enumerate(at["steps"], 1):
                        lines.append(f"{i}. {step}")
                lines.append(f"\n**Expected Result:** {at['expected_result']}")
                if at["notes"]:
                    lines.append(f"\n**Notes:** {at['notes']}")
                lines.append("")

        # External Resources
        if data["external_resources"]:
            lines.append("\n## External Resources\n")
            lines.append("| Name | Type | URL | Authentication | Description |")
            lines.append("|---|---|---|---|---|")
            for res in data["external_resources"]:
                lines.append(
                    f"| {res['name']} | {res['type']} | {res['url']} | "
                    f"{res['authentication']} | {res['description']} |"
                )
            lines.append("")

        # Research Documents
        if data["research"]:
            lines.append("\n## Research Documents\n")
            for doc in data["research"]:
                lines.append(f"### {doc['title']}")
                if doc["tags"]:
                    lines.append(f"*Tags: {doc['tags']}*\n")
                if doc["body"]:
                    lines.append(doc["body"])
                lines.append("")

        # Project Plans
        if data["project_plans"]:
            lines.append("\n## Project Plans\n")
            for plan in data["project_plans"]:
                lines.append(f"### {plan['project_name']}")
                if plan["project_description"]:
                    lines.append(f"\n{plan['project_description']}")
                if plan["goals"]:
                    lines.append("\n**Goals:**")
                    for i, goal in enumerate(plan["goals"], 1):
                        lines.append(f"{i}. {goal}")
                if plan["in_scope"]:
                    lines.append("\n**In Scope:**")
                    for item in plan["in_scope"]:
                        lines.append(f"- {item}")
                if plan["out_scope"]:
                    lines.append("\n**Out of Scope:**")
                    for item in plan["out_scope"]:
                        lines.append(f"- {item}")
                if plan["milestones"]:
                    lines.append("\n**Milestones:**\n")
                    lines.append("| Milestone | Target Date | Deliverables | Status |")
                    lines.append("|---|---|---|---|")
                    for m in plan["milestones"]:
                        lines.append(f"| {m.get('name', '')} | {m.get('target_date', '')} | {m.get('deliverables', '')} | {m.get('status', '')} |")
                if plan["risks"]:
                    lines.append("\n**Risks:**\n")
                    lines.append("| Risk | Likelihood | Impact | Mitigation |")
                    lines.append("|---|---|---|---|")
                    for r in plan["risks"]:
                        lines.append(f"| {r.get('description', '')} | {r.get('likelihood', '')} | {r.get('impact', '')} | {r.get('mitigation', '')} |")
                lines.append("")

        # Test Plans
        if data["test_plans"]:
            lines.append("\n## Test Plans\n")
            for tp in data["test_plans"]:
                lines.append(f"### Test Scope\n\n{tp['test_scope']}")
                if tp["test_strategy"]:
                    lines.append(f"\n**Strategy:** {tp['test_strategy']}")
                if tp["test_cases"]:
                    lines.append("\n**Test Cases:**\n")
                    lines.append("| Description | Steps | Expected Result | Status |")
                    lines.append("|---|---|---|---|")
                    for tc in tp["test_cases"]:
                        lines.append(f"| {tc.get('description', '')} | {tc.get('steps', '')} | {tc.get('expected_result', '')} | {tc.get('status', '')} |")
                if tp["entry_criteria"]:
                    lines.append(f"\n**Entry Criteria:** {tp['entry_criteria']}")
                if tp["exit_criteria"]:
                    lines.append(f"\n**Exit Criteria:** {tp['exit_criteria']}")
                if tp["environment"]:
                    lines.append(f"\n**Environment:** {tp['environment']}")
                lines.append("")

        # Diagrams
        if data["diagrams"]:
            lines.append("\n## Diagrams\n")
            for diag in data["diagrams"]:
                lines.append(f"### {diag['name']} ({diag['type']})\n")
                lines.append(f"- **Nodes:** {len(diag['nodes'])}")
                lines.append(f"- **Edges:** {len(diag['edges'])}")
                if diag["nodes"]:
                    lines.append("\n**Nodes:**")
                    for node in diag["nodes"]:
                        label = node.get("data", {}).get("label", node.get("id", ""))
                        lines.append(f"- {label} (type: {node.get('type', 'default')})")
                if diag["edges"]:
                    lines.append("\n**Edges:**")
                    for edge in diag["edges"]:
                        label = f" [{edge.get('label', '')}]" if edge.get("label") else ""
                        lines.append(f"- {edge.get('source', '')} → {edge.get('target', '')}{label}")
                lines.append("")

        # API Endpoints
        if data["api_endpoints"]:
            lines.append("\n## API Endpoints\n")
            for ep in data["api_endpoints"]:
                lines.append(f"### `{ep['method']} {ep['path']}`\n")
                if ep["description"]:
                    lines.append(f"{ep['description']}\n")
                if ep["parameters"]:
                    lines.append("**Parameters:**\n")
                    lines.append("| Name | Location | Type | Required | Description |")
                    lines.append("|---|---|---|---|---|")
                    for p in ep["parameters"]:
                        req = "Yes" if p.get("required") else "No"
                        lines.append(f"| {p.get('name', '')} | {p.get('location', '')} | {p.get('type', '')} | {req} | {p.get('description', '')} |")
                if ep["request_body"]:
                    lines.append(f"\n**Request Body:**\n```json\n{ep['request_body']}\n```")
                if ep["response_body"]:
                    lines.append(f"\n**Response Body:**\n```json\n{ep['response_body']}\n```")
                if ep["status_codes"]:
                    lines.append("\n**Status Codes:**\n")
                    for sc in ep["status_codes"]:
                        lines.append(f"- `{sc.get('code', '')}`: {sc.get('description', '')}")
                lines.append("")

        # Traceability
        if data["traceability"]:
            lines.append("\n## Traceability\n")
            lines.append("| Acceptance Test | Requirements | User Stories |")
            lines.append("|---|---|---|")
            for entry in data["traceability"]:
                req_ids = ", ".join(entry["requirement_ids"]) or "—"
                us_ids = ", ".join(entry["user_story_ids"]) or "—"
                lines.append(f"| {entry['acceptance_test_id']} | {req_ids} | {us_ids} |")
            lines.append("")

        # CI Status
        if data.get("ci_status"):
            ci = data["ci_status"]
            lines.append("\n## CI Status\n")
            lines.append(f"- **Repository:** {ci['repo']}")
            lines.append(f"- **Branch:** {ci['branch']}")
            lines.append(f"- **Last Run:** {ci['last_run_conclusion'] or 'unknown'}")
            if ci.get("last_run_date"):
                lines.append(f"- **Date:** {ci['last_run_date']}")
            if ci.get("total_tests") is not None:
                lines.append(f"- **Tests:** {ci['passed'] or 0} passed, {ci['failed'] or 0} failed, {ci['skipped'] or 0} skipped ({ci['total_tests']} total)")
            lines.append("")

        # Filter out empty strings from conditional lines
        return "\n".join(line for line in lines if line is not None)
