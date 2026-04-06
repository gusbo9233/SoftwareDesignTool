import json
import os
import subprocess
import threading

from flask import current_app


class StitchService:
    """SDK-backed client for Stitch operations via a local Node bridge."""

    _call_lock = threading.Lock()

    @staticmethod
    def _bridge_command(tool_name):
        node_binary = current_app.config["STITCH_NODE_BINARY"]
        bridge_script = current_app.config["STITCH_BRIDGE_SCRIPT"]
        if not os.path.exists(bridge_script):
            raise RuntimeError(f"Stitch bridge script not found: {bridge_script}")
        return [node_binary, bridge_script, tool_name]

    @staticmethod
    def _bridge_env():
        env = os.environ.copy()
        for key in (
            "STITCH_API_KEY",
            "STITCH_ACCESS_TOKEN",
            "GOOGLE_CLOUD_PROJECT",
            "STITCH_API_URL",
            "STITCH_HOST",
        ):
            config_key = {
                "STITCH_API_KEY": "STITCH_API_KEY",
                "STITCH_ACCESS_TOKEN": "STITCH_AUTH_TOKEN",
                "GOOGLE_CLOUD_PROJECT": "STITCH_GCP_PROJECT",
                "STITCH_API_URL": "STITCH_API_URL",
                "STITCH_HOST": "STITCH_API_URL",
            }[key]
            value = current_app.config.get(config_key, "")
            if value:
                env[key] = value
        return env

    @staticmethod
    def _parse_bridge_output(raw_output):
        raw_output = (raw_output or "").strip()
        if not raw_output:
            return {}

        try:
            return json.loads(raw_output)
        except json.JSONDecodeError:
            pass

        for line in reversed(raw_output.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue

        raise RuntimeError(raw_output)

    @staticmethod
    def _call_tool(tool_name, arguments):
        command = StitchService._bridge_command(tool_name)
        payload = json.dumps(arguments or {})

        with StitchService._call_lock:
            try:
                completed = subprocess.run(
                    command,
                    input=payload,
                    capture_output=True,
                    text=True,
                    timeout=330,
                    env=StitchService._bridge_env(),
                    cwd=os.path.dirname(current_app.config["STITCH_BRIDGE_SCRIPT"]),
                )
            except FileNotFoundError as exc:
                raise RuntimeError(
                    "Node.js is required for Stitch SDK integration, but the configured binary was not found."
                ) from exc
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(
                    "Stitch request timed out before the SDK returned a response."
                ) from exc
            except subprocess.SubprocessError as exc:
                raise RuntimeError(f"Stitch bridge failed to run: {exc}") from exc

        raw_output = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part and part.strip())
        try:
            bridge_result = StitchService._parse_bridge_output(raw_output)
        except RuntimeError:
            if completed.returncode != 0:
                raise RuntimeError(raw_output or "Stitch bridge failed without a readable error.")
            raise RuntimeError(
                f"Stitch bridge returned invalid JSON: {raw_output[:500] or '<empty>'}"
            )

        if completed.returncode != 0 or bridge_result.get("ok") is False:
            error = bridge_result.get("error", {}) if isinstance(bridge_result, dict) else {}
            message = error.get("message") or raw_output or "Stitch request failed."
            raise RuntimeError(message)

        return bridge_result.get("result", {})

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
        return StitchService._call_tool("get_screen", {
            "name": f"projects/{project_id}/screens/{screen_id}",
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
