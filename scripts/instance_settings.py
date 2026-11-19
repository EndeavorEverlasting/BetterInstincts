#!/usr/bin/env python3
"""Inspect or edit BetterInstincts installation-local preferences on demand.

No background process, telemetry, profile auto-migration or game input.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

from betterinstincts.installation_profiles import (
    DEFAULTS, LAUNCH_OPTIONS, InstallationProfileError, choose_profile, create_profile,
    reset_launch_preferences, reset_toggle, set_launch_preferences, set_preferred_household,
    set_toggle, view,
)


def choose_launch_household(choices: dict[str, str]) -> str | None:
    """Ask for one exact identity from the launcher's current verified catalog."""
    try:
        import tkinter as tk
        from tkinter import ttk
    except ImportError as exc:
        raise InstallationProfileError("HOUSEHOLD_PICKER_UNAVAILABLE") from exc
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise InstallationProfileError("HOUSEHOLD_PICKER_UNAVAILABLE") from exc
    root.title("BetterInstincts · Choose a household")
    frame = ttk.Frame(root, padding=22)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Which household do you want to play?",
              font=("Segoe UI", 15, "bold")).pack(anchor="w")
    ttk.Label(frame, text="BetterInstincts will remember this choice for your profile.").pack(
        anchor="w", pady=(5, 16))
    rows = sorted(choices.items(), key=lambda item: (item[1].casefold(), item[0]))
    from collections import Counter

    name_counts = Counter(name.casefold() for _, name in rows)
    select = ttk.Combobox(frame, state="readonly", width=44, values=[
        f"{name} ({identity})" if name_counts[name.casefold()] > 1 else name
        for identity, name in rows
    ])
    select.pack(fill="x")
    selected = None

    def accept() -> None:
        nonlocal selected
        index = select.current()
        if index >= 0:
            selected = rows[index][0]
            root.destroy()

    buttons = ttk.Frame(frame)
    buttons.pack(fill="x", pady=(18, 0))
    ttk.Button(buttons, text="Cancel", command=root.destroy).pack(side="right")
    ttk.Button(buttons, text="Play household", command=accept).pack(side="right", padx=8)
    root.bind("<Escape>", lambda _event: root.destroy())
    root.after(90_000, root.destroy)
    select.focus_set()
    root.mainloop()
    return selected


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
    root.geometry("660x620")
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
    notebook = ttk.Notebook(frame)
    notebook.pack(fill="both", expand=True, pady=(12, 0))
    launch_frame = ttk.Frame(notebook, padding=14)
    settings_frame = ttk.Frame(notebook, padding=14)
    notebook.add(launch_frame, text="Play")
    notebook.add(settings_frame, text="Features")
    state = ttk.Label(frame, text="Read-only until you change a preference.")
    state.pack(anchor="w")

    def error(exc: Exception) -> None:
        state.configure(text="No changes saved: " + str(exc))
        messagebox.showerror("BetterInstincts", str(exc), parent=root)

    def refresh() -> None:
        data = view()
        profile_choice["values"] = data["profiles"]
        profile_var.set(data["active_profile"])
        for widget in launch_frame.winfo_children():
            widget.destroy()
        editors = {}
        for key, option in LAUNCH_OPTIONS.items():
            value = data["launch"][key]
            if option["control"] == "toggle":
                variable = tk.BooleanVar(value=value)
                ttk.Checkbutton(launch_frame, text=option["label"], variable=variable).pack(anchor="w", pady=8)
                editors[key] = variable.get
                continue
            ttk.Label(launch_frame, text=option["label"]).pack(anchor="w", pady=(8, 3))
            index = option["choices"].index(value)
            if option["control"] == "slider":
                label = ttk.Label(launch_frame, text=option["labels"][index])
                label.pack(anchor="w")
                slider = tk.Scale(launch_frame, from_=0, to=len(option["choices"]) - 1,
                                  showvalue=False, orient="horizontal",
                                  command=lambda v, label=label, option=option:
                                      label.configure(text=option["labels"][int(float(v))]))
                slider.set(index)
                slider.pack(fill="x")
                editors[key] = lambda slider=slider, option=option: option["choices"][int(slider.get())]
            else:
                box = ttk.Combobox(launch_frame, state="readonly", values=option["labels"], width=45)
                box.current(index)
                box.pack(anchor="w")
                editors[key] = lambda box=box, option=option: option["choices"][box.current()]
        ttk.Label(launch_frame, text=("Household remembered for this profile." if data["preferred_household_id"]
                                     else "Choose your household from the game catalog during Play.")).pack(
            anchor="w", pady=(14, 8))

        def save(*, play=False) -> None:
            try:
                set_launch_preferences({key: read() for key, read in editors.items()},
                                       expected_revision=data["revision"])
                if play:
                    subprocess.Popen([sys.executable, "-m", "scripts.play",
                                      "--profile-launch", "--choose-household"], close_fds=True)
                    root.destroy()
                else:
                    refresh()
                    state.configure(text="Play settings saved.")
            except (InstallationProfileError, OSError) as exc:
                error(exc)
                refresh()

        actions = ttk.Frame(launch_frame)
        actions.pack(anchor="w")
        ttk.Button(actions, text="Save settings", command=save).pack(side="left")
        ttk.Button(actions, text="Save and choose household in Play",
                   command=lambda: save(play=True)).pack(side="left", padx=8)
        def reset_play() -> None:
            try:
                reset_launch_preferences(expected_revision=data["revision"])
                refresh()
                state.configure(text="Play defaults restored.")
            except (InstallationProfileError, OSError) as exc:
                error(exc)
                refresh()

        ttk.Button(actions, text="Restore defaults", command=reset_play).pack(side="left")
        for widget in settings_frame.winfo_children():
            widget.destroy()
        for key, enabled in data["settings"].items():
            item = tk.BooleanVar(value=enabled)
            def set_value(name: str = key, var: object = item) -> None:
                try:
                    set_toggle(name, var.get())
                    refresh()
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
    household = sub.add_parser("choose-household", help="Remember a household you selected")
    household.add_argument("household_id")
    household.add_argument("--profile")
    sub.add_parser("gui", help="Open the local Tk settings panel (explicit action only)")
    sub.add_parser("reset-play", help="Restore Play defaults for the active profile")
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
        elif args.command == "choose-household":
            result = set_preferred_household(args.household_id, profile_id=args.profile)
        elif args.command == "reset-play":
            result = reset_launch_preferences()
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
