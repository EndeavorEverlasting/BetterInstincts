"""Machine-readable Sims screen atlas and cooperative Playwright-hosted game click.

Reuse the canonical UI chrome, scene, camera and console owners. The atlas is
read-only until a P08 exact-game calibration and an independent host observation
are injected. It NEVER starts Playwright, discovers saves or controls Win32.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Awaitable, Callable, Mapping

from betterinstincts.camera_traverse import classify_cursor, safe_rest_point
from betterinstincts.scenes import load_catalog
from betterinstincts.ui_chrome import glossary_snapshot, load_contract as load_chrome, resolve_target
from betterinstincts.workflow_interop import CooperativeScreenQueue, QueuedStep

ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / "contracts" / "screen-atlas.v1.json"
CONSOLE = ROOT / "contracts" / "hidden-object-discovery.v1.json"
EVIDENCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")


class ScreenAtlasError(ValueError):
    """Unsafe or stale map data; never guess a game-screen target."""


def _bounded_json(path: Path, limit: int) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ScreenAtlasError("ATLAS_SOURCE_UNSAFE")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ScreenAtlasError("ATLAS_JSON_INVALID") from exc
    if not isinstance(obj, dict):
        raise ScreenAtlasError("ATLAS_JSON_NOT_OBJECT")
    return obj


def load_atlas(path: Path = ATLAS) -> dict:
    atlas = _bounded_json(path, 180_000)
    if atlas.get("schema") != "betterinstincts.screen-atlas/v1" or atlas.get("policy") != "OBSERVE_VERIFY_SINGLE_ACTION_SAFE_REST":
        raise ScreenAtlasError("ATLAS_CONTRACT_INVALID")
    if atlas.get("mode_scenes") != {"LIVE": "live_mode", "BUY": "buy_mode", "BUILD": "build_mode"}:
        raise ScreenAtlasError("ATLAS_MODE_SCENES_INVALID")
    if atlas.get("execution", {}).get("default_allowed") is not False or atlas["execution"].get("cooperative_queue_only") is not True:
        raise ScreenAtlasError("ATLAS_EXECUTION_UNSAFE")
    if atlas.get("mouse", {}).get("rest_requires_fresh_presence_checkpoint") is not True:
        raise ScreenAtlasError("ATLAS_MOUSE_REST_UNSAFE")
    return atlas


def inventory(*, atlas: dict | None = None) -> dict:
    """Dynamic inventory: existing contracts own names, modes and console lines."""
    atlas = atlas or load_atlas()
    chrome = load_chrome()
    scene = load_catalog()
    console = _bounded_json(CONSOLE, 180_000)
    if console.get("schema") != "betterinstincts.hidden-object-discovery/v1":
        raise ScreenAtlasError("CONSOLE_OWNER_SCHEMA_UNKNOWN")
    modes = glossary_snapshot(chrome)["modes"]
    return {
        "schema": "betterinstincts.screen-atlas.inventory/v1",
        "exact_game_version": scene["game_version"],
        "modes": modes,
        "scenes": [s["id"] for s in scene["scenes"]],
        "console": {
            "source": "contracts/hidden-object-discovery.v1.json",
            "toggle_chords": console["platform_console_chords"],
            "ordered_commands": [{"line": s, "execute_allowed": False, "review": "EACH_MUTATION_REQUIRES_CONSENT"} for s in console["ordered_console_lines"]],
            "optional_command": {"line": console["optional_live_edit_line"], "execute_allowed": False, "review": "EXPLICIT_OPT_IN"},
            "coverage": "KNOWN_CURATED_COMMANDS_NOT_COMPLETE_GAME_CONSOLE",
        },
        "execute_allowed": False,
        "proof_ceiling": atlas["proof_ceiling"],
    }


def _valid_int(value: Any, minimum: int, maximum: int) -> bool:
    return type(value) is int and minimum <= value <= maximum


def resolved_calibration(
    calibration: Mapping[str, Any], *, atlas: dict | None = None
) -> dict:
    """Check exact-build, mode, size, target and evidence before issuing a point.

    A supplied calibration attests one target; the atlas cannot infer an
    operator's proof or promote candidate ui_chrome points on its own.
    """
    atlas = atlas or load_atlas()
    if not isinstance(calibration, Mapping) or len(json.dumps(dict(calibration))) > 8192:
        raise ScreenAtlasError("CALIBRATION_INVALID")
    keys = atlas["calibration"]["required"]
    if any(k not in calibration for k in keys):
        raise ScreenAtlasError("CALIBRATION_INCOMPLETE")
    scene = load_catalog()
    if calibration["game_version"] != scene["game_version"]:
        raise ScreenAtlasError("UNKNOWN_GAME_PATCH")
    mode = calibration["mode"]
    if mode not in atlas["mode_scenes"]:
        raise ScreenAtlasError("UNKNOWN_MODE")
    if calibration["status"] != atlas["calibration"]["status_required"] or not isinstance(calibration["evidence_ref"], str) or not EVIDENCE_ID.fullmatch(calibration["evidence_ref"]):
        raise ScreenAtlasError("VERIFIED_CALIBRATION_REQUIRED")
    width, height = calibration["client_width"], calibration["client_height"]
    if not (_valid_int(width, 320, 4000) and _valid_int(height, 240, 4000) and width * height <= 16_000_000):
        raise ScreenAtlasError("CLIENT_DIMENSIONS_UNSAFE")
    profile = calibration["profile"]
    chrome = load_chrome()
    if profile not in chrome["resolution_profiles"]:
        raise ScreenAtlasError("UNKNOWN_PROFILE")
    size = chrome["resolution_profiles"][profile]
    if width != size["width"] or height != size["height"]:
        raise ScreenAtlasError("PROFILE_GEOMETRY_MISMATCH")
    # Existing target/mode owner rejects missing target, cross-mode or stub.
    candidate = resolve_target(calibration["target_id"], mode=mode, profile=profile, client_width=width, client_height=height, cfg=chrome)
    x, y = calibration["x"], calibration["y"]
    if not (_valid_int(x, 0, width - 1) and _valid_int(y, 0, height - 1)):
        raise ScreenAtlasError("TARGET_PIXEL_OUT_OF_BOUNDS")
    rest = safe_rest_point(client_width=width, client_height=height)
    cx, cy = rest["client"]
    if classify_cursor(cx, cy, client_width=width, client_height=height)["in_edge_band"]:
        raise ScreenAtlasError("NO_SAFE_CURSOR_REST")
    return {
        "target_id": candidate["target_id"], "mode": mode,
        "scene_id": atlas["mode_scenes"][mode],
        "game_version": scene["game_version"], "profile": profile,
        "client_width": width, "client_height": height,
        "click": [x, y], "safe_rest": [cx, cy],
        "evidence_ref": calibration["evidence_ref"], "execute_allowed": False,
        "proof_ceiling": atlas["proof_ceiling"],
    }


def _observation_matches(observation: Mapping[str, Any], resolved: Mapping[str, Any]) -> bool:
    """Host-supplied live check; two independent cues, not cached hotkey hints."""
    if not isinstance(observation, Mapping):
        return False
    expected = {
        "game_version": resolved["game_version"], "mode": resolved["mode"],
        "scene_id": resolved["scene_id"], "profile": resolved["profile"],
        "client_width": resolved["client_width"], "client_height": resolved["client_height"],
        "target_id": resolved["target_id"], "capture_quality": "CONTENT_PRESENT",
        "viewport_state": "NORMAL", "target_visible": True,
        "player_queue_owned": False, "save_authorized": True,
    }
    if any(type(observation.get(k)) is not type(v) or observation.get(k) != v for k, v in expected.items()):
        return False
    cues = observation.get("independent_cues")
    return (isinstance(cues, list) and len(cues) == 2
            and {c.get("source") for c in cues if isinstance(c, dict)} == {"visual", "operator"}
            and all(isinstance(c.get("token"), str) and 1 <= len(c["token"]) <= 80 for c in cues if isinstance(c, dict)))


def enqueue_game_click(
    queue: CooperativeScreenQueue, *, work_id: str, page: Any,
    calibration: Mapping[str, Any],
    observe: Callable[[], Awaitable[Mapping[str, Any]]],
) -> dict:
    """One opt-in Playwright page.mouse click and cursor park.

    Only works where the game is actually in the existing Playwright page.
    The native Sims executable needs its independent Win32 host adapter.
    Never opens a browser and never treats a target declaration as authority.
    """
    resolved = resolved_calibration(calibration)
    if not callable(observe) or not hasattr(page, "mouse") or not hasattr(page.mouse, "click") or not hasattr(page.mouse, "move"):
        raise ScreenAtlasError("EXISTING_PLAYWRIGHT_PAGE_REQUIRED")

    async def validate() -> bool:
        if page.is_closed():
            return False
        return _observation_matches(await observe(), resolved)

    async def action(checkpoint) -> None:
        if not await validate():
            raise ScreenAtlasError("TARGET_STALE_BEFORE_EFFECT")
        await checkpoint()
        if not await validate():
            raise ScreenAtlasError("TARGET_STALE_AT_EFFECT")
        x, y = resolved["click"]
        try:
            await page.mouse.click(x, y)
        finally:
            # Move only while still admitted: never steal mouse from player.
            # A post-click interruption defers rest and quarantines the job,
            # avoiding a second click after an ambiguous first outcome.
            await checkpoint()
            await page.mouse.move(*resolved["safe_rest"])

    queue.enqueue(QueuedStep(work_id=work_id, validate=validate, action=action))
    return {"state": "QUEUED_REQUIRES_LIVE_REVALIDATION", "work_id": work_id,
            "target_id": resolved["target_id"], "safe_rest": resolved["safe_rest"],
            "execute_allowed": False, "proof_ceiling": resolved["proof_ceiling"]}
