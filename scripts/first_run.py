#!/usr/bin/env python3
"""First-run Sims 4 handoff; user chooses an installed executable and game mode."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from betterinstincts.first_run import (
    FirstRunError, GOALS, discover_game_installs, launch_game,
    plan_journey, select_game,
)


def gui() -> int:
    if sys.platform != "win32":
        raise FirstRunError("LOCAL_WINDOWS_GAME_HOST_REQUIRED")
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except ImportError as exc:
        raise FirstRunError("TKINTER_UNAVAILABLE_USE_CLI") from exc
    root = tk.Tk()
    root.title("BetterInstincts · Play The Sims 4")
    root.geometry("690x410")
    root.resizable(False, False)
    frame = ttk.Frame(root, padding=22)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="BetterInstincts", font=("Segoe UI", 20, "bold")).pack(anchor="w")
    ttk.Label(
        frame, text="Your game. Your saves. Your decisions. The toolkit is installed separately from The Sims 4.",
        wraplength=630, justify="left",
    ).pack(anchor="w", pady=(5, 14))
    candidates = discover_game_installs()
    labels = [str(path) for path in candidates]
    selected = tk.StringVar(value=labels[0] if len(labels) == 1 else "")
    ttk.Label(frame, text="Game installation").pack(anchor="w")
    picker = ttk.Combobox(frame, textvariable=selected, values=labels, width=90, state="readonly")
    picker.pack(anchor="w", pady=(4, 4))
    ttk.Label(
        frame, text="Nothing listed? Select the TS4_x64.exe in your installed Game/Bin folder.",
        wraplength=630,
    ).pack(anchor="w")
    def browse() -> None:
        path = filedialog.askopenfilename(
            parent=root, title="Select your installed Sims 4 executable",
            filetypes=[("Sims 4 executable", "TS4_x64.exe TS4.exe"), ("Executable", "*.exe")],
        )
        if path:
            try:
                target = select_game([], path)
            except FirstRunError as exc:
                messagebox.showerror("BetterInstincts", str(exc), parent=root)
                return
            if str(target) not in labels:
                labels.append(str(target))
                picker["values"] = labels
            selected.set(str(target))
    ttk.Button(frame, text="Choose game executable…", command=browse).pack(anchor="w", pady=(4, 13))
    goal = tk.StringVar(value="balanced")
    ttk.Label(frame, text="Optional new Sim playstyle").pack(anchor="w")
    ttk.Combobox(
        frame, textvariable=goal, values=list(GOALS), state="readonly", width=20,
    ).pack(anchor="w", pady=(4, 14))
    status = tk.StringVar(value="The game starts only when you choose a mode below.")
    ttk.Label(frame, textvariable=status, wraplength=625).pack(anchor="w", pady=(0, 12))

    def begin(mode: str) -> None:
        try:
            exe = select_game(candidates, selected.get() or None)
            advice = plan_journey(mode, goal.get())
            receipt = launch_game(exe, user_clicked_launch=True)
            status.set("Game launch requested. Finish the next step in The Sims 4.")
            messagebox.showinfo(
                "BetterInstincts · Next step",
                advice["next_step"] + (
                    "\n\nSuggested aspiration: " + str(advice["cas_advice"]["aspiration"])
                    + "\nSuggested traits: " + ", ".join(advice["cas_advice"]["traits"])
                    + "\n\nSuggestions only; your character is never edited automatically."
                    if mode == "new" else
                    "\n\nYour existing save remains your choice. No automatic Resume click."
                ) + "\n\n" + receipt["state"], parent=root,
            )
        except (FirstRunError, OSError) as exc:
            status.set("Nothing launched: " + str(exc))
            messagebox.showerror("BetterInstincts", str(exc), parent=root)
    actions = ttk.Frame(frame)
    actions.pack(anchor="w")
    ttk.Button(actions, text="Continue existing game", command=lambda: begin("existing")).pack(side="left", padx=(0, 12))
    ttk.Button(actions, text="Start a new game", command=lambda: begin("new")).pack(side="left")
    root.mainloop()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("gui")
    sub.add_parser("discover")
    p = sub.add_parser("plan")
    p.add_argument("--mode", choices=("existing", "new"), required=True)
    p.add_argument("--goal", choices=tuple(GOALS), default="balanced")
    p = sub.add_parser("launch")
    p.add_argument("--game-exe", type=Path, required=True)
    p.add_argument("--mode", choices=("existing", "new"), required=True)
    p.add_argument("--goal", choices=tuple(GOALS), default="balanced")
    p.add_argument("--confirm-launch", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command in (None, "gui"):
            return gui()
        if args.command == "discover":
            output = {"state": "READ_ONLY", "candidates": [str(x) for x in discover_game_installs()]}
        elif args.command == "plan":
            output = plan_journey(args.mode, args.goal)
        else:
            output = {**launch_game(args.game_exe, user_clicked_launch=args.confirm_launch),
                      "handoff": plan_journey(args.mode, args.goal)}
        print(json.dumps(output, sort_keys=True))
        return 0
    except (FirstRunError, OSError, ValueError) as exc:
        print(json.dumps({"state": "BLOCKED_PRESERVE", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
