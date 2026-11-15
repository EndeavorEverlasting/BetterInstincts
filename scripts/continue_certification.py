"""Hand an in-flight Sims certification to the installed Windows Codex agent."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import shutil
import subprocess
import sys

from betterinstincts.first_run import FirstRunError
from scripts.launch_save_route import LOCAL_CONTEXT, route_local_context
from scripts.smart_start import read_sims_processes

ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "docs" / "LIVE_CERTIFICATION_HANDOFF.md"


class HandoffError(RuntimeError):
    pass


def build_handoff(root: Path = ROOT) -> str:
    try:
        processes = read_sims_processes()
    except FirstRunError as error:
        process = {"state": "PROCESS_INVENTORY_UNAVAILABLE", "reason": str(error)}
    else:
        process = {"state": "LOCAL_PROCESS_NAMES_OBSERVED", "pids": sorted(processes)}

    memo = root / LOCAL_CONTEXT.relative_to(ROOT)
    route = route_local_context(
        path=memo, game_running_observed=len(process.get("pids", [])) == 1,
    )
    # This is an observation of process names and a memo, not a fresh dialog,
    # exact build, checked save, permission to focus, or current native result.
    summary = {"process_sample": process, "memo_route": route["state"]}
    return ("The operator launched the BetterInstincts live-certification handoff. "
            "Execute the scoped task below in this evidence checkout. "
            "Local startup observation (recheck before any live action): "
            + json.dumps(summary, sort_keys=True) + "\n\n"
            + HANDOFF.read_text(encoding="utf-8"))


def installed_codex(root: Path) -> Path:
    candidate = shutil.which("codex.exe") or shutil.which("codex.cmd")
    if candidate is None:
        raise HandoffError("Codex CLI was not found on PATH. Use the installed local "
                           "Codex CLI and run this launcher again.")
    executable = Path(candidate)
    if not executable.is_absolute() or executable.resolve().is_relative_to(root.resolve()):
        raise HandoffError("Resolve Codex CLI from its installed location outside this checkout.")
    return executable


@contextmanager
def checkout_dispatch(root: Path):
    """Keep two launcher invocations from dispatching in the same checkout."""
    import msvcrt

    path = root / "dist" / "game-host" / "certification-dispatch.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:
        # Windows permits a byte-range lock beyond EOF. The OS releases it
        # when this handle closes, including when the dispatcher crashes.
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise HandoffError("This checkout already has a certification dispatcher.") from error
        yield


def evidence_checkout(path: Path) -> Path:
    root = path.resolve(strict=True)
    if not ((root / ".git").exists()
            and (root / "docs" / "AGENT_OPERATING_RULES.md").is_file()
            and (root / "plans" / "active" / "BI-002.execution.v1.json").is_file()):
        raise HandoffError("Select the existing BetterInstincts Windows evidence checkout.")
    return root


def dispatch(root: Path = ROOT) -> int:
    if sys.platform != "win32":
        raise HandoffError("Run the certification launcher on the Windows Sims host.")
    root = evidence_checkout(root)
    executable = installed_codex(root)
    with checkout_dispatch(root):
        # Only fixed arguments reach the Windows executable/shim. Task text
        # goes through stdin and the existing Codex settings/permissions apply.
        result = subprocess.run(
            [str(executable), "exec", "-"],
            cwd=root, input=build_handoff(root).encode("utf-8"), check=False,
        )
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-handoff", action="store_true",
                        help="Show the task and read-only startup observation without dispatching")
    parser.add_argument("--checkout", type=Path, default=ROOT,
                        help="Existing BetterInstincts worktree containing the local receipts")
    args = parser.parse_args()
    try:
        if args.print_handoff:
            print(build_handoff(args.checkout.resolve()))
            return 0
        result = dispatch(args.checkout)
        if result:
            print(f"Local Codex exited with code {result}. Check the output above.",
                  file=sys.stderr)
        return result
    except (HandoffError, OSError) as error:
        print(f"Certification launcher: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
