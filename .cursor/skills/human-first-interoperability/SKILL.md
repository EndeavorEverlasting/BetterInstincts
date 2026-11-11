---
name: human-first-interoperability
description: Enforce BetterInstincts P00/P01 human sovereignty, classify every effect, and validate agent adapter coverage without touching operator Windows settings or saves.
---

# Human-first interoperability

Trigger before adding or modifying a game/mouse/keyboard/Win32/Playwright/agent
input path, background callback, focus borrow, or computer-use adapter.

1. Read root `AGENTS.md`, `docs/AGENT_OPERATING_RULES.md`,
   `docs/DOCTRINE.md`, `docs/ONTOLOGY.md`, and
   `docs/HUMAN_FIRST_HARNESS.md` first.
2. Read the **existing** `contracts/effect-authority.v1.json`,
   `contracts/human-first-harness.v1.json` and
   `contracts/workflow-interoperability.v1.json`.
3. Human input in any app wins. Classify the effect; unknown and OS settings
   DENY. Read-only background callbacks do not focus/type/click/mutate.
4. For UI/game actions, use a reviewed cooperative adapter, two fresh idle
   probes before and after focus borrow, live scene/save/target/queue
   attestation and per-effect recheck. Never replay unknown partial effects.
5. Add or revise one entry in the machine registry for each new physical
   or desktop action path; a raw Win32 helper alone does not confer authority.
6. Run `python -m unittest discover -s tests -v` plus
   `python -m scripts.check_human_sovereignty --json` in CI/authorized
   terminal, `scripts.check_ontology`, and peripheral boundary tests.
7. Preserve the canonical `bootstrap.py` / workstation path registry.
   Report source/CI, merge, installed app and live operator-input proof
   separately. Do not claim local hook activation from a GitHub branch.

Forbidden: disable Bluetooth, drivers, Print Screen, Escape/U mappings,
accessibility, Windows hotkeys, protected saves, or Cursor hook protections.
Do not install a background keylogger, cron job or global interception hook.
