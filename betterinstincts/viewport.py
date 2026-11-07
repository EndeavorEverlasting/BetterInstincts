"""Classify PrintWindow Sims client bitmaps for black / stuck viewport states.

LOCAL_OBSERVED 2026-11-07 on bi002-quiz-boot (1.121.361.1020, 1920x1080): after
Manage Worlds reload + empty-lot CAS abort + night empty lot, PrintWindow returned
a near-uniform black client while TS4_x64 stayed restored/non-iconic.

Canonical RCA + avoidance + recovery ladder:
  contracts/viewport-black.v1.json
Scene id: live_viewport_black

This module never clicks the game. Recovery/restart belongs to
scripts/viewport_recover.py (deterministic host logic).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Sequence, Tuple

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "viewport-black.v1.json"
SCENE_ID = "live_viewport_black"
MAX_IMAGE_BYTES = 12_000_000
MAX_PIXELS = 16_000_000
MAX_CONTRACT_BYTES = 64_000

# Luma thresholds tuned for 8-bit RGB PrintWindow samples of a black client.
FULL_BLACK_MEAN = 8.0
FULL_BLACK_STD = 12.0
VIEWPORT_BLACK_MEAN = 18.0
HUD_ALIVE_MEAN = 28.0
HUD_ALIVE_STD = 10.0
# Sparse bright edges (lot platform wireframe in void): operator-observed 2026-11-07.
WIREFRAME_BRIGHT_LUMA = 40.0
WIREFRAME_BRIGHT_FRAC_MIN = 0.00005
WIREFRAME_BRIGHT_FRAC_MAX = 0.03
WIREFRAME_MAX_LUMA_MIN = 48.0
# Build/Buy purchase catalog strip: dark world + bright, high-variance bottom tray.
# LOCAL_OBSERVED recovery after ENTER_BUILD_BUY_UNSTICK (Build hammer @ 1505,22).
BUY_CATALOG_HUD_MEAN = 36.0
BUY_CATALOG_HUD_STD = 22.0


class ViewportError(ValueError):
    """Invalid capture or contract for viewport analysis; never gameplay success."""


@dataclass(frozen=True)
class RegionStats:
    name: str
    mean_luma: float
    std_luma: float
    max_luma: float
    pixel_count: int


@dataclass(frozen=True)
class ViewportReport:
    state: str
    classification: str
    scene_id: Optional[str]
    width: int
    height: int
    regions: Tuple[RegionStats, ...]
    next_gate: str
    recovery_ladder: Tuple[str, ...]
    avoidance: Tuple[str, ...]
    rca_summary: str
    proof_ceiling: str


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_CONTRACT_BYTES:
        raise ViewportError("VIEWPORT_CONTRACT_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.viewport-black/v1":
        raise ViewportError("BAD_VIEWPORT_SCHEMA")
    if cfg.get("scene_id") != SCENE_ID:
        raise ViewportError("VIEWPORT_SCENE_MISMATCH")
    if not isinstance(cfg.get("recovery_ladder"), list) or not cfg["recovery_ladder"]:
        raise ViewportError("RECOVERY_LADDER_REQUIRED")
    if not isinstance(cfg.get("avoidance"), list) or not cfg["avoidance"]:
        raise ViewportError("AVOIDANCE_REQUIRED")
    return cfg


def _ladder_steps(cfg: dict | None = None) -> Tuple[str, ...]:
    cfg = cfg or load_contract()
    return tuple(str(row["step"]) for row in cfg["recovery_ladder"] if isinstance(row, dict) and "step" in row)


def _avoidance_ids(cfg: dict | None = None) -> Tuple[str, ...]:
    cfg = cfg or load_contract()
    return tuple(str(row["id"]) for row in cfg["avoidance"] if isinstance(row, dict) and "id" in row)


def _rca_summary(cfg: dict | None = None) -> str:
    cfg = cfg or load_contract()
    return str(cfg.get("root_cause_analysis", {}).get("summary", ""))


def _luma_stats(pixels: Sequence[Tuple[int, int, int]], name: str) -> RegionStats:
    if not pixels:
        raise ViewportError("EMPTY_REGION:" + name)
    lumas = [0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in pixels]
    mean = sum(lumas) / len(lumas)
    var = sum((x - mean) ** 2 for x in lumas) / len(lumas)
    return RegionStats(
        name=name,
        mean_luma=round(mean, 3),
        std_luma=round(var ** 0.5, 3),
        max_luma=round(max(lumas), 3),
        pixel_count=len(lumas),
    )


def _bright_fraction(pixels: Sequence[Tuple[int, int, int]], threshold: float = WIREFRAME_BRIGHT_LUMA) -> float:
    if not pixels:
        return 0.0
    bright = 0
    for r, g, b in pixels:
        if 0.2126 * r + 0.7152 * g + 0.0722 * b >= threshold:
            bright += 1
    return bright / len(pixels)


def _sample_grid(img: Image.Image, box: Tuple[int, int, int, int], step: int = 8) -> list[Tuple[int, int, int]]:
    left, top, right, bottom = box
    left = max(0, left)
    top = max(0, top)
    right = min(img.width, right)
    bottom = min(img.height, bottom)
    if right <= left or bottom <= top:
        raise ViewportError("BAD_REGION_BOX")
    rgb = img.convert("RGB")
    out = []
    for y in range(top, bottom, step):
        for x in range(left, right, step):
            out.append(rgb.getpixel((x, y)))
    return out


def region_boxes(width: int, height: int) -> Mapping[str, Tuple[int, int, int, int]]:
    """Heuristic HUD vs world boxes for borderless 16:9 Live Mode clients."""
    if width < 320 or height < 240:
        raise ViewportError("CLIENT_TOO_SMALL")
    return {
        "world": (int(width * 0.15), int(height * 0.12), int(width * 0.85), int(height * 0.72)),
        "hud_bottom": (0, int(height * 0.88), width, height),
        "hud_top": (int(width * 0.55), 0, width, int(height * 0.08)),
        "full": (0, 0, width, height),
    }


def predict_risk(context: Mapping[str, object]) -> dict:
    """Offline predictor: raise risk score when known precursors are present.

    Context flags are operator/host attested booleans — not vision claims.
    """
    cfg = load_contract()
    flags = {
        "empty_lot": bool(context.get("empty_lot")),
        "night": bool(context.get("night")),
        "no_lights_placed": bool(context.get("no_lights_placed")),
        "after_cas_abort": bool(context.get("after_cas_abort")),
        "after_manage_worlds": bool(context.get("after_manage_worlds")),
        "used_desktop_capture_overlay": bool(context.get("used_desktop_capture_overlay")),
        "needs_critical": bool(context.get("needs_critical")),
        "sim_off_lot": bool(context.get("sim_off_lot")),
    }
    score = 0
    reasons = []
    if flags["after_cas_abort"]:
        score += 4
        reasons.append("H1_cas_abort")
    if flags["after_manage_worlds"]:
        score += 2
        reasons.append("C2_manage_worlds")
    if flags["empty_lot"] and flags["night"] and flags["no_lights_placed"]:
        score += 3
        reasons.append("H2_night_empty_unlit")
    if flags["used_desktop_capture_overlay"]:
        score += 2
        reasons.append("H3_desktop_capture_overlay")
    if flags["needs_critical"] and flags["sim_off_lot"]:
        score += 1
        reasons.append("A1_prefer_send_alone")
    level = "LOW"
    if score >= 6:
        level = "HIGH"
    elif score >= 3:
        level = "ELEVATED"
    return {
        "state": "VIEWPORT_RISK_SCORED",
        "risk_level": level,
        "score": score,
        "flags": flags,
        "reasons": reasons,
        "required_before_clicks": [
            "PRINTWINDOW_CAPTURE",
            "VIEWPORT_ANALYZE",
        ] if level in {"ELEVATED", "HIGH"} else ["PRINTWINDOW_CAPTURE_OPTIONAL"],
        "avoidance": list(_avoidance_ids(cfg)),
        "proof_ceiling": "HOST_CONTEXT_RISK_NOT_ENGINE_PROOF",
    }


def analyze_image(path: Path, *, step: int = 8, contract: dict | None = None) -> ViewportReport:
    cfg = contract or load_contract()
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ViewportError("CAPTURE_MISSING")
    if path.stat().st_size > MAX_IMAGE_BYTES:
        raise ViewportError("CAPTURE_TOO_LARGE")
    img = Image.open(path)
    img.load()
    width, height = img.size
    if width * height > MAX_PIXELS:
        raise ViewportError("CAPTURE_PIXEL_BUDGET")

    boxes = region_boxes(width, height)
    samples = {name: _sample_grid(img, boxes[name], step=step) for name in ("world", "hud_bottom", "hud_top", "full")}
    regions = tuple(_luma_stats(samples[name], name) for name in ("world", "hud_bottom", "hud_top", "full"))
    by_name = {r.name: r for r in regions}
    world, hud_b, hud_t, full = by_name["world"], by_name["hud_bottom"], by_name["hud_top"], by_name["full"]
    ladder = _ladder_steps(cfg)
    avoidance = _avoidance_ids(cfg)
    summary = _rca_summary(cfg)
    gates = cfg.get("host_next_gates", {})
    world_bright_frac = _bright_fraction(samples["world"])

    full_black = full.mean_luma <= FULL_BLACK_MEAN and full.std_luma <= FULL_BLACK_STD and full.max_luma < WIREFRAME_MAX_LUMA_MIN
    world_black = world.mean_luma <= VIEWPORT_BLACK_MEAN and world.std_luma <= FULL_BLACK_STD * 1.5
    hud_alive = (
        max(hud_b.mean_luma, hud_t.mean_luma) >= HUD_ALIVE_MEAN
        or max(hud_b.std_luma, hud_t.std_luma) >= HUD_ALIVE_STD
    )
    # Operator sneak capture: near-black void + sparse bright lot-platform edges that track mouse.
    wireframe_void = (
        world.mean_luma <= VIEWPORT_BLACK_MEAN
        and world.max_luma >= WIREFRAME_MAX_LUMA_MIN
        and WIREFRAME_BRIGHT_FRAC_MIN <= world_bright_frac <= WIREFRAME_BRIGHT_FRAC_MAX
        and not hud_alive
    )

    if wireframe_void:
        classification = "VOID_LOT_PLATFORM_WIREFRAME"
        return ViewportReport(
            state="VIEWPORT_ANOMALY",
            classification=classification,
            scene_id=SCENE_ID,
            width=width,
            height=height,
            regions=regions,
            next_gate=str(gates.get(classification, "CAMERA_THEN_BUILD_LIVE_OR_RESTART")),
            recovery_ladder=ladder,
            avoidance=avoidance,
            rca_summary=summary + f" | wireframe_bright_frac={world_bright_frac:.5f}",
            proof_ceiling="PRINTWINDOW_LUMA_CLASSIFIER_NOT_SCENE_CERTIFICATION",
        )
    if full_black:
        classification = "FULL_CLIENT_BLACK"
        next_gate = str(gates.get(classification, "ENTER_BUILD_BUY_UNSTICK"))
        return ViewportReport(
            state="VIEWPORT_ANOMALY",
            classification=classification,
            scene_id=SCENE_ID,
            width=width,
            height=height,
            regions=regions,
            next_gate=next_gate,
            recovery_ladder=ladder,
            avoidance=avoidance,
            rca_summary=(
                summary
                + " | PrintWindow may omit DX wireframe; operator secondary-monitor sneak can still show mouse-tracking lot platform."
                + " | Prefer ENTER_BUILD_BUY_UNSTICK (Build hammer) before Live toggle or restart."
            ),
            proof_ceiling="PRINTWINDOW_LUMA_CLASSIFIER_NOT_SCENE_CERTIFICATION",
        )
    buy_catalog = (
        world_black
        and hud_b.mean_luma >= BUY_CATALOG_HUD_MEAN
        and hud_b.std_luma >= BUY_CATALOG_HUD_STD
    )
    if buy_catalog:
        classification = "BUILD_BUY_CATALOG_RECOVERY"
        return ViewportReport(
            state="VIEWPORT_MODE_BUILD_BUY",
            classification=classification,
            scene_id=SCENE_ID,
            width=width,
            height=height,
            regions=regions,
            next_gate=str(gates.get(classification, "EXIT_BUY_TO_LIVE_OR_OPERATOR_SAVE_EXIT")),
            recovery_ladder=ladder,
            avoidance=avoidance,
            rca_summary=(
                summary
                + " | Build/Buy catalog HUD present with dark world — black glitch unstuck into purchase mode;"
                + " not Live Mode; withhold needs clicks (A7/H5)."
            ),
            proof_ceiling="PRINTWINDOW_LUMA_CLASSIFIER_NOT_SCENE_CERTIFICATION",
        )
    if world_black and hud_alive:
        classification = "VIEWPORT_BLACK_HUD_ALIVE"
        return ViewportReport(
            state="VIEWPORT_ANOMALY",
            classification=classification,
            scene_id=SCENE_ID,
            width=width,
            height=height,
            regions=regions,
            next_gate=str(gates.get(classification, "CAMERA_RECOVER_THEN_RECAPTURE")),
            recovery_ladder=ladder,
            avoidance=avoidance,
            rca_summary=summary,
            proof_ceiling="PRINTWINDOW_LUMA_CLASSIFIER_NOT_SCENE_CERTIFICATION",
        )
    if world_black and not hud_alive:
        classification = "VIEWPORT_NEAR_BLACK"
        return ViewportReport(
            state="VIEWPORT_ANOMALY",
            classification=classification,
            scene_id=SCENE_ID,
            width=width,
            height=height,
            regions=regions,
            next_gate=str(gates.get(classification, "RECAPTURE_THEN_CAMERA_RECOVER")),
            recovery_ladder=ladder,
            avoidance=avoidance,
            rca_summary=summary,
            proof_ceiling="PRINTWINDOW_LUMA_CLASSIFIER_NOT_SCENE_CERTIFICATION",
        )
    return ViewportReport(
        state="VIEWPORT_OK",
        classification="CONTENT_PRESENT",
        scene_id=None,
        width=width,
        height=height,
        regions=regions,
        next_gate=str(gates.get("VIEWPORT_OK", "CONTINUE_HOST_LANE")),
        recovery_ladder=(),
        avoidance=avoidance,
        rca_summary=summary,
        proof_ceiling="PRINTWINDOW_LUMA_CLASSIFIER_NOT_SCENE_CERTIFICATION",
    )


def report_to_dict(report: ViewportReport) -> dict:
    return {
        "state": report.state,
        "classification": report.classification,
        "scene_id": report.scene_id,
        "width": report.width,
        "height": report.height,
        "regions": [
            {
                "name": r.name,
                "mean_luma": r.mean_luma,
                "std_luma": r.std_luma,
                "max_luma": r.max_luma,
                "pixel_count": r.pixel_count,
            }
            for r in report.regions
        ],
        "next_gate": report.next_gate,
        "recovery_ladder": list(report.recovery_ladder),
        "avoidance": list(report.avoidance),
        "rca_summary": report.rca_summary,
        "proof_ceiling": report.proof_ceiling,
    }
