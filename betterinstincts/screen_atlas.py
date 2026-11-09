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

from betterinstincts.camera_traverse import assess_drift_recovery, classify_cursor, safe_rest_point
from betterinstincts.scenes import load_catalog
from betterinstincts.ui_chrome import glossary_snapshot, load_contract as load_chrome, resolve_target
from betterinstincts.workflow_interop import CooperativeScreenQueue, QueuedStep

ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / "contracts" / "screen-atlas.v1.json"
CONSOLE = ROOT / "contracts" / "hidden-object-discovery.v1.json"
HOST_MENU = ROOT / "contracts" / "host-menu.v1.json"
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
    menu = _bounded_json(HOST_MENU, 180_000)
    if menu.get("schema") != "betterinstincts.host-menu/v1" or menu.get("game_version") != scene["game_version"]:
        raise ScreenAtlasError("HOST_MENU_VERSION_OR_SCHEMA_DRIFT")
    by_scene = {scene_id: mode for mode, scene_id in atlas["mode_scenes"].items()}
    screens = []
    for row in scene["scenes"]:
        mode = by_scene.get(row["id"])
        transitions = []
        for transition in menu["transitions"]:
            if transition.get("from") == row["id"] and "click" in transition:
                transitions.append({
                    "id": transition["id"], "to": transition["to"],
                    "client_point": list(transition["click"]),
                    "status": "HISTORICAL_HOST_CANDIDATE_RECALIBRATE",
                    "execute_allowed": False,
                })
        targets = list(modes[mode]["targets"]) if mode else []
        screens.append({
            "scene_id": row["id"], "mode": mode,
            "required_cues": row["required_cues"],
            "target_ids": targets,
            "menu_clicks": transitions,
            "unmapped": not bool(targets or transitions),
            "execute_allowed": False,
        })
    return {
        "schema": "betterinstincts.screen-atlas.inventory/v1",
        "exact_game_version": scene["game_version"],
        "modes": modes,
        "scenes": [s["id"] for s in scene["scenes"]],
        "screen_maps": screens,
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


def _native_owner(obs: Mapping[str, Any], process_id: int, session_id: str) -> bool:
    """Single exact-window, exact-session provenance gate for native clicks."""
    return (isinstance(obs, Mapping)
            and type(obs.get("process_id")) is int
            and obs.get("process_id") == process_id
            and type(obs.get("focused_process_id")) is int
            and obs.get("focused_process_id") == process_id
            and obs.get("session_id") == session_id
            and obs.get("host_admitted") is True
            and _valid_int(obs.get("client_origin_x"), -20_000, 20_000)
            and _valid_int(obs.get("client_origin_y"), -20_000, 20_000))


def enqueue_native_game_click(
    queue: CooperativeScreenQueue, *, work_id: str,
    calibration: Mapping[str, Any],
    observe: Callable[[], Awaitable[Mapping[str, Any]]],
    process_id: int, session_id: str,
    click_screen: Callable[[int, int], Awaitable[None]],
    move_screen: Callable[[int, int], Awaitable[None]],
) -> dict:
    """Win32-compatible *injected port*, not a second native input owner.

    Caller must supply exact-PID/window-bounds observation and admitted
    click/move functions from the existing local Sims host. This interface
    never calls Win32 directly or changes a save. Queue owns 15s idle + lock.
    """
    resolved = resolved_calibration(calibration)
    if (not _valid_int(process_id, 1, 2_147_483_647)
            or not isinstance(session_id, str) or not EVIDENCE_ID.fullmatch(session_id)
            or not callable(observe) or not callable(click_screen) or not callable(move_screen)):
        raise ScreenAtlasError("EXACT_NATIVE_HOST_PORT_REQUIRED")


    async def validate() -> bool:
        obs = await observe()
        return _native_owner(obs, process_id, session_id) and _observation_matches(obs, resolved)

    async def action(checkpoint) -> None:
        if not await validate():
            raise ScreenAtlasError("NATIVE_TARGET_STALE")
        await checkpoint()
        obs = await observe()
        if not _native_owner(obs, process_id, session_id) or not _observation_matches(obs, resolved):
            raise ScreenAtlasError("NATIVE_TARGET_CHANGED_AT_EFFECT")
        origin = (obs["client_origin_x"], obs["client_origin_y"])
        point = (origin[0] + resolved["click"][0], origin[1] + resolved["click"][1])
        try:
            await click_screen(*point)
        finally:
            # The game may change scene after click; verify desktop ownership
            # and stable window geometry, not the clicked target's visibility.
            await checkpoint()
            after = await observe()
            if (not _native_owner(after, process_id, session_id) or
                    (after["client_origin_x"], after["client_origin_y"]) != origin or
                    (after.get("client_width"), after.get("client_height")) !=
                    (resolved["client_width"], resolved["client_height"])):
                raise ScreenAtlasError("WINDOW_MOVED_OR_CONTROL_CHANGED_BEFORE_REST")
            await move_screen(
                origin[0] + resolved["safe_rest"][0],
                origin[1] + resolved["safe_rest"][1],
            )

    queue.enqueue(QueuedStep(work_id=work_id, validate=validate, action=action))
    return {"state": "QUEUED_REQUIRES_NATIVE_HOST_REVALIDATION",
            "work_id": work_id, "target_id": resolved["target_id"],
            "safe_rest_client": resolved["safe_rest"],
            "execute_allowed": False, "proof_ceiling": resolved["proof_ceiling"]}



def enqueue_world_game_click(
    queue: CooperativeScreenQueue, *, work_id: str, target_id: str,
    capture_ref: str, client_width: int, client_height: int,
    observe: Callable[[], Awaitable[Mapping[str, Any]]],
    process_id: int, session_id: str,
    click_screen: Callable[[int, int], Awaitable[None]],
    move_screen: Callable[[int, int], Awaitable[None]],
) -> dict:
    """Native world-object click at *current camera* pixels only.

    Unlike fixed HUD chrome, a world object's click point changes after any
    pan, recenter, zoom, or drift. The canonical camera recovery owner must
    declare STABLE+FRAMED on every observation, and the camera revision must
    remain identical through the final effect checkpoint. Never retry a click.
    """
    if not isinstance(queue, CooperativeScreenQueue) or not (
        _valid_int(process_id, 1, 2_147_483_647)
        and isinstance(session_id, str) and EVIDENCE_ID.fullmatch(session_id)
        and callable(observe) and callable(click_screen) and callable(move_screen)
    ):
        raise ScreenAtlasError("WORLD_CLICK_HOST_PORT_INVALID")
    if not isinstance(target_id, str) or not 1 <= len(target_id) <= 96:
        raise ScreenAtlasError("WORLD_CLICK_TARGET_INVALID")
    if not isinstance(capture_ref, str) or not EVIDENCE_ID.fullmatch(capture_ref):
        raise ScreenAtlasError("WORLD_CLICK_CAPTURE_REF_INVALID")
    anchor: dict[str, Any] = {}

    async def fresh_world_frame() -> dict | None:
        obs = await observe()
        if not _native_owner(obs, process_id, session_id):
            return None
        if obs.get("game_version") != load_catalog()["game_version"] or obs.get("capture_quality") != "CONTENT_PRESENT":
            return None
        if obs.get("mode") not in ("LIVE", "BUY", "BUILD") or obs.get("viewport_state") != "NORMAL":
            return None
        cues = obs.get("independent_cues")
        if not isinstance(cues, list) or len(cues) != 2 or (
            {c.get("source") for c in cues if isinstance(c, Mapping)} != {"visual", "operator"}
        ) or not all(isinstance(c, Mapping) and isinstance(c.get("token"), str) and c.get("token") for c in cues):
            return None
        try:
            candidate = assess_drift_recovery(
                target_kind="WORLD_OBJECT", capture_ref=capture_ref,
                observation=obs, client_width=client_width,
                client_height=client_height, target_id=target_id,
                world_target_observation=obs.get("world_target"),
            )
        except (ValueError, TypeError):
            return None
        if candidate["state"] != "CAMERA_STABLE_TARGET_FRAMED" or candidate["world_click_ready"] is not True:
            return None
        if (obs.get("client_width"), obs.get("client_height")) != (client_width, client_height):
            return None
        return {
            "revision": candidate["camera_revision"],
            "clock_revision": candidate.get("clock_revision"),
            "click": tuple(candidate["target_framing"]["click_candidate"]),
            "origin": (obs["client_origin_x"], obs["client_origin_y"]),
            "safe_rest": tuple(candidate["safe_rest"]["client"]),
        }

    async def validate() -> bool:
        frame = await fresh_world_frame()
        if frame is None:
            return False
        if anchor:
            return frame == anchor
        anchor.update(frame)
        return True

    async def action(checkpoint) -> None:
        await checkpoint()
        if not await validate():
            raise ScreenAtlasError("WORLD_CLICK_STALE_CAMERA_OR_CURSOR")
        # One admitted action from a camera-bound, verified position.
        x = anchor["origin"][0] + anchor["click"][0]
        y = anchor["origin"][1] + anchor["click"][1]
        try:
            await click_screen(x, y)
        finally:
            # No blind replay after effect or human interruption.
            await checkpoint()
            after = await observe()
            if not _native_owner(after, process_id, session_id) or (
                after.get("client_origin_x"), after.get("client_origin_y")
            ) != anchor["origin"] or (
                after.get("client_width"), after.get("client_height")
            ) != (client_width, client_height):
                raise ScreenAtlasError("WORLD_CLICK_REST_OWNER_CHANGED")
            await move_screen(
                anchor["origin"][0] + anchor["safe_rest"][0],
                anchor["origin"][1] + anchor["safe_rest"][1],
            )

    queue.enqueue(QueuedStep(work_id=work_id, validate=validate, action=action))
    return {
        "state": "QUEUED_WORLD_CLICK_REQUIRES_STABLE_CAMERA",
        "work_id": work_id, "target_id": target_id,
        "capture_ref": capture_ref, "execute_allowed": False,
        "proof_ceiling": "OFFLINE_CAMERA_REVISION_GUARD_NOT_LIVE_CLICK_CERTIFIED",
    }
