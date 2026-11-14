"""Read-only Sims 4 bottom-right panel intelligence.

A pixel sensor and an intent planner, NOT an input injector or Sims mod.
Only the personal-inventory anchor is attested for the 1919x1079,
1.121.361.1020 operator captures. Unseen panel types fail closed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


PROFILE = (1919, 1079)
PATCH = "1.121.361.1020"
PANEL = "personal_inventory"
MIN_HEADER_Y = 727
MAX_HEADER_Y = 217


@dataclass(frozen=True)
class PanelState:
    panel_id: str
    visibility: str  # COLLAPSED | CONDENSED | EXPANDED | UNKNOWN
    expansion: float | None
    header_y: int | None
    inventory_scroll: str  # always UNKNOWN unless a separate sensor proves it
    selected_sim: str  # never inferred from the pixels used here
    cue_status: str
    source: str = "HOST_PIXEL_SENSOR_V1"
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _blue(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb[:3]
    return b > 85 and b > r + 25 and g > r + 15 and g > 50 and r < 120


def _best_blue_row(pixels: Any, xs: range, ys: range) -> tuple[int | None, int]:
    best_y, best_count = None, 0
    for y in ys:
        count = sum(_blue(pixels[x, y]) for x in xs)
        if count > best_count:
            best_y, best_count = y, count
    return best_y, best_count


def observe_inventory_image(image: Any, *, mode: str, patch: str = PATCH) -> PanelState:
    """Two independent UI text-color bands locate inventory on supported captures.

    No OCR/model verdict is required; never claim other panels can be sensed.
    Missing both cues means this *module* is collapsed, not that all HUD is hidden.
    """
    def unknown(why: str) -> PanelState:
        return PanelState(PANEL, "UNKNOWN", None, None, "UNKNOWN", "UNKNOWN", why)
    if mode != "LIVE" or patch != PATCH:
        return unknown("UNATTESTED_GAME_MODE_OR_PATCH")
    if getattr(image, "size", None) != PROFILE:
        return unknown("UNATTESTED_IMAGE_GEOMETRY")
    pixels = image.convert("RGB").load()
    title_y, title_count = _best_blue_row(pixels, range(1520, 1660), range(180, 880))
    _, sale_count = _best_blue_row(pixels, range(1640, 1800), range(965, 1020))
    title = title_count >= 40
    sale = sale_count >= 50
    if not title and not sale:
        return PanelState(PANEL, "COLLAPSED", 0.0, None, "UNKNOWN", "UNKNOWN", "TWO_CUES_ABSENT")
    if not (title and sale and title_y is not None):
        return unknown("CUE_DISAGREEMENT")
    header_y = title_y - 30
    if not 190 <= header_y <= 780:
        return unknown("UNATTESTED_HEADER_POSITION")
    expansion = round(max(0.0, min(1.0, (MIN_HEADER_Y - header_y) / (MIN_HEADER_Y - MAX_HEADER_Y))), 3)
    visibility = "EXPANDED" if expansion >= 0.97 else "CONDENSED"
    return PanelState(PANEL, visibility, expansion, header_y, "UNKNOWN", "UNKNOWN", "TWO_CUES_PRESENT")


def observe_inventory_png(path: str, *, mode: str, patch: str = PATCH) -> PanelState:
    """Optional host-only Pillow bridge. Never imported by native Sims runtime."""
    from PIL import Image
    with Image.open(path) as image:
        return observe_inventory_image(image, mode=mode, patch=patch)


def classify_calibrated_bounds(
    *, panel_id: str, top_y: int, min_y: int, max_y: int,
    independent_cues: int, mode: str = "LIVE"
) -> PanelState:
    """Universal state semantics for a future *independently calibrated* module.

    Caller supplies observed physical bounds from its registered sensor, not
    a language-model prediction. No vision implementation is implied.
    """
    if (mode != "LIVE" or not panel_id or independent_cues < 2
            or any(type(v) is not int for v in (top_y, min_y, max_y))
            or not (0 <= max_y < min_y) or not max_y <= top_y <= min_y):
        return PanelState(panel_id, "UNKNOWN", None, None, "UNKNOWN", "UNKNOWN", "GEOMETRY_UNATTESTED")
    expansion = round((min_y - top_y) / (min_y - max_y), 3)
    return PanelState(panel_id, "EXPANDED" if expansion >= .97 else "CONDENSED",
                      expansion, top_y, "UNKNOWN", "UNKNOWN", "CALIBRATED_TWO_CUES")


def propose_panel_posture(
    observed: PanelState, *, intent: str, operator_idle: bool,
    panel_owner: str, current_visible_panel_id: str | None,
    scene_fresh: bool, sim_fresh: bool
) -> dict[str, Any]:
    """Pure intent-to-posture selection; every proposal is NON-EXECUTABLE.

    Semantics: expanded for long scans, condensed for one status/item,
    collapsed only after host-owned work; other people's panels stay intact.
    No scroll action is implied by a resize, and no cursor moves are issued.
    """
    result: dict[str, Any] = {
        "schema": "betterinstincts.hud-panel-proposal/v1",
        "panel_id": observed.panel_id, "observed": observed.visibility,
        "intent": intent, "op": "HOLD", "requested": None,
        "execute_allowed": False,
        "effect_owner": "EXISTING_COOPERATIVE_SCREEN_QUEUE_ONLY",
    }
    # An unknown/None visible-panel identity is not proof of an empty HUD.
    # Require a specifically witnessed empty position for opening a closed
    # module, or the exact same active module before resize or close.
    focus_matches = (current_visible_panel_id == "NONE" if observed.visibility == "COLLAPSED"
                     else current_visible_panel_id == observed.panel_id)
    if (not operator_idle or panel_owner != "HOST" or not scene_fresh or not sim_fresh
            or not focus_matches or observed.visibility == "UNKNOWN"):
        result["reason"] = "PLAYER_OR_OBSERVATION_GATE"
        return result
    if intent in ("LONG_LIST", "INVENTORY_AUDIT", "SCROLL_SEARCH"):
        desired, target = "EXPANDED", 1.0
    elif intent in ("QUICK_STATUS", "SINGLE_ITEM"):
        desired, target = "CONDENSED", 0.18
    elif intent == "FINISHED":
        desired, target = "COLLAPSED", 0.0
    else:
        result["reason"] = "UNRECOGNIZED_INTENT_PRESERVE"
        return result
    result["requested"] = desired
    if desired == "COLLAPSED":
        result["op"] = "NOOP" if observed.visibility == "COLLAPSED" else "REQUEST_EXISTING_HOTKEY_CLOSE"
    elif observed.visibility == "COLLAPSED":
        result["op"] = "REQUEST_EXISTING_HOTKEY_OPEN_THEN_REOBSERVE"
    elif observed.expansion is None:
        result["reason"] = "NO_MEASURED_EXPANSION"
    elif desired == "EXPANDED" and observed.expansion >= .97:
        result["op"] = "NOOP"
    elif desired == "CONDENSED" and observed.expansion <= .24:
        result["op"] = "NOOP"
    else:
        result["op"] = "REQUEST_CALIBRATED_RESIZE_THEN_REOBSERVE"
        result["target_expansion"] = target
    result["reason"] = result.get("reason", "SAFE_NON_EFFECT_PROPOSAL_ONLY")
    return result
