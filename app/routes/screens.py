import json
import mimetypes
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import time
import traceback as traceback_module
import traceback
import uuid

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_file, Response
from werkzeug.utils import secure_filename

from app.services.project_service import ProjectService, ProjectServiceUnavailableError
from app.services.screen_service import ScreenService
from app.services.design_system_service import DesignSystemService
from app.services.stitch_service import StitchService

screens_bp = Blueprint("screens", __name__)
_GENERATION_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="stitch-screen")

DEVICE_TYPES = {
    "MOBILE": "Mobile",
    "DESKTOP": "Desktop",
    "TABLET": "Tablet",
    "AGNOSTIC": "Agnostic",
}

FONT_CHOICES = [
    ("INTER", "Inter"),
    ("SPACE_GROTESK", "Space Grotesk"),
    ("MANROPE", "Manrope"),
    ("DM_SANS", "DM Sans"),
    ("GEIST", "Geist"),
    ("RUBIK", "Rubik"),
    ("MONTSERRAT", "Montserrat"),
    ("WORK_SANS", "Work Sans"),
    ("PLUS_JAKARTA_SANS", "Plus Jakarta Sans"),
    ("PUBLIC_SANS", "Public Sans"),
    ("SORA", "Sora"),
    ("LEXEND", "Lexend"),
    ("EPILOGUE", "Epilogue"),
    ("IBM_PLEX_SANS", "IBM Plex Sans"),
    ("NOTO_SERIF", "Noto Serif"),
    ("NEWSREADER", "Newsreader"),
    ("EB_GARAMOND", "EB Garamond"),
    ("LITERATA", "Literata"),
    ("SOURCE_SERIF_FOUR", "Source Serif 4"),
]

ROUNDNESS_CHOICES = [
    ("ROUND_FOUR", "Small (4px)"),
    ("ROUND_EIGHT", "Medium (8px)"),
    ("ROUND_TWELVE", "Large (12px)"),
    ("ROUND_FULL", "Full"),
]

COLOR_VARIANT_CHOICES = [
    ("TONAL_SPOT", "Tonal Spot"),
    ("VIBRANT", "Vibrant"),
    ("EXPRESSIVE", "Expressive"),
    ("NEUTRAL", "Neutral"),
    ("MONOCHROME", "Monochrome"),
    ("FIDELITY", "Fidelity"),
    ("CONTENT", "Content"),
    ("RAINBOW", "Rainbow"),
    ("FRUIT_SALAD", "Fruit Salad"),
]


def _get_project_or_redirect(project_id):
    try:
        project = ProjectService.get(project_id)
    except ProjectServiceUnavailableError as exc:
        flash(str(exc), "error")
        return None
    if not project:
        flash("Project not found.", "error")
        return None
    return project


def _screen_folder_name(screen):
    return (screen.data or {}).get("folder_name") or screen.name


def _screen_parent_id(screen):
    data = screen.data or {}
    parent_id = data.get("parent_id")
    return str(parent_id) if parent_id else ""


def _default_wireframe(name="Wireframe 1"):
    return {
        "id": f"wfdoc-{uuid.uuid4().hex[:10]}",
        "name": name,
        "canvas": {"width": 1200, "height": 760},
        "items": [],
        "connections": [],
        "created_at": _utc_now_iso(),
        "updated_at": _utc_now_iso(),
    }


def _slugify_filename(value, fallback="wireframe"):
    cleaned = secure_filename((value or "").strip())
    return cleaned or fallback


def _screen_wireframes(data):
    if not isinstance(data, dict):
        return []
    wireframes = data.get("wireframes", [])
    normalized = []
    if isinstance(wireframes, list):
        for index, item in enumerate(wireframes, start=1):
            if not isinstance(item, dict):
                continue
            normalized.append({
                "id": item.get("id") or f"wfdoc-{uuid.uuid4().hex[:10]}",
                "name": item.get("name") or f"Wireframe {index}",
                "canvas": item.get("canvas") or {"width": 1200, "height": 760},
                "items": item.get("items") if isinstance(item.get("items"), list) else [],
                "connections": item.get("connections") if isinstance(item.get("connections"), list) else [],
                "created_at": item.get("created_at") or _utc_now_iso(),
                "updated_at": item.get("updated_at") or _utc_now_iso(),
            })
    if normalized:
        return normalized
    legacy = data.get("wireframe")
    if isinstance(legacy, dict):
        migrated = _default_wireframe()
        migrated["canvas"] = legacy.get("canvas") or migrated["canvas"]
        migrated["items"] = legacy.get("items") if isinstance(legacy.get("items"), list) else []
        migrated["connections"] = legacy.get("connections") if isinstance(legacy.get("connections"), list) else []
        migrated["created_at"] = legacy.get("created_at") or migrated["created_at"]
        migrated["updated_at"] = legacy.get("updated_at") or migrated["updated_at"]
        return [migrated]
    return []


def _find_wireframe(screen, wireframe_id):
    data = screen.data or {}
    wireframes = _screen_wireframes(data)
    if wireframe_id:
        for wireframe in wireframes:
            if wireframe["id"] == wireframe_id:
                return wireframe
    return wireframes[0] if wireframes else None


def _wireframe_export_payload(screen, wireframe):
    return {
        "project_id": screen.project_id,
        "screen_id": screen.id,
        "screen_name": screen.name,
        "folder_name": _screen_folder_name(screen),
        "wireframe_id": wireframe["id"],
        "wireframe_name": wireframe["name"],
        "canvas": wireframe.get("canvas", {}),
        "items": wireframe.get("items", []),
        "connections": wireframe.get("connections", []),
        "created_at": wireframe.get("created_at"),
        "updated_at": wireframe.get("updated_at"),
    }


def _wireframe_export_markdown(screen, wireframe):
    payload = _wireframe_export_payload(screen, wireframe)
    lines = [
        f"# {payload['wireframe_name']}",
        "",
        f"- Folder: {payload['folder_name']}",
        f"- Screen: {payload['screen_name']}",
        f"- Wireframe ID: {payload['wireframe_id']}",
        f"- Canvas: {payload['canvas'].get('width', 0)}x{payload['canvas'].get('height', 0)}",
        f"- Blocks: {len(payload['items'])}",
        f"- Connections: {len(payload['connections'])}",
    ]
    if payload.get("updated_at"):
        lines.append(f"- Updated: {payload['updated_at']}")
    lines.extend(["", "## Blocks", ""])
    if payload["items"]:
        for item in payload["items"]:
            label = item.get("label") or "(untitled)"
            object_id = item.get("objectId") or "n/a"
            item_type = item.get("type") or "block"
            parent_id = item.get("parentId") or "none"
            position = f"({item.get('x', 0)}, {item.get('y', 0)})"
            size = f"{item.get('width', 0)}x{item.get('height', 0)}"
            lines.append(f"- {label}")
            lines.append(f"  Type: {item_type}, Block ID: {object_id}, Parent: {parent_id}")
            lines.append(f"  Position: {position}, Size: {size}")
            if item.get("notes"):
                lines.append(f"  Notes: {item['notes']}")
    else:
        lines.append("- No blocks")
    lines.extend(["", "## Connections", ""])
    if payload["connections"]:
        for connection in payload["connections"]:
            lines.append(f"- {connection.get('from', 'unknown')} -> {connection.get('to', 'unknown')}")
    else:
        lines.append("- No connections")
    return "\n".join(lines) + "\n"


def _screen_materials(data):
    materials = data.get("materials", []) if isinstance(data, dict) else []
    if not isinstance(materials, list):
        return []
    normalized = []
    for item in materials:
        if not isinstance(item, dict):
            continue
        normalized.append(item)
    return normalized


def _screen_material_count(screen):
    data = screen.data or {}
    return len(_screen_materials(data))


def _screen_depth(screen_map, screen_id):
    depth = 0
    current = screen_map.get(screen_id)
    seen = set()
    while current:
        parent_id = _screen_parent_id(current)
        if not parent_id or parent_id in seen:
            break
        seen.add(parent_id)
        current = screen_map.get(parent_id)
        depth += 1
    return depth


def _screen_ancestor_ids(screen_map, screen_id):
    ancestors = set()
    current = screen_map.get(screen_id)
    while current:
        parent_id = _screen_parent_id(current)
        if not parent_id or parent_id in ancestors:
            break
        ancestors.add(parent_id)
        current = screen_map.get(parent_id)
    return ancestors


def _screen_parent_options(screens, current_screen=None):
    screen_map = {screen.id: screen for screen in screens}
    blocked = {current_screen.id} | _screen_ancestor_ids(screen_map, current_screen.id) if current_screen else set()
    options = []
    for screen in screens:
        if screen.id in blocked:
            continue
        options.append({
            "id": screen.id,
            "label": _screen_folder_name(screen),
            "depth": _screen_depth(screen_map, screen.id),
        })
    options.sort(key=lambda item: (item["depth"], item["label"].lower()))
    return options


def _valid_parent_id(screens, selected_parent_id, current_screen=None):
    if not selected_parent_id:
        return ""
    options = {item["id"] for item in _screen_parent_options(screens, current_screen=current_screen)}
    return selected_parent_id if selected_parent_id in options else ""


def _screen_tree_items(screens):
    by_parent = {}
    screen_map = {screen.id: screen for screen in screens}
    for screen in screens:
        parent_id = _screen_parent_id(screen)
        if parent_id and parent_id in screen_map and parent_id != screen.id:
            by_parent.setdefault(parent_id, []).append(screen)
        else:
            by_parent.setdefault("", []).append(screen)

    for items in by_parent.values():
        items.sort(key=lambda screen: _screen_folder_name(screen).lower())

    ordered = []

    def visit(screen, depth):
        ordered.append({"screen": screen, "depth": depth, "has_children": bool(by_parent.get(screen.id))})
        for child in by_parent.get(screen.id, []):
            visit(child, depth + 1)

    for root in by_parent.get("", []):
        visit(root, 0)
    return ordered


def _screen_storage_dir(screen_id):
    return os.path.join(current_app.config["SCREEN_MATERIALS_DIR"], screen_id)


def _material_storage_path(screen_id, stored_name):
    return os.path.join(_screen_storage_dir(screen_id), stored_name)


def _write_material_file(screen_id, stored_name, content, mode="w"):
    storage_dir = _screen_storage_dir(screen_id)
    os.makedirs(storage_dir, exist_ok=True)
    destination = _material_storage_path(screen_id, stored_name)
    with open(destination, mode, encoding="utf-8") as handle:
        handle.write(content)
    return destination


def _build_material_download_url(project_id, screen_id, material_id):
    return url_for(
        "screens.download_material",
        project_id=project_id,
        id=screen_id,
        material_id=material_id,
    )


def _material_badge(material):
    kind = material.get("kind", "reference")
    labels = {
        "upload": "Uploaded File",
        "stitch-preview": "Stitch Preview",
        "stitch-html": "Stitch HTML",
        "html": "HTML Snippet",
        "wireframe": "Wireframe Board",
        "reference": "Reference Link",
    }
    return labels.get(kind, "Material")


def _material_icon(material):
    kind = material.get("kind", "reference")
    if kind in {"upload", "stitch-html", "html"}:
        return "description"
    if kind == "wireframe":
        return "dashboard_customize"
    if kind == "stitch-preview":
        return "image"
    return "link"


def _upsert_material(data, material):
    materials = _screen_materials(data)
    materials = [item for item in materials if item.get("id") != material["id"]]
    materials.insert(0, material)
    data["materials"] = materials
    return data


def _create_material(
    *,
    title,
    kind,
    source,
    created_at=None,
    text_content="",
    external_url="",
    storage_name="",
    original_filename="",
    content_type="",
    size_bytes=None,
):
    timestamp = created_at or _utc_now_iso()
    material_id = f"mat-{uuid.uuid4().hex[:12]}"
    return {
        "id": material_id,
        "title": title,
        "kind": kind,
        "source": source,
        "created_at": timestamp,
        "updated_at": timestamp,
        "text_content": text_content,
        "external_url": external_url,
        "storage_name": storage_name,
        "original_filename": original_filename,
        "content_type": content_type,
        "size_bytes": size_bytes,
    }


def _sync_screen_materials(screen):
    data = dict(screen.data or {})
    materials = _screen_materials(data)

    html = data.get("html", "")
    image_url = data.get("image_url", "")
    wireframes = _screen_wireframes(data)

    materials = [
        item for item in materials
        if item.get("source") not in {"screen_html", "screen_image", "wireframe_board"}
    ]

    if image_url:
        materials.insert(0, {
            "id": "screen-image",
            "title": "Latest screen preview",
            "kind": "stitch-preview" if data.get("stitch_screen_id") else "reference",
            "source": "screen_image",
            "created_at": data.get("generation_finished_at") or _utc_now_iso(),
            "updated_at": data.get("generation_finished_at") or _utc_now_iso(),
            "text_content": "",
            "external_url": image_url,
            "storage_name": "",
            "original_filename": "",
            "content_type": "image",
            "size_bytes": None,
        })

    if html:
        stored_name = "current-screen.html"
        file_path = _write_material_file(screen.id, stored_name, html)
        materials.insert(0, {
            "id": "screen-html",
            "title": "Current screen HTML",
            "kind": "stitch-html" if data.get("stitch_screen_id") else "html",
            "source": "screen_html",
            "created_at": data.get("generation_finished_at") or _utc_now_iso(),
            "updated_at": data.get("generation_finished_at") or _utc_now_iso(),
            "text_content": "",
            "external_url": data.get("html_download_url", ""),
            "storage_name": stored_name,
            "original_filename": "current-screen.html",
            "content_type": "text/html",
            "size_bytes": os.path.getsize(file_path),
        })

    for wireframe in reversed(wireframes):
        items = wireframe.get("items", [])
        if isinstance(items, list):
            materials.insert(0, {
                "id": f"wireframe-board-{wireframe['id']}",
                "title": wireframe.get("name") or "Wireframe",
                "kind": "wireframe",
                "source": "wireframe_board",
                "wireframe_id": wireframe["id"],
                "created_at": wireframe.get("created_at") or _utc_now_iso(),
                "updated_at": wireframe.get("updated_at") or _utc_now_iso(),
                "text_content": "",
                "external_url": "",
                "storage_name": "",
                "original_filename": "",
                "content_type": "application/json",
                "size_bytes": len(json.dumps(wireframe).encode("utf-8")),
            })

    data["materials"] = materials
    data["folder_name"] = data.get("folder_name") or screen.name
    data["wireframes"] = wireframes
    data["wireframe"] = None
    ScreenService.update(screen, data=data)
    return ScreenService.get(screen.id)


def _material_view_model(project_id, screen_id, material):
    item = dict(material)
    item["badge"] = _material_badge(item)
    item["icon"] = _material_icon(item)
    item["download_url"] = ""
    item["open_url"] = item.get("external_url", "")
    item["is_file"] = bool(item.get("storage_name"))
    item["is_html"] = (item.get("content_type") == "text/html") or item.get("kind") in {"html", "stitch-html"}
    item["can_delete"] = item.get("source") == "upload"
    item["is_wireframe"] = item.get("kind") == "wireframe"
    item["can_edit"] = item["is_html"] and (
        item.get("is_file") or item.get("source") == "screen_html"
    )
    if item["is_file"]:
        item["download_url"] = _build_material_download_url(project_id, screen_id, item["id"])
        item["open_url"] = item["download_url"]
    elif item["is_wireframe"]:
        item["open_url"] = url_for(
            "screens.wireframe_editor",
            project_id=project_id,
            id=screen_id,
            wireframe_id=item.get("wireframe_id", ""),
        )
    return item


def _screen_detail_context(project, screen):
    synced_screen = _sync_screen_materials(screen)
    data = synced_screen.data or {}
    materials = [
        _material_view_model(project.id, synced_screen.id, material)
        for material in _screen_materials(data)
    ]
    return {
        "project": project,
        "screen": synced_screen,
        "device_labels": DEVICE_TYPES,
        "materials": materials,
        "material_count": len(materials),
        "folder_name": _screen_folder_name(synced_screen),
        "wireframes": _screen_wireframes(data),
    }


def _save_uploaded_material(screen, uploaded_file):
    filename = secure_filename(uploaded_file.filename or "")
    if not filename:
        raise ValueError("Choose a file to upload.")

    storage_dir = _screen_storage_dir(screen.id)
    os.makedirs(storage_dir, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex[:12]}-{filename}"
    destination = _material_storage_path(screen.id, unique_name)
    uploaded_file.save(destination)

    content_type = uploaded_file.mimetype or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    size_bytes = os.path.getsize(destination)

    material = _create_material(
        title=filename,
        kind="upload",
        source="upload",
        storage_name=unique_name,
        original_filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
    )
    data = dict(screen.data or {})
    _upsert_material(data, material)
    ScreenService.update(screen, data=data)
    return material


def _delete_material_from_screen(screen, material_id):
    data = dict(screen.data or {})
    materials = _screen_materials(data)
    target = next((item for item in materials if item.get("id") == material_id), None)
    if not target:
        return False

    storage_name = target.get("storage_name")
    if storage_name:
        file_path = _material_storage_path(screen.id, storage_name)
        if os.path.exists(file_path):
            os.remove(file_path)

    data["materials"] = [item for item in materials if item.get("id") != material_id]
    ScreenService.update(screen, data=data)
    return True


def _find_material(screen, material_id):
    for material in _screen_materials(screen.data or {}):
        if material.get("id") == material_id:
            return material
    return None


def _material_text_content(screen, material):
    storage_name = material.get("storage_name")
    if storage_name:
        file_path = _material_storage_path(screen.id, storage_name)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as handle:
                return handle.read()
    return material.get("text_content", "")


def _extract_stitch_content(result):
    """Extract HTML and image URL from a Stitch MCP result."""
    if isinstance(result, dict) and "content" not in result:
        raw_text = json.dumps(result)
        html = ""
        image_url = ""
        screen_id = ""
        assistant_text = ""
        suggestions = []
        html_download_url = ""

        extracted_resource = _extract_screen_from_resource(result)
        if extracted_resource:
            html = extracted_resource.get("html", "")
            image_url = extracted_resource.get("image_url", "")
            screen_id = extracted_resource.get("screen_id", "")
            html_download_url = extracted_resource.get("html_download_url", "")

        output_components = result.get("outputComponents", [])
        if isinstance(output_components, list):
            for component in output_components:
                if not isinstance(component, dict):
                    continue
                if component.get("text"):
                    assistant_text = component.get("text", "").strip()
                if component.get("suggestion"):
                    suggestions.append(component.get("suggestion", "").strip())
                design = component.get("design", {})
                screens = design.get("screens", []) if isinstance(design, dict) else []
                if screens and not screen_id:
                    extracted = _extract_screen_from_resource(screens[0])
                    if extracted:
                        html = extracted.get("html", html)
                        image_url = extracted.get("image_url", image_url)
                        screen_id = extracted.get("screen_id", screen_id)
                        html_download_url = extracted.get("html_download_url", html_download_url)

        return {
            "html": html,
            "image_url": image_url,
            "screen_id": screen_id,
            "raw_text": raw_text,
            "assistant_text": assistant_text,
            "suggestions": [s for s in suggestions if s],
            "html_download_url": html_download_url,
        }

    content = result.get("content", [])
    html = ""
    image_url = ""
    screen_id = ""
    raw_text = ""
    assistant_text = ""
    suggestions = []

    for item in content:
        if isinstance(item, dict):
            if item.get("type") == "text":
                raw_text = item.get("text", "")
            elif item.get("type") == "resource":
                resource = item.get("resource", {})
                uri = resource.get("uri", "")
                if "image" in resource.get("mimeType", ""):
                    image_url = uri

    # Try to parse screen info from the text content
    if raw_text:
        try:
            parsed = json.loads(raw_text)
            if isinstance(parsed, dict):
                screen_id = parsed.get("screenId", parsed.get("screen_id", ""))
                html = parsed.get("html", parsed.get("code", ""))
                if not image_url:
                    image_url = parsed.get("imageUrl", parsed.get("image_url", ""))
                output_components = parsed.get("outputComponents", [])
                if isinstance(output_components, list):
                    for component in output_components:
                        if not isinstance(component, dict):
                            continue
                        if component.get("text"):
                            assistant_text = component.get("text", "").strip()
                        if component.get("suggestion"):
                            suggestions.append(component.get("suggestion", "").strip())
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "html": html,
        "image_url": image_url,
        "screen_id": screen_id,
        "raw_text": raw_text,
        "assistant_text": assistant_text,
        "suggestions": [s for s in suggestions if s],
        "html_download_url": "",
    }


def _screen_ids_from_list_result(result):
    screens = result if isinstance(result, list) else result.get("screens", []) if isinstance(result, dict) else []
    ids = set()
    for item in screens:
        if not isinstance(item, dict):
            continue
        screen_id = item.get("id")
        if not screen_id and item.get("name"):
            screen_id = str(item["name"]).split("/")[-1]
        if screen_id:
            ids.add(str(screen_id))
    return ids


def _extract_screen_from_resource(result):
    if not isinstance(result, dict):
        return None

    screen_id = result.get("id")
    if not screen_id and result.get("name"):
        screen_id = str(result["name"]).split("/")[-1]

    screenshot = result.get("screenshot", {}) if isinstance(result.get("screenshot"), dict) else {}
    html_code = result.get("htmlCode", {}) if isinstance(result.get("htmlCode"), dict) else {}

    image_url = screenshot.get("downloadUrl", "")
    html_download_url = html_code.get("downloadUrl", "")

    if not any([screen_id, image_url, html_download_url]):
        return None

    return {
        "screen_id": str(screen_id or ""),
        "image_url": image_url,
        "html": "",
        "raw_text": json.dumps(result)[:5000],
        "html_download_url": html_download_url,
    }


def _recover_generated_screen(project_id, existing_screen_ids, poll_attempts=6, poll_interval_seconds=20):
    if existing_screen_ids is None:
        return None

    for attempt in range(poll_attempts):
        if attempt:
            time.sleep(poll_interval_seconds)

        listed = StitchService.list_screens(project_id)
        screens = listed if isinstance(listed, list) else listed.get("screens", []) if isinstance(listed, dict) else []

        for item in screens:
            if not isinstance(item, dict):
                continue

            screen_id = item.get("id")
            if not screen_id and item.get("name"):
                screen_id = str(item["name"]).split("/")[-1]
            if not screen_id or str(screen_id) in existing_screen_ids:
                continue

            detailed = StitchService.get_screen(project_id, str(screen_id))
            extracted = _extract_screen_from_resource(detailed)
            if extracted:
                return extracted

    return None


def _recover_generation_after_disconnect(app, screen_id, project_id, existing_screen_ids):
    with app.app_context():
        try:
            recovered = _recover_generated_screen(
                project_id,
                existing_screen_ids,
                poll_attempts=15,
                poll_interval_seconds=20,
            )
            if recovered:
                _update_generation_state(
                    screen_id,
                    stitch_project_id=project_id,
                    stitch_screen_id=recovered["screen_id"],
                    html=recovered["html"],
                    image_url=recovered["image_url"],
                    raw_response=recovered["raw_text"],
                    html_download_url=recovered.get("html_download_url", ""),
                    generation_status="completed",
                    generation_error="",
                    generation_error_details="",
                    generation_finished_at=_utc_now_iso(),
                )
                return

            _update_generation_state(
                screen_id,
                generation_status="failed",
                generation_error=(
                    "Stitch dropped the connection before returning a result, "
                    "and no new screen appeared after waiting. Please try again."
                ),
                generation_finished_at=_utc_now_iso(),
            )
        except Exception as exc:
            traceback.print_exc()
            _update_generation_state(
                screen_id,
                generation_status="failed",
                generation_error=(
                    "Stitch dropped the connection and recovery failed while checking for the generated screen."
                ),
                generation_error_details="".join(
                    traceback_module.format_exception(type(exc), exc, exc.__traceback__)
                )[:5000],
                generation_finished_at=_utc_now_iso(),
            )


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def _update_generation_state(screen_id, **changes):
    screen = ScreenService.get(screen_id)
    if not screen:
        return None

    data = dict(screen.data or {})
    data.update(changes)
    updated = ScreenService.update_data(screen_id, data)
    if updated and any(key in changes for key in ("html", "image_url", "html_download_url")):
        return _sync_screen_materials(updated)
    return updated


def _run_screen_generation(app, project_id, screen_id, prompt, device_type, stitch_project_id=""):
    with app.app_context():
        active_stitch_project_id = stitch_project_id
        existing_screen_ids = None
        try:
            _update_generation_state(
                screen_id,
                generation_status="running",
                generation_error="",
                generation_error_details="",
                generation_started_at=_utc_now_iso(),
            )
            if not active_stitch_project_id:
                design_system = DesignSystemService.get_for_project(project_id)
                if design_system and design_system.data:
                    active_stitch_project_id = design_system.data.get("stitch_project_id", "")

            if not active_stitch_project_id:
                try:
                    project = ProjectService.get(project_id)
                except ProjectServiceUnavailableError:
                    project = None
                create_result = StitchService.create_project(
                    title=project.name if project else "Untitled Project"
                )
                stitch_content = _extract_stitch_content(create_result)
                if stitch_content["raw_text"]:
                    try:
                        parsed = json.loads(stitch_content["raw_text"])
                        active_stitch_project_id = str(
                            parsed.get("projectId", parsed.get("name", "").split("/")[-1])
                        )
                    except (json.JSONDecodeError, TypeError):
                        pass

            if not active_stitch_project_id:
                raise RuntimeError("Could not create or find a Stitch project.")

            existing_screen_ids = _screen_ids_from_list_result(
                StitchService.list_screens(active_stitch_project_id)
            )

            result = StitchService.generate_screen(
                project_id=active_stitch_project_id,
                prompt=prompt,
                device_type=device_type,
            )
            content = _extract_stitch_content(result)

            if not any([content["screen_id"], content["html"], content["image_url"]]):
                if content["assistant_text"] or content["suggestions"]:
                    _update_generation_state(
                        screen_id,
                        stitch_project_id=active_stitch_project_id,
                        raw_response=content["raw_text"][:5000],
                        generation_status="needs_input",
                        generation_error="",
                        generation_error_details="",
                        assistant_text=content["assistant_text"],
                        assistant_suggestions=content["suggestions"][:5],
                        generation_finished_at=_utc_now_iso(),
                    )
                    return
                raise RuntimeError("Stitch did not return a screen preview.")

            _update_generation_state(
                screen_id,
                stitch_project_id=active_stitch_project_id,
                stitch_screen_id=content["screen_id"],
                html=content["html"],
                image_url=content["image_url"],
                raw_response=content["raw_text"][:5000],
                generation_status="completed",
                generation_error="",
                generation_error_details="",
                assistant_text="",
                assistant_suggestions=[],
                generation_finished_at=_utc_now_iso(),
            )
        except Exception as exc:
            traceback.print_exc()
            if (
                str(exc) == "Stitch closed the connection before sending a response."
                and active_stitch_project_id
            ):
                try:
                    _update_generation_state(
                        screen_id,
                        generation_status="recovering",
                        generation_error="",
                        generation_error_details="",
                        generation_finished_at="",
                    )
                    _GENERATION_EXECUTOR.submit(
                        _recover_generation_after_disconnect,
                        current_app._get_current_object(),
                        screen_id,
                        active_stitch_project_id,
                        existing_screen_ids or set(),
                    )
                    return
                except Exception:
                    traceback.print_exc()

            _update_generation_state(
                screen_id,
                generation_status="failed",
                generation_error=str(exc),
                generation_error_details="".join(
                    traceback_module.format_exception(type(exc), exc, exc.__traceback__)
                )[:5000],
                generation_finished_at=_utc_now_iso(),
            )


# --- Screen CRUD routes ---

@screens_bp.route("/projects/<project_id>/screens")
def index(project_id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))
    screens = ScreenService.get_all_for_project(project_id)
    screens = [_sync_screen_materials(screen) for screen in screens]
    design_system = DesignSystemService.get_for_project(project_id)
    return render_template(
        "screens/index.html",
        project=project,
        screens=screens,
        screen_tree=_screen_tree_items(screens),
        design_system=design_system,
        device_labels=DEVICE_TYPES,
        screen_material_count=_screen_material_count,
    )


@screens_bp.route("/projects/<project_id>/screens/new", methods=["GET", "POST"])
def create(project_id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))
    screens = [_sync_screen_materials(screen) for screen in ScreenService.get_all_for_project(project_id)]
    parent_options = _screen_parent_options(screens)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        device_type = request.form.get("device_type", "DESKTOP")
        description = request.form.get("description", "").strip()
        html_content = request.form.get("html_content", "").strip()
        image_url = request.form.get("image_url", "").strip()
        parent_id = _valid_parent_id(screens, request.form.get("parent_id", "").strip())

        if not name:
            flash("Screen name is required.", "error")
            return render_template(
                "screens/form.html",
                project=project,
                device_types=DEVICE_TYPES,
                data={},
                parent_options=parent_options,
                selected_parent_id=parent_id,
            )

        data = {"folder_name": name}
        if parent_id:
            data["parent_id"] = parent_id
        if html_content:
            data["html"] = html_content
        if image_url:
            data["image_url"] = image_url

        screen = ScreenService.create(
            project_id=project_id, name=name,
            device_type=device_type, description=description, data=data,
        )
        screen = _sync_screen_materials(screen)
        flash("Screen created.", "success")
        return redirect(url_for("screens.detail", project_id=project_id, id=screen.id))

    return render_template(
        "screens/form.html",
        project=project,
        device_types=DEVICE_TYPES,
        data={},
        parent_options=parent_options,
        selected_parent_id=_valid_parent_id(screens, request.args.get("parent_id", "").strip()),
    )


@screens_bp.route("/projects/<project_id>/screens/<id>")
def detail(project_id, id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))
    screen = ScreenService.get(id)
    if not screen or screen.project_id != project_id:
        flash("Screen not found.", "error")
        return redirect(url_for("screens.index", project_id=project_id))
    return render_template("screens/detail.html", **_screen_detail_context(project, screen))


@screens_bp.route("/projects/<project_id>/screens/<id>/materials", methods=["POST"])
def upload_material(project_id, id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))
    screen = ScreenService.get(id)
    if not screen or screen.project_id != project_id:
        flash("Screen folder not found.", "error")
        return redirect(url_for("screens.index", project_id=project_id))

    uploaded_file = request.files.get("material_file")
    if not uploaded_file or not uploaded_file.filename:
        flash("Choose a file to upload.", "error")
        return redirect(url_for("screens.detail", project_id=project_id, id=id))

    try:
        _save_uploaded_material(screen, uploaded_file)
        flash("Material uploaded to the screen folder.", "success")
    except ValueError as exc:
        flash(str(exc), "error")

    return redirect(url_for("screens.detail", project_id=project_id, id=id))


@screens_bp.route("/projects/<project_id>/screens/<id>/materials/<material_id>")
def download_material(project_id, id, material_id):
    screen = ScreenService.get(id)
    if not screen or screen.project_id != project_id:
        flash("Screen folder not found.", "error")
        return redirect(url_for("screens.index", project_id=project_id))

    material = _find_material(screen, material_id)
    if not material:
        flash("Material not found.", "error")
        return redirect(url_for("screens.detail", project_id=project_id, id=id))

    if material.get("storage_name"):
        file_path = _material_storage_path(screen.id, material["storage_name"])
        if not os.path.exists(file_path):
            flash("Material file is missing on disk.", "error")
            return redirect(url_for("screens.detail", project_id=project_id, id=id))
        return send_file(
            file_path,
            mimetype=material.get("content_type") or "application/octet-stream",
            as_attachment=False,
            download_name=material.get("original_filename") or material.get("title") or "material",
        )

    external_url = material.get("external_url")
    if external_url:
        return redirect(external_url)

    flash("This material cannot be opened directly.", "error")
    return redirect(url_for("screens.detail", project_id=project_id, id=id))


@screens_bp.route("/projects/<project_id>/screens/<id>/materials/<material_id>/delete", methods=["POST"])
def delete_material(project_id, id, material_id):
    screen = ScreenService.get(id)
    if not screen or screen.project_id != project_id:
        flash("Screen folder not found.", "error")
        return redirect(url_for("screens.index", project_id=project_id))

    if _delete_material_from_screen(screen, material_id):
        flash("Material removed from the screen folder.", "success")
    else:
        flash("Material not found.", "error")

    return redirect(url_for("screens.detail", project_id=project_id, id=id))


@screens_bp.route("/projects/<project_id>/screens/<id>/materials/<material_id>/edit", methods=["GET", "POST"])
def edit_material(project_id, id, material_id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))
    screen = ScreenService.get(id)
    if not screen or screen.project_id != project_id:
        flash("Screen folder not found.", "error")
        return redirect(url_for("screens.index", project_id=project_id))

    screen = _sync_screen_materials(screen)
    material = _find_material(screen, material_id)
    if not material:
        flash("Material not found.", "error")
        return redirect(url_for("screens.detail", project_id=project_id, id=id))

    if material.get("content_type") != "text/html":
        flash("Only HTML materials can be edited here.", "error")
        return redirect(url_for("screens.detail", project_id=project_id, id=id))

    if request.method == "POST":
        html_content = request.form.get("html_content", "")
        data = dict(screen.data or {})
        if material.get("source") == "screen_html":
            data["html"] = html_content
            ScreenService.update(screen, data=data)
            _sync_screen_materials(screen)
        elif material.get("storage_name"):
            _write_material_file(screen.id, material["storage_name"], html_content)
            materials = _screen_materials(data)
            for item in materials:
                if item.get("id") == material_id:
                    item["updated_at"] = _utc_now_iso()
                    item["size_bytes"] = len(html_content.encode("utf-8"))
                    break
            data["materials"] = materials
            ScreenService.update(screen, data=data)
        flash("HTML file updated.", "success")
        return redirect(url_for("screens.detail", project_id=project_id, id=id))

    return render_template(
        "screens/edit_material.html",
        project=project,
        screen=screen,
        folder_name=_screen_folder_name(screen),
        material=material,
        html_content=_material_text_content(screen, material),
    )


@screens_bp.route("/projects/<project_id>/screens/<id>/wireframe")
def wireframe_editor(project_id, id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))
    screen = ScreenService.get(id)
    if not screen or screen.project_id != project_id:
        flash("Screen folder not found.", "error")
        return redirect(url_for("screens.index", project_id=project_id))

    screen = _sync_screen_materials(screen)
    data = dict(screen.data or {})
    wireframes = _screen_wireframes(data)
    if request.args.get("new") == "1":
        new_wireframe = _default_wireframe(f"Wireframe {len(wireframes) + 1}")
        wireframes.append(new_wireframe)
        data["wireframes"] = wireframes
        data["wireframe"] = None
        ScreenService.update(screen, data=data)
        return redirect(
            url_for("screens.wireframe_editor", project_id=project_id, id=id, wireframe_id=new_wireframe["id"])
        )

    if not wireframes:
        initial_wireframe = _default_wireframe("Wireframe 1")
        wireframes = [initial_wireframe]
        data["wireframes"] = wireframes
        data["wireframe"] = None
        ScreenService.update(screen, data=data)
        screen = ScreenService.get(screen.id)

    selected_id = request.args.get("wireframe_id", "").strip()
    selected_wireframe = next((item for item in wireframes if item["id"] == selected_id), None)
    if not selected_wireframe:
        selected_wireframe = wireframes[0]

    return render_template(
        "screens/wireframe.html",
        project=project,
        screen=screen,
        folder_name=_screen_folder_name(screen),
        wireframe=selected_wireframe,
        wireframes=wireframes,
    )


@screens_bp.route("/projects/<project_id>/screens/<id>/wireframes/<wireframe_id>/export")
def export_wireframe(project_id, id, wireframe_id):
    screen = ScreenService.get(id)
    if not screen or screen.project_id != project_id:
        flash("Screen folder not found.", "error")
        return redirect(url_for("screens.index", project_id=project_id))

    screen = _sync_screen_materials(screen)
    wireframe = _find_wireframe(screen, wireframe_id)
    if not wireframe:
        flash("Wireframe not found.", "error")
        return redirect(url_for("screens.wireframe_editor", project_id=project_id, id=id))

    fmt = request.args.get("format", "json")
    filename = _slugify_filename(f"{_screen_folder_name(screen)}-{wireframe['name']}", "wireframe")
    if fmt == "markdown":
        markdown = _wireframe_export_markdown(screen, wireframe)
        return Response(
            markdown,
            mimetype="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={filename}.md"},
        )

    return Response(
        json.dumps(_wireframe_export_payload(screen, wireframe), indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}.json"},
    )


@screens_bp.route("/projects/<project_id>/screens/<id>/edit", methods=["GET", "POST"])
def edit(project_id, id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))
    screen = ScreenService.get(id)
    if not screen or screen.project_id != project_id:
        flash("Screen not found.", "error")
        return redirect(url_for("screens.index", project_id=project_id))
    screen = _sync_screen_materials(screen)
    screens = [_sync_screen_materials(item) for item in ScreenService.get_all_for_project(project_id)]
    parent_options = _screen_parent_options(screens, current_screen=screen)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        device_type = request.form.get("device_type", screen.device_type)
        description = request.form.get("description", "").strip()
        html_content = request.form.get("html_content", "").strip()
        image_url = request.form.get("image_url", "").strip()
        parent_id = _valid_parent_id(screens, request.form.get("parent_id", "").strip(), current_screen=screen)

        if not name:
            flash("Screen name is required.", "error")
            return render_template(
                "screens/form.html",
                project=project,
                screen=screen,
                device_types=DEVICE_TYPES,
                data=screen.data or {},
                parent_options=parent_options,
                selected_parent_id=parent_id,
            )

        data = dict(screen.data or {})
        data["folder_name"] = name
        data["parent_id"] = parent_id or None
        if html_content:
            data["html"] = html_content
        elif "html" in data and not html_content:
            pass  # keep existing HTML if field left empty
        if image_url:
            data["image_url"] = image_url

        ScreenService.update(screen, name=name, device_type=device_type,
                             description=description, data=data)
        _sync_screen_materials(screen)
        flash("Screen updated.", "success")
        return redirect(url_for("screens.detail", project_id=project_id, id=id))

    return render_template(
        "screens/form.html",
        project=project,
        screen=screen,
        device_types=DEVICE_TYPES,
        data=screen.data or {},
        parent_options=parent_options,
        selected_parent_id=_screen_parent_id(screen),
    )


@screens_bp.route("/projects/<project_id>/screens/<id>/delete", methods=["POST"])
def delete(project_id, id):
    screen = ScreenService.get(id)
    if screen and screen.project_id == project_id:
        shutil.rmtree(_screen_storage_dir(screen.id), ignore_errors=True)
        ScreenService.delete(screen)
        flash("Screen deleted.", "success")
    return redirect(url_for("screens.index", project_id=project_id))


# --- Stitch Generation routes ---

@screens_bp.route("/projects/<project_id>/screens/generate", methods=["GET", "POST"])
def generate(project_id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))

    initial_data = {
        "prompt": request.args.get("prompt", "").strip(),
        "name": request.args.get("name", "").strip(),
        "device_type": request.args.get("device_type", "DESKTOP").strip() or "DESKTOP",
    }

    if request.method == "POST":
        prompt = request.form.get("prompt", "").strip()
        device_type = request.form.get("device_type", "DESKTOP")
        screen_name = request.form.get("name", "").strip() or "Generated Screen"
        stitch_project_id = request.form.get("stitch_project_id", "").strip()

        if not prompt:
            flash("A prompt is required to generate a screen.", "error")
            return render_template("screens/generate.html", project=project,
                                   device_types=DEVICE_TYPES, data=initial_data)

        data = {
            "prompt": prompt,
            "folder_name": screen_name,
            "stitch_project_id": stitch_project_id,
            "generation_status": "queued",
            "generation_error": "",
            "generation_error_details": "",
            "generation_queued_at": _utc_now_iso(),
        }

        screen = ScreenService.create(
            project_id=project_id,
            name=screen_name,
            device_type=device_type.lower(),
            description=f"Generated from prompt: {prompt[:200]}",
            data=data,
        )

        try:
            _GENERATION_EXECUTOR.submit(
                _run_screen_generation,
                current_app._get_current_object(),
                project_id,
                screen.id,
                prompt,
                device_type,
                stitch_project_id,
            )
        except Exception as exc:
            traceback.print_exc()
            _update_generation_state(
                screen.id,
                generation_status="failed",
                generation_error=f"Could not start background generation: {exc}",
                generation_error_details="".join(
                    traceback_module.format_exception(type(exc), exc, exc.__traceback__)
                )[:5000],
                generation_finished_at=_utc_now_iso(),
            )
            flash("Screen generation could not be started.", "error")
            return redirect(url_for("screens.detail", project_id=project_id, id=screen.id))

        flash("Screen generation started. This page will update when Stitch finishes.", "success")
        return redirect(url_for("screens.detail", project_id=project_id, id=screen.id))

    return render_template("screens/generate.html", project=project,
                           device_types=DEVICE_TYPES, data=initial_data)


@screens_bp.route("/projects/<project_id>/screens/<id>/edit-with-ai", methods=["GET", "POST"])
def edit_with_ai(project_id, id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))
    screen = ScreenService.get(id)
    if not screen or screen.project_id != project_id:
        flash("Screen not found.", "error")
        return redirect(url_for("screens.index", project_id=project_id))

    if request.method == "POST":
        prompt = request.form.get("prompt", "").strip()
        if not prompt:
            flash("An edit prompt is required.", "error")
            return render_template("screens/edit_with_ai.html", project=project, screen=screen)

        try:
            screen_data = screen.data or {}
            stitch_project_id = screen_data.get("stitch_project_id", "")
            stitch_screen_id = screen_data.get("stitch_screen_id", "")

            if not stitch_project_id or not stitch_screen_id:
                flash("This screen has no Stitch reference. Generate it first.", "error")
                return render_template("screens/edit_with_ai.html", project=project, screen=screen)

            result = StitchService.edit_screens(
                project_id=stitch_project_id,
                screen_ids=[stitch_screen_id],
                prompt=prompt,
                device_type=screen.device_type.upper(),
            )

            content = _extract_stitch_content(result)

            # Update screen data
            data = dict(screen_data)
            if content["html"]:
                data["html"] = content["html"]
            if content["image_url"]:
                data["image_url"] = content["image_url"]
            data["last_edit_prompt"] = prompt

            ScreenService.update(screen, data=data)
            _sync_screen_materials(screen)
            flash("Screen updated with AI edits.", "success")
            return redirect(url_for("screens.detail", project_id=project_id, id=id))

        except Exception as e:
            flash(f"AI edit failed: {str(e)}", "error")
            traceback.print_exc()
            return render_template("screens/edit_with_ai.html", project=project, screen=screen)

    return render_template("screens/edit_with_ai.html", project=project, screen=screen)


@screens_bp.route("/projects/<project_id>/screens/<id>/variants", methods=["GET", "POST"])
def generate_variants(project_id, id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))
    screen = ScreenService.get(id)
    if not screen or screen.project_id != project_id:
        flash("Screen not found.", "error")
        return redirect(url_for("screens.index", project_id=project_id))

    if request.method == "POST":
        prompt = request.form.get("prompt", "").strip() or "Generate variants"
        variant_count = int(request.form.get("variant_count", "3"))
        creative_range = request.form.get("creative_range", "EXPLORE")
        aspects = request.form.getlist("aspects")

        try:
            screen_data = screen.data or {}
            stitch_project_id = screen_data.get("stitch_project_id", "")
            stitch_screen_id = screen_data.get("stitch_screen_id", "")

            if not stitch_project_id or not stitch_screen_id:
                flash("This screen has no Stitch reference.", "error")
                return render_template("screens/variants.html", project=project, screen=screen)

            result = StitchService.generate_variants(
                project_id=stitch_project_id,
                screen_ids=[stitch_screen_id],
                prompt=prompt,
                variant_count=variant_count,
                creative_range=creative_range,
                aspects=aspects or None,
            )

            # Result may contain multiple screens
            content = _extract_stitch_content(result)
            # Save as a new screen
            data = {
                "prompt": f"Variant of '{screen.name}': {prompt}",
                "stitch_project_id": stitch_project_id,
                "stitch_screen_id": content["screen_id"],
                "html": content["html"],
                "image_url": content["image_url"],
                "variant_of": id,
            }
            variant = ScreenService.create(
                project_id=project_id,
                name=f"{screen.name} (variant)",
                device_type=screen.device_type,
                description=f"Variant of '{screen.name}'",
                data=data,
            )
            variant = _sync_screen_materials(variant)

            flash("Variant generated!", "success")
            return redirect(url_for("screens.detail", project_id=project_id, id=variant.id))

        except Exception as e:
            flash(f"Variant generation failed: {str(e)}", "error")
            traceback.print_exc()
            return render_template("screens/variants.html", project=project, screen=screen)

    return render_template("screens/variants.html", project=project, screen=screen)


# --- Design System routes ---

@screens_bp.route("/projects/<project_id>/design-system")
def design_system(project_id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))
    ds = DesignSystemService.get_for_project(project_id)
    return render_template(
        "screens/design_system.html",
        project=project,
        design_system=ds,
        font_choices=FONT_CHOICES,
    )


@screens_bp.route("/projects/<project_id>/design-system/edit", methods=["GET", "POST"])
def design_system_edit(project_id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))
    ds = DesignSystemService.get_for_project(project_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip() or f"{project.name} Design System"
        color_mode = request.form.get("color_mode", "LIGHT")
        custom_color = request.form.get("custom_color", "#005db5")
        headline_font = request.form.get("headline_font", "INTER")
        body_font = request.form.get("body_font", "INTER")
        label_font = request.form.get("label_font", "")
        roundness = request.form.get("roundness", "ROUND_EIGHT")
        color_variant = request.form.get("color_variant", "TONAL_SPOT")
        design_md = request.form.get("design_md", "").strip()
        sync_to_stitch = request.form.get("sync_to_stitch") == "on"

        data = {
            "color_mode": color_mode,
            "custom_color": custom_color,
            "headline_font": headline_font,
            "body_font": body_font,
            "label_font": label_font,
            "roundness": roundness,
            "color_variant": color_variant,
            "design_md": design_md,
        }

        # Optionally sync to Stitch
        if sync_to_stitch:
            try:
                stitch_ds = {
                    "displayName": name,
                    "theme": {
                        "colorMode": color_mode,
                        "customColor": custom_color,
                        "headlineFont": headline_font,
                        "bodyFont": body_font,
                        "roundness": roundness,
                        "colorVariant": color_variant,
                    },
                }
                if label_font:
                    stitch_ds["theme"]["labelFont"] = label_font
                if design_md:
                    stitch_ds["theme"]["designMd"] = design_md

                stitch_project_id = ""
                if ds and ds.data:
                    stitch_project_id = ds.data.get("stitch_project_id", "")

                if ds and ds.data and ds.data.get("stitch_asset_id"):
                    asset_name = f"assets/{ds.data['stitch_asset_id']}"
                    StitchService.update_design_system(stitch_project_id, asset_name, stitch_ds)
                else:
                    result = StitchService.create_design_system(stitch_project_id, stitch_ds)
                    content = _extract_stitch_content(result)
                    if content["raw_text"]:
                        try:
                            parsed = json.loads(content["raw_text"])
                            data["stitch_asset_id"] = parsed.get("assetId", parsed.get("name", "").split("/")[-1])
                        except (json.JSONDecodeError, TypeError):
                            pass

                flash("Design system synced to Stitch.", "success")
            except Exception as e:
                flash(f"Stitch sync failed (saved locally): {str(e)}", "warning")

        if ds:
            # Preserve stitch IDs
            existing_data = ds.data or {}
            for key in ("stitch_project_id", "stitch_asset_id"):
                if key in existing_data and key not in data:
                    data[key] = existing_data[key]
            DesignSystemService.update(ds, name=name, data=data)
        else:
            DesignSystemService.create(project_id=project_id, name=name, data=data)

        flash("Design system saved.", "success")
        return redirect(url_for("screens.design_system", project_id=project_id))

    return render_template(
        "screens/design_system_form.html",
        project=project,
        design_system=ds,
        font_choices=FONT_CHOICES,
        roundness_choices=ROUNDNESS_CHOICES,
        color_variant_choices=COLOR_VARIANT_CHOICES,
        data=ds.data if ds else {},
    )


# --- JSON API routes ---

@screens_bp.route("/api/screens/<id>", methods=["GET"])
def api_get(id):
    screen = ScreenService.get(id)
    if not screen:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "id": screen.id,
        "project_id": screen.project_id,
        "name": screen.name,
        "device_type": screen.device_type,
        "description": screen.description,
        "data": screen.data,
    })


@screens_bp.route("/api/screens/<id>", methods=["PUT"])
def api_update(id):
    screen = ScreenService.get(id)
    if not screen:
        return jsonify({"error": "not found"}), 404
    body = request.get_json()
    if not body:
        return jsonify({"error": "invalid JSON"}), 400
    ScreenService.update(
        screen,
        name=body.get("name"),
        device_type=body.get("device_type"),
        description=body.get("description"),
        data=body.get("data"),
    )
    if body.get("data") is not None:
        _sync_screen_materials(screen)
    return jsonify({"status": "ok"})
