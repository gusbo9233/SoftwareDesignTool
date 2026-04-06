import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import traceback as traceback_module
import traceback

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app

from app.services.project_service import ProjectService
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
    project = ProjectService.get(project_id)
    if not project:
        flash("Project not found.", "error")
        return None
    return project


def _extract_stitch_content(result):
    """Extract HTML and image URL from a Stitch MCP result."""
    content = result.get("content", [])
    html = ""
    image_url = ""
    screen_id = ""
    raw_text = ""

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
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "html": html,
        "image_url": image_url,
        "screen_id": screen_id,
        "raw_text": raw_text,
    }


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def _update_generation_state(screen_id, **changes):
    screen = ScreenService.get(screen_id)
    if not screen:
        return None

    data = dict(screen.data or {})
    data.update(changes)
    return ScreenService.update_data(screen_id, data)


def _run_screen_generation(app, project_id, screen_id, prompt, device_type, stitch_project_id=""):
    with app.app_context():
        try:
            _update_generation_state(
                screen_id,
                generation_status="running",
                generation_error="",
                generation_error_details="",
                generation_started_at=_utc_now_iso(),
            )

            active_stitch_project_id = stitch_project_id
            if not active_stitch_project_id:
                design_system = DesignSystemService.get_for_project(project_id)
                if design_system and design_system.data:
                    active_stitch_project_id = design_system.data.get("stitch_project_id", "")

            if not active_stitch_project_id:
                create_result = StitchService.create_project(title=ProjectService.get(project_id).name)
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

            result = StitchService.generate_screen(
                project_id=active_stitch_project_id,
                prompt=prompt,
                device_type=device_type,
            )
            content = _extract_stitch_content(result)

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
                generation_finished_at=_utc_now_iso(),
            )
        except Exception as exc:
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
    design_system = DesignSystemService.get_for_project(project_id)
    return render_template(
        "screens/index.html",
        project=project,
        screens=screens,
        design_system=design_system,
        device_labels=DEVICE_TYPES,
    )


@screens_bp.route("/projects/<project_id>/screens/new", methods=["GET", "POST"])
def create(project_id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        device_type = request.form.get("device_type", "DESKTOP")
        description = request.form.get("description", "").strip()
        html_content = request.form.get("html_content", "").strip()
        image_url = request.form.get("image_url", "").strip()

        if not name:
            flash("Screen name is required.", "error")
            return render_template("screens/form.html", project=project,
                                   device_types=DEVICE_TYPES, data={})

        data = {}
        if html_content:
            data["html"] = html_content
        if image_url:
            data["image_url"] = image_url

        screen = ScreenService.create(
            project_id=project_id, name=name,
            device_type=device_type, description=description, data=data,
        )
        flash("Screen created.", "success")
        return redirect(url_for("screens.detail", project_id=project_id, id=screen.id))

    return render_template("screens/form.html", project=project,
                           device_types=DEVICE_TYPES, data={})


@screens_bp.route("/projects/<project_id>/screens/<id>")
def detail(project_id, id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))
    screen = ScreenService.get(id)
    if not screen or screen.project_id != project_id:
        flash("Screen not found.", "error")
        return redirect(url_for("screens.index", project_id=project_id))
    return render_template(
        "screens/detail.html",
        project=project,
        screen=screen,
        device_labels=DEVICE_TYPES,
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

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        device_type = request.form.get("device_type", screen.device_type)
        description = request.form.get("description", "").strip()
        html_content = request.form.get("html_content", "").strip()
        image_url = request.form.get("image_url", "").strip()

        if not name:
            flash("Screen name is required.", "error")
            return render_template("screens/form.html", project=project, screen=screen,
                                   device_types=DEVICE_TYPES, data=screen.data or {})

        data = dict(screen.data or {})
        if html_content:
            data["html"] = html_content
        elif "html" in data and not html_content:
            pass  # keep existing HTML if field left empty
        if image_url:
            data["image_url"] = image_url

        ScreenService.update(screen, name=name, device_type=device_type,
                             description=description, data=data)
        flash("Screen updated.", "success")
        return redirect(url_for("screens.detail", project_id=project_id, id=id))

    return render_template("screens/form.html", project=project, screen=screen,
                           device_types=DEVICE_TYPES, data=screen.data or {})


@screens_bp.route("/projects/<project_id>/screens/<id>/delete", methods=["POST"])
def delete(project_id, id):
    screen = ScreenService.get(id)
    if screen and screen.project_id == project_id:
        ScreenService.delete(screen)
        flash("Screen deleted.", "success")
    return redirect(url_for("screens.index", project_id=project_id))


# --- Stitch Generation routes ---

@screens_bp.route("/projects/<project_id>/screens/generate", methods=["GET", "POST"])
def generate(project_id):
    project = _get_project_or_redirect(project_id)
    if not project:
        return redirect(url_for("projects.index"))

    if request.method == "POST":
        prompt = request.form.get("prompt", "").strip()
        device_type = request.form.get("device_type", "DESKTOP")
        screen_name = request.form.get("name", "").strip() or "Generated Screen"
        stitch_project_id = request.form.get("stitch_project_id", "").strip()

        if not prompt:
            flash("A prompt is required to generate a screen.", "error")
            return render_template("screens/generate.html", project=project,
                                   device_types=DEVICE_TYPES)

        data = {
            "prompt": prompt,
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
                           device_types=DEVICE_TYPES)


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
    return jsonify({"status": "ok"})
