import json
import logging

import requests
from flask import current_app

logger = logging.getLogger(__name__)


class StitchService:
    """Client for Google Stitch MCP API (JSON-RPC over HTTP)."""

    @staticmethod
    def _call_tool(tool_name, arguments):
        """Call a Stitch MCP tool via JSON-RPC."""
        url = current_app.config["STITCH_API_URL"]
        token = current_app.config["STITCH_AUTH_TOKEN"]
        gcp_project = current_app.config["STITCH_GCP_PROJECT"]

        if not token:
            raise RuntimeError("STITCH_AUTH_TOKEN not configured")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "softwaredesign/1.0 (+https://example.com/softwaredesign)",
            "Connection": "close",
        }
        if gcp_project:
            headers["X-Goog-User-Project"] = gcp_project

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=300)
            resp.raise_for_status()
            result = resp.json()
        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            response_text = ""
            if exc.response is not None and exc.response.text:
                response_text = exc.response.text.strip()[:1000]
            message = f"Stitch HTTP error {status_code or 'unknown'}."
            if response_text:
                message += f" Response: {response_text}"
            logger.warning("Stitch HTTP error for %s: %s", tool_name, message)
            raise RuntimeError(message) from exc
        except requests.exceptions.Timeout as exc:
            logger.warning("Stitch timeout for %s", tool_name)
            raise RuntimeError(
                "Stitch request timed out before the service returned a response."
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            logger.warning("Stitch connection error for %s: %s", tool_name, exc)
            raise RuntimeError(
                "Stitch closed the connection before sending a response."
            ) from exc
        except requests.exceptions.RequestException as exc:
            logger.warning("Stitch request error for %s: %s", tool_name, exc)
            raise RuntimeError(f"Stitch request failed: {exc.__class__.__name__}: {exc}") from exc
        except ValueError as exc:
            response_text = resp.text.strip()[:1000] if resp.text else ""
            message = "Stitch returned a non-JSON response."
            if response_text:
                message += f" Response: {response_text}"
            logger.warning("Stitch invalid JSON for %s", tool_name)
            raise RuntimeError(message) from exc

        if "error" in result:
            logger.warning("Stitch API error for %s: %s", tool_name, result["error"])
            raise RuntimeError(f"Stitch API error: {result['error']}")

        return result.get("result", {})

    @staticmethod
    def create_project(title=""):
        args = {}
        if title:
            args["title"] = title
        return StitchService._call_tool("create_project", args)

    @staticmethod
    def list_projects():
        return StitchService._call_tool("list_projects", {})

    @staticmethod
    def get_project(project_name):
        return StitchService._call_tool("get_project", {"name": project_name})

    @staticmethod
    def generate_screen(project_id, prompt, device_type="DESKTOP", model_id="GEMINI_3_1_PRO"):
        args = {
            "projectId": project_id,
            "prompt": prompt,
        }
        if device_type:
            args["deviceType"] = device_type
        if model_id:
            args["modelId"] = model_id
        return StitchService._call_tool("generate_screen_from_text", args)

    @staticmethod
    def get_screen(project_id, screen_id):
        name = f"projects/{project_id}/screens/{screen_id}"
        return StitchService._call_tool("get_screen", {
            "name": name,
            "projectId": project_id,
            "screenId": screen_id,
        })

    @staticmethod
    def list_screens(project_id):
        return StitchService._call_tool("list_screens", {"projectId": project_id})

    @staticmethod
    def edit_screens(project_id, screen_ids, prompt, device_type="DESKTOP", model_id="GEMINI_3_1_PRO"):
        args = {
            "projectId": project_id,
            "selectedScreenIds": screen_ids,
            "prompt": prompt,
        }
        if device_type:
            args["deviceType"] = device_type
        if model_id:
            args["modelId"] = model_id
        return StitchService._call_tool("edit_screens", args)

    @staticmethod
    def generate_variants(project_id, screen_ids, prompt, variant_count=3,
                          creative_range="EXPLORE", aspects=None):
        args = {
            "projectId": project_id,
            "selectedScreenIds": screen_ids,
            "prompt": prompt,
            "variantOptions": {
                "variantCount": variant_count,
                "creativeRange": creative_range,
            },
        }
        if aspects:
            args["variantOptions"]["aspects"] = aspects
        return StitchService._call_tool("generate_variants", args)

    @staticmethod
    def create_design_system(project_id, design_system):
        args = {"designSystem": design_system}
        if project_id:
            args["projectId"] = project_id
        return StitchService._call_tool("create_design_system", args)

    @staticmethod
    def update_design_system(project_id, asset_name, design_system):
        return StitchService._call_tool("update_design_system", {
            "projectId": project_id,
            "name": asset_name,
            "designSystem": design_system,
        })

    @staticmethod
    def list_design_systems(project_id=""):
        args = {}
        if project_id:
            args["projectId"] = project_id
        return StitchService._call_tool("list_design_systems", args)

    @staticmethod
    def apply_design_system(project_id, screen_instances, asset_id):
        return StitchService._call_tool("apply_design_system", {
            "projectId": project_id,
            "selectedScreenInstances": screen_instances,
            "assetId": asset_id,
        })
