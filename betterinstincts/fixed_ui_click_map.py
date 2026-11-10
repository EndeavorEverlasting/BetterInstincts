"""Fixed-HUD click ledger: record every agent click; learn attested coords.

Moving world/Sim targets are out of scope — use a separate system.
Never SendInput from this module.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "fixed-ui-click-map.v1.json"
DEFAULT_LEDGER = ROOT / "dist" / "game-host" / "fixed-ui-click-ledger.json"
MAX_BYTES = 256_000


class FixedUiClickMapError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise FixedUiClickMapError("FIXED_UI_CLICK_MAP_CONTRACT_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.fixed-ui-click-map/v1":
        raise FixedUiClickMapError("BAD_FIXED_UI_CLICK_MAP_SCHEMA")
    if cfg.get("execute_allowed_default") is not False:
        raise FixedUiClickMapError("FIXED_UI_MAP_MUST_DEFAULT_EXECUTE_FALSE")
    return cfg


def default_ledger_path(cfg: Optional[dict] = None) -> Path:
    cfg = cfg or load_contract()
    rel = str(cfg.get("ledger_path_default") or "dist/game-host/fixed-ui-click-ledger.json")
    path = Path(rel)
    return path if path.is_absolute() else ROOT / path


def empty_ledger(*, profile: str = "1920x1080") -> dict:
    return {
        "schema": "betterinstincts.fixed-ui-click-ledger/v1",
        "profile": profile,
        "targets": {},
        "attempts": [],
        "note": "Append-only click attempts for FIXED HUD only. Moving targets forbidden.",
    }


def load_ledger(path: Path | None = None) -> dict:
    path = Path(path) if path is not None else default_ledger_path()
    if not path.is_file():
        return empty_ledger()
    if path.is_symlink() or path.stat().st_size > MAX_BYTES:
        raise FixedUiClickMapError("FIXED_UI_LEDGER_UNSAFE")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.fixed-ui-click-ledger/v1":
        raise FixedUiClickMapError("BAD_FIXED_UI_LEDGER_SCHEMA")
    if not isinstance(data.get("attempts"), list):
        data["attempts"] = []
    if not isinstance(data.get("targets"), dict):
        data["targets"] = {}
    return data


def save_ledger(ledger: Mapping[str, object], path: Path | None = None) -> Path:
    path = Path(path) if path is not None else default_ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(ledger), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def seed_targets_from_contract(cfg: Optional[dict] = None) -> dict:
    """Return seed target rows for the default resolution profile."""
    cfg = cfg or load_contract()
    seeds = cfg.get("seed_targets_1920x1080") or {}
    if not isinstance(seeds, Mapping):
        raise FixedUiClickMapError("SEED_TARGETS_REQUIRED")
    out: dict[str, dict] = {}
    for tid, row in seeds.items():
        if not isinstance(row, Mapping):
            continue
        xy = row.get("client_xy")
        if not (
            isinstance(xy, (list, tuple))
            and len(xy) == 2
            and all(isinstance(v, int) for v in xy)
        ):
            continue
        out[str(tid)] = {
            "target_id": str(tid),
            "role": str(row.get("role") or ""),
            "client_xy": [int(xy[0]), int(xy[1])],
            "status": str(row.get("status") or "CANDIDATE"),
            "hit_count": 0,
            "miss_count": 0,
            "wrong_control_count": 0,
            "notes": str(row.get("notes") or ""),
            "roster_index": row.get("roster_index"),
            "display_name_hint": row.get("display_name_hint"),
            "attested": False,
        }
    return out


def ensure_seeded_ledger(ledger: dict | None = None, *, cfg: Optional[dict] = None) -> dict:
    book = dict(ledger) if isinstance(ledger, Mapping) else empty_ledger()
    targets = book.get("targets")
    if not isinstance(targets, dict):
        targets = {}
    for tid, row in seed_targets_from_contract(cfg).items():
        if tid not in targets:
            targets[tid] = row
    book["targets"] = targets
    return book


def classify_click(
    *,
    intended_xy: Sequence[int],
    observed_xy: Sequence[int],
    cfg: Optional[dict] = None,
    observed_control_id: str | None = None,
    intended_target_id: str | None = None,
) -> dict:
    """Score one click. WRONG_CONTROL when a different fixed control opened."""
    cfg = cfg or load_contract()
    if len(intended_xy) != 2 or len(observed_xy) != 2:
        raise FixedUiClickMapError("XY_MUST_BE_TWO_INTS")
    if any(type(v) is not int for v in list(intended_xy) + list(observed_xy)):
        raise FixedUiClickMapError("XY_MUST_BE_TWO_INTS")
    thr = cfg.get("thresholds_px") or {}
    hit_r = int(thr.get("hit_radius") or 12)
    near_r = int(thr.get("near_miss_radius") or 36)
    dx = int(observed_xy[0]) - int(intended_xy[0])
    dy = int(observed_xy[1]) - int(intended_xy[1])
    err = math.hypot(dx, dy)
    if (
        observed_control_id
        and intended_target_id
        and str(observed_control_id) != str(intended_target_id)
    ):
        classification = "WRONG_CONTROL"
    elif err <= hit_r:
        classification = "HIT"
    elif err <= near_r:
        classification = "NEAR_MISS"
    else:
        classification = "MISS"
    return {
        "classification": classification,
        "error_px": round(err, 3),
        "dx": dx,
        "dy": dy,
        "intended_xy": [int(intended_xy[0]), int(intended_xy[1])],
        "observed_xy": [int(observed_xy[0]), int(observed_xy[1])],
        "intended_target_id": intended_target_id,
        "observed_control_id": observed_control_id,
    }


def record_click_attempt(
    ledger: dict,
    *,
    target_id: str,
    client_xy: Sequence[int],
    classification: str,
    intended_xy: Sequence[int] | None = None,
    observed_control_id: str | None = None,
    note: str = "",
    moving_target: bool = False,
    cfg: Optional[dict] = None,
) -> dict:
    """Append one click attempt and update target stats (fixed UI only)."""
    cfg = cfg or load_contract()
    if moving_target:
        attempt = {
            "target_id": str(target_id or "UNKNOWN"),
            "client_xy": list(client_xy) if client_xy is not None else None,
            "classification": "OUT_OF_SCOPE_MOVING_TARGET",
            "note": note or "Moving targets have a separate system",
        }
        ledger.setdefault("attempts", []).append(attempt)
        return attempt
    tid = str(target_id or "").strip()
    if not tid:
        raise FixedUiClickMapError("TARGET_ID_REQUIRED")
    if (
        not isinstance(client_xy, (list, tuple))
        or len(client_xy) != 2
        or any(type(v) is not int for v in client_xy)
    ):
        raise FixedUiClickMapError("CLIENT_XY_MUST_BE_TWO_INTS")
    allowed = set(cfg.get("classifications") or [])
    label = str(classification)
    if label not in allowed:
        raise FixedUiClickMapError("UNKNOWN_CLICK_CLASSIFICATION")
    book = ensure_seeded_ledger(ledger, cfg=cfg)
    targets = book["targets"]
    row = dict(targets.get(tid) or {"target_id": tid, "client_xy": [int(client_xy[0]), int(client_xy[1])], "status": "CANDIDATE", "hit_count": 0, "miss_count": 0, "wrong_control_count": 0, "attested": False})
    if label == "HIT":
        row["hit_count"] = int(row.get("hit_count") or 0) + 1
        row["client_xy"] = [int(client_xy[0]), int(client_xy[1])]
        row["attested"] = True
        row["status"] = "ATTESTED_HIT"
    elif label == "WRONG_CONTROL":
        row["wrong_control_count"] = int(row.get("wrong_control_count") or 0) + 1
        # Do not rewrite intended target coords from a wrong-control click.
    else:
        row["miss_count"] = int(row.get("miss_count") or 0) + 1
    targets[tid] = row
    book["targets"] = targets
    attempt = {
        "target_id": tid,
        "client_xy": [int(client_xy[0]), int(client_xy[1])],
        "intended_xy": list(intended_xy) if intended_xy is not None else [int(client_xy[0]), int(client_xy[1])],
        "classification": label,
        "observed_control_id": observed_control_id,
        "note": str(note or ""),
    }
    book.setdefault("attempts", []).append(attempt)
    ledger.clear()
    ledger.update(book)
    return attempt


def resolve_target_xy(ledger: Mapping[str, object], target_id: str, *, cfg: Optional[dict] = None) -> dict:
    """Resolve the best known client_xy for a fixed target."""
    cfg = cfg or load_contract()
    book = ensure_seeded_ledger(dict(ledger), cfg=cfg)
    tid = str(target_id).strip()
    row = (book.get("targets") or {}).get(tid)
    if not isinstance(row, Mapping) or not row.get("client_xy"):
        raise FixedUiClickMapError("TARGET_XY_UNKNOWN:" + tid)
    return {
        "target_id": tid,
        "client_xy": [int(row["client_xy"][0]), int(row["client_xy"][1])],
        "status": str(row.get("status") or "CANDIDATE"),
        "attested": bool(row.get("attested")),
        "role": str(row.get("role") or ""),
        "proof_ceiling": cfg["proof_ceiling"],
    }


def plan_arm_to_console_handoff(*, cfg: Optional[dict] = None) -> dict:
    """Plan LMB/RMB arm then CHEAT_CONSOLE microsystem handoff."""
    cfg = cfg or load_contract()
    hand = cfg.get("handoff") or {}
    from betterinstincts.diy_skill_force import plan_live_hotkey_arm

    arm = plan_live_hotkey_arm()
    return {
        "schema": "betterinstincts.arm-to-console-handoff/v1",
        "step": "ARM_TO_CHEAT_CONSOLE",
        "order": list(hand.get("order") or []),
        "arm": arm,
        "console": {
            "hotkey_id": str(hand.get("console_hotkey_id") or "CHEAT_CONSOLE"),
            "chord": list(hand.get("console_chord") or ["CTRL", "SHIFT", "C"]),
            "require_white_strip_observed": bool(
                hand.get("console_strip_required_before_type", True)
            ),
            "owner": "scripts.diy_skill_force._toggle_cheat_console",
            "refocus_strip_target": "live.cheat_console_strip",
        },
        "forbidden": [
            "TYPE_WITHOUT_CONSOLE_STRIP",
            "TREAT_CANCEL_RMB_AS_PORTRAIT_FOLLOW",
            "BARE_HOTKEY_WITHOUT_ARM",
        ],
        "note": str(hand.get("note") or ""),
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
    }


def plan_skills_burger_expand(*, cfg: Optional[dict] = None) -> dict:
    """Plan L → locate MIN burger → stepped LMB drag to MAX for full Skills list.

    Endpoints are PrintWindow-measured on 1920×1080. This plan never SendInputs;
    live drag requires ACTIVE host session + screen admit outside this module.
    """
    cfg = cfg or load_contract()
    block = cfg.get("skills_burger_bar_1920x1080") or {}
    if not isinstance(block, Mapping):
        raise FixedUiClickMapError("SKILLS_BURGER_BAR_BLOCK_REQUIRED")
    endpoints = block.get("endpoints") if isinstance(block.get("endpoints"), Mapping) else {}
    amin = endpoints.get("min") if isinstance(endpoints.get("min"), Mapping) else {}
    amax = endpoints.get("max") if isinstance(endpoints.get("max"), Mapping) else {}
    expand = block.get("expand_drag") if isinstance(block.get("expand_drag"), Mapping) else {}
    from_xy = list(expand.get("from_xy") or amin.get("client_xy") or [])
    to_xy = list(expand.get("to_xy") or amax.get("client_xy") or [])
    if len(from_xy) != 2 or len(to_xy) != 2:
        raise FixedUiClickMapError("SKILLS_BURGER_ENDPOINTS_REQUIRED")
    if from_xy == to_xy:
        raise FixedUiClickMapError("SKILLS_BURGER_MIN_MAX_MUST_DIFFER")
    return {
        "schema": "betterinstincts.skills-burger-expand/v1",
        "step": "EXPAND_SKILLS_BURGER",
        "order": [
            "ARM_LIVE_HOTKEYS",
            "OPEN_SKILLS_HOTKEY_L",
            "LOCATE_BURGER_MIN",
            "LEFT_DRAG_MIN_TO_MAX",
            "CONFIRM_GREEN_HEADER_NEAR_MAX_Y",
        ],
        "open_hotkey": str(block.get("open_hotkey") or "L"),
        "min": {
            "target_id": str(amin.get("target_id") or "live.skills_burger_grip_min"),
            "client_xy": [int(from_xy[0]), int(from_xy[1])],
        },
        "max": {
            "target_id": str(amax.get("target_id") or "live.skills_burger_grip_max"),
            "client_xy": [int(to_xy[0]), int(to_xy[1])],
        },
        "drag": {
            "from_xy": [int(from_xy[0]), int(from_xy[1])],
            "to_xy": [int(to_xy[0]), int(to_xy[1])],
            "input": str(expand.get("input") or "LEFT_BUTTON_STEPPED_DRAG"),
            "owner": str(expand.get("owner") or "scripts.win32_input.left_drag"),
        },
        "forbidden": [
            "SCROLLBAR_ALONE_AS_FULL_PANEL_READ",
            "TREAT_BURGER_DRAG_AS_SKILLS_PANEL_PASS",
            "SENDINPUT_FROM_MAP_MODULE",
        ],
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
        "note": (
            "Grab the two-line burger above SKILL MASTERY PERKS at MIN height and "
            "drag upward to MAX before panel-record. Remeasure if green header Y drifts."
        ),
    }
