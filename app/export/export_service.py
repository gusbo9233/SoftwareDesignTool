from app.services.project_service import ProjectService
from app.services.document_service import DocumentService
from app.services.diagram_service import DiagramService
from app.services.api_endpoint_service import APIEndpointService


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

        return {
            "project": project.name,
            "description": project.description or "",
            "requirements": requirements,
            "user_stories": user_stories,
            "project_plans": project_plans,
            "test_plans": test_plans,
            "diagrams": diagram_list,
            "api_endpoints": api_list,
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

        # Filter out empty strings from conditional lines
        return "\n".join(line for line in lines if line is not None)
