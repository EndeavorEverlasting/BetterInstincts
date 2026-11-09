#!/usr/bin/env python3
"""Inspect or edit BetterInstincts installation-local preferences on demand.

No background process, telemetry, profile auto-migration or game input.
"""
from __future__ import annotations

import argparse
import json

from betterinstincts.installation_profiles import (
    DEFAULTS, InstallationProfileError, choose_profile, create_profile,
    reset_toggle, set_toggle, view,
)


def gui() -> int:
    """A deliberate desktop action; opening the panel reads but never writes."""
    try:
        import tkinter as tk
        from tkinter import messagebox, simpledialog, ttk
        root = tk.Tk()
    except (ImportError, RuntimeError, OSError) as exc:
        raise InstallationProfileError("SETTINGS_GUI_UNAVAILABLE") from exc
    except Exception as exc:
        # Tk.TclError on headless Linux is not defined if Tk cannot import.
        raise InstallationProfileError("SETTINGS_GUI_UNAVAILABLE") from exc

    root.title("BetterInstincts · Local Profiles")
    root.geometry("630x560")
    root.resizable(True, True)
    frame = ttk.Frame(root, padding=16)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Local installation profiles", font=("Arial", 16, "bold")).pack(anchor="w")
    ttk.Label(frame, text="Preferences stay on this computer. No game or screen control is granted.",
              wraplength=570).pack(anchor="w", pady=(4, 12))
    controls = ttk.Frame(frame)
    controls.pack(fill="x")
    profile_var = tk.StringVar()
    profile_choice = ttk.Combobox(controls, textvariable=profile_var, state="readonly", width=28)
    profile_choice.pack(side="left", padx=(0, 8))
    settings_frame = ttk.Frame(frame)
    settings_frame.pack(fill="both", expand=True, pady=(12, 0))
    state = ttk.Label(frame, text="Read-only until you change a preference.")
    state.pack(anchor="w")

    def error(exc: Exception) -> None:
        state.configure(text="No changes saved: " + str(exc))
        messagebox.showerror("BetterInstincts", str(exc), parent=root)

    def refresh() -> None:
        data = view()
        profile_choice["values"] = data["profiles"]
        profile_var.set(data["active_profile"])
        for widget in settings_frame.winfo_children():
            widget.destroy()
        for key, enabled in data["settings"].items():
            item = tk.BooleanVar(value=enabled)
            def set_value(name: str = key, var: object = item) -> None:
                try:
                    set_toggle(name, var.get())
                    state.configure(text="Saved locally: " + name)
                except (InstallationProfileError, OSError) as exc:
                    error(exc)
                    refresh()
            ttk.Checkbutton(settings_frame, text=key, variable=item,
                            command=set_value).pack(anchor="w", pady=4)

    def choose(_event: object = None) -> None:
        try:
            choose_profile(profile_var.get())
            state.configure(text="Active profile changed.")
            refresh()
        except (InstallationProfileError, OSError) as exc:
            error(exc)
            refresh()

    def add_profile() -> None:
        proposed = simpledialog.askstring("New profile", "Name (lowercase letters, numbers, _ or -):",
                                          parent=root)
        if proposed is None:
            return
        try:
            create_profile(proposed)
            choose_profile(proposed)
            state.configure(text="Profile created locally.")
            refresh()
        except (InstallationProfileError, OSError) as exc:
            error(exc)

    profile_choice.bind("<<ComboboxSelected>>", choose)
    ttk.Button(controls, text="New profile", command=add_profile).pack(side="left")
    try:
        refresh()
    except (InstallationProfileError, OSError) as exc:
        root.destroy()
        raise InstallationProfileError("SETTINGS_LOAD_BLOCKED:" + str(exc)) from exc
    root.mainloop()
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    show = sub.add_parser("show", help="Read effective toggles (no file created)")
    show.add_argument("--profile", default=None)
    sub.add_parser("profiles", help="List existing local profile IDs")
    create = sub.add_parser("create", help="Create an isolated profile")
    create.add_argument("profile_id")
    choose = sub.add_parser("choose", help="Select current profile")
    choose.add_argument("profile_id")
    set_p = sub.add_parser("set", help="Set a boolean toggle")
    set_p.add_argument("key", choices=sorted(DEFAULTS))
    set_p.add_argument("value", choices=["true", "false"])
    set_p.add_argument("--profile", default=None)
    reset = sub.add_parser("reset", help="Restore a toggle to its catalog default")
    reset.add_argument("key", choices=sorted(DEFAULTS))
    reset.add_argument("--profile", default=None)
    sub.add_parser("gui", help="Open the local Tk settings panel (explicit action only)")
    args = p.parse_args(argv)
    try:
        if args.command == "gui":
            return gui()
        if args.command == "show":
            result = view(profile_id=args.profile)
        elif args.command == "profiles":
            result = view()
            result = {"state": "PROFILES_LISTED", "profiles": result["profiles"],
                      "active_profile": result["active_profile"]}
        elif args.command == "create":
            result = create_profile(args.profile_id)
        elif args.command == "choose":
            result = choose_profile(args.profile_id)
        elif args.command == "set":
            result = set_toggle(args.key, args.value == "true", profile_id=args.profile)
        else:
            result = reset_toggle(args.key, profile_id=args.profile)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (InstallationProfileError, OSError) as exc:
        print(json.dumps({"state": "BLOCKED_PRESERVE", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
