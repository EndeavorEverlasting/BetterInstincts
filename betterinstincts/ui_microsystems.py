"""Semantic Sims UI panels: one glossary, no speculative pixel/Win32 input.

P95 owns the panel/action identity and attested hitbox seam. P124 keeps actual
mouse effects in screen_atlas and the existing cooperative screen queue.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "ui-microsystems.v1.json"
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")
MODES = frozenset({"LIVE", "BUY", "BUILD"})


class UIMicrosystemError(ValueError):
    """An ambiguous or unverified panel must never turn into a click."""


def load_contract(path: Path = CONTRACT) -> dict:
    """Read a bounded, declarative registry; reject weakened safety contracts."""
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 48_000:
        raise UIMicrosystemError("MICROSYSTEM_CONTRACT_UNSAFE")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise UIMicrosystemError("MICROSYSTEM_JSON_INVALID") from exc
    if (not isinstance(data, dict)
            or data.get("schema") != "betterinstincts.ui-microsystems/v1"
            or data.get("policy") != "PER_PANEL_SEMANTIC_TARGET_AND_HITBOX_CENTER_ONLY"
            or data.get("execution", {}).get("default_allowed") is not False
            or data["execution"].get("force_click") is not False
            or data["execution"].get("auto_reclick") is not False):
        raise UIMicrosystemError("MICROSYSTEM_POLICY_INVALID")
    panels = data.get("panels")
    if not isinstance(panels, dict) or not 1 <= len(panels) <= 32:
        raise UIMicrosystemError("MICROSYSTEM_PANELS_INVALID")
    for panel_id, panel in panels.items():
        if not isinstance(panel_id, str) or not TOKEN.fullmatch(panel_id) or not isinstance(panel, dict):
            raise UIMicrosystemError("MICROSYSTEM_PANEL_ID_INVALID")
        modes = panel.get("modes")
        if (not isinstance(modes, list) or not modes or
                not set(modes).issubset(MODES) or len(set(modes)) != len(modes)):
            raise UIMicrosystemError("MICROSYSTEM_MODE_INVALID")
        actions = panel.get("actions")
        if not isinstance(actions, dict) or len(actions) > 24:
            raise UIMicrosystemError("MICROSYSTEM_ACTIONS_INVALID")
        if panel.get("family") in {"UNRESOLVED_LABEL", "COMPOSITE_READ_ONLY"}:
            if actions:
                raise UIMicrosystemError("MICROSYSTEM_UNRESOLVED_MUST_HAVE_NO_ACTIONS")
            continue
        cues = panel.get("cues")
        if (not isinstance(cues, dict) or set(cues) != {"visual", "operator"}
                or not all(isinstance(v, str) and TOKEN.fullmatch(v) for v in cues.values())):
            raise UIMicrosystemError("MICROSYSTEM_TWO_CUES_REQUIRED")
        for action_id, action in actions.items():
            if (not isinstance(action_id, str) or not TOKEN.fullmatch(action_id)
                    or not isinstance(action, dict)
                    or action.get("status") != "REQUIRES_EXACT_BUILD_HITBOX_ATTESTATION"):
                raise UIMicrosystemError("MICROSYSTEM_ACTION_UNSAFE")
    return data


def inventory(*, cfg: dict | None = None) -> dict:
    """Agent-facing discoverability; declared actions are never click permits."""
    cfg = cfg or load_contract()
    return {
        "schema": "betterinstincts.ui-microsystems.inventory/v1",
        "panels": {
            panel_id: {
                "family": panel["family"],
                "modes": list(panel["modes"]),
                "status": panel["status"],
                "actions": sorted(panel["actions"]),
                "cues": panel.get("cues"),
                "open_hotkey_id": panel.get("open_hotkey_id"),
                "open_chord": list(panel.get("open_chord") or []) or None,
                "execute_allowed": False,
            }
            for panel_id, panel in cfg["panels"].items()
        },
        "bottom_right_panel_hotkeys": dict(cfg.get("bottom_right_panel_hotkeys") or {}),
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
    }


def normalize_bottom_right_panel_id(panel_id: str, *, cfg: dict | None = None) -> str:
    """Resolve work/school/inventory aliases to canonical microsystem panel ids."""
    cfg = cfg or load_contract()
    raw = str(panel_id or "").strip().casefold()
    if not raw:
        raise UIMicrosystemError("BOTTOM_RIGHT_PANEL_ID_REQUIRED")
    table = (cfg.get("bottom_right_panel_hotkeys") or {}).get("aliases") or {}
    if not isinstance(table, dict):
        table = {}
    canonical = str(table.get(raw) or raw)
    panels = (cfg.get("bottom_right_panel_hotkeys") or {}).get("panels") or {}
    if canonical not in panels and canonical not in (cfg.get("panels") or {}):
        raise UIMicrosystemError("UNKNOWN_BOTTOM_RIGHT_PANEL:" + raw)
    return canonical


def plan_open_bottom_right_panel(panel_id: str, *, cfg: dict | None = None) -> dict:
    """Hotkey-first plan to open a Live bottom-right panel (J=work, G=aspirations, …).

    Requires live-hotkey-arm before the letter. Does not authorize SendInput and
    does not claim the panel is visible until independent cues confirm it.
    """
    cfg = cfg or load_contract()
    from betterinstincts.ui_chrome import resolve_bottom_right_panel_hotkey

    canonical = normalize_bottom_right_panel_id(panel_id, cfg=cfg)
    hotkey = resolve_bottom_right_panel_hotkey(canonical)
    panel = (cfg.get("panels") or {}).get(canonical) or {}
    return {
        "schema": "betterinstincts.ui-microsystems.open-bottom-right/v1",
        "state": "BR_PANEL_HOTKEY_PLANNED",
        "panel_id": canonical,
        "requested_panel": panel_id,
        "hotkey_id": hotkey["hotkey_id"],
        "chord": list(hotkey["chord"]),
        "channel": "HOTKEY",
        "order": [
            "ARM_LIVE_HOTKEYS",
            "PRESS_PANEL_LETTER",
            "CONFIRM_PANEL_CUES",
        ],
        "requires_live_hotkey_arm": True,
        "requires_entitlement_attestation": bool(
            hotkey.get("requires_entitlement_attestation")
            or panel.get("requires_entitlement_attestation")
        ),
        "panel_cues": panel.get("cues"),
        "mouse_fallback": "FORBIDDEN_WHILE_HOTKEY_CATALOGUED",
        "execute_allowed": False,
        "proof_ceiling": "BR_PANEL_HOTKEY_PLAN_NOT_LIVE_PANEL_PROOF",
        "note": (
            "G=aspirations J=career/work L=skills R=relationships "
            "I=inventory Y=simology O=needs U=clubs"
        ),
    }


def resolve_action(
    panel_id: str, target_id: str, *, mode: str, cfg: dict | None = None
) -> dict:
    """Resolve a semantic target to the correct panel, never to a guessed point."""
    cfg = cfg or load_contract()
    if not isinstance(panel_id, str) or not isinstance(target_id, str):
        raise UIMicrosystemError("PANEL_AND_TARGET_REQUIRED")
    panel = cfg["panels"].get(panel_id)
    if panel is None:
        raise UIMicrosystemError("UNKNOWN_PANEL")
    if panel["family"] in {"UNRESOLVED_LABEL", "COMPOSITE_READ_ONLY"}:
        raise UIMicrosystemError("PANEL_NOT_A_CLICK_SURFACE")
    if mode not in panel["modes"]:
        raise UIMicrosystemError("PANEL_WRONG_MODE")
    prefix = panel_id + "."
    if not target_id.startswith(prefix) or target_id[len(prefix):] not in panel["actions"]:
        raise UIMicrosystemError("TARGET_NOT_IN_PANEL")
    return {
        "panel_id": panel_id, "target_id": target_id, "mode": mode,
        "panel_cues": panel["cues"],
        "requires_entitlement_attestation": panel.get("requires_entitlement_attestation", False),
        "status": "REQUIRES_EXACT_BUILD_HITBOX_ATTESTATION",
        "execute_allowed": False,
    }


def validate_hitbox_calibration(
    calibration: Mapping[str, Any], *, mode: str, width: int, height: int
) -> dict:
    """Accept only a centered click within an attested rectangle of this panel.

    The native host supplies physical screenshot evidence, scene, layout and
    selected-Sim revisions independently. This function never manufactures it.
    """
    if not isinstance(calibration, Mapping):
        raise UIMicrosystemError("PANEL_CALIBRATION_INVALID")
    resolved = resolve_action(calibration.get("panel_id"), calibration.get("target_id"), mode=mode)
    rectangle = calibration.get("hitbox")
    if (not isinstance(rectangle, list) or len(rectangle) != 4
            or any(type(v) is not int for v in rectangle)):
        raise UIMicrosystemError("PANEL_HITBOX_REQUIRED")
    left, top, right, bottom = rectangle
    if (not 0 <= left < right < width or not 0 <= top < bottom < height
            or min(right-left, bottom-top) < 8):
        raise UIMicrosystemError("PANEL_HITBOX_OUT_OF_BOUNDS")
    center = [(left + right) // 2, (top + bottom) // 2]
    if [calibration.get("x"), calibration.get("y")] != center:
        raise UIMicrosystemError("PANEL_CLICK_MUST_BE_HITBOX_CENTER")
    for field in ("ui_layout_revision", "selected_sim_revision"):
        if not isinstance(calibration.get(field), str) or not TOKEN.fullmatch(calibration[field]):
            raise UIMicrosystemError("PANEL_REVISION_REQUIRED:" + field)
    if (resolved["requires_entitlement_attestation"]
            and calibration.get("entitlement_attested") is not True):
        raise UIMicrosystemError("PANEL_ENTITLEMENT_UNVERIFIED")
    return {
        **resolved,
        "hitbox": list(rectangle),
        "ui_layout_revision": calibration["ui_layout_revision"],
        "selected_sim_revision": calibration["selected_sim_revision"],
        "entitlement_attested": bool(calibration.get("entitlement_attested", False)),
        "click": center,
    }


def panel_observation_matches(observation: Mapping[str, Any], resolved: Mapping[str, Any]) -> bool:
    """Recheck panel, visibility, occlusion and geometry at each action boundary."""
    if not isinstance(observation, Mapping) or not isinstance(resolved, Mapping):
        return False
    expected = {
        "panel_id": resolved["panel_id"],
        "panel_visible": True,
        "panel_hitbox": resolved["hitbox"],
        "ui_layout_revision": resolved["ui_layout_revision"],
        "selected_sim_revision": resolved["selected_sim_revision"],
        "panel_obscured": False,
        "panel_animation_stable": True,
        "target_enabled": True,
    }
    if any(type(observation.get(k)) is not type(v) or observation.get(k) != v for k, v in expected.items()):
        return False
    if resolved.get("requires_entitlement_attestation") and observation.get("entitlement_attested") is not True:
        return False
    cues = observation.get("panel_cues")
    expected_cues = resolved["panel_cues"]
    return (isinstance(cues, list) and len(cues) == 2
            and all(isinstance(c, dict) and set(c) == {"source", "token"} for c in cues)
            and {c["source"]: c["token"] for c in cues} == expected_cues)
