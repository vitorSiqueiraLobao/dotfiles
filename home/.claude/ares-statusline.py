#!/usr/bin/env python3
# ARES // barra de status do Claude Code + coleta dos limites de uso
# O Claude Code manda um JSON no stdin a cada atualização; aqui ele:
#   1. salva rate_limits (janela de 5h e semanal) em ~/.cache/ares/claude_limits.json,
#      que o widget da Waybar (waybar/scripts/claude_limits.py) lê;
#   2. imprime a barra de status no tema Cyber-Red.
# Ligado em ~/.claude/settings.json -> "statusLine".

import json
import os
import subprocess
import sys
import time

CACHE = os.path.expanduser("~/.cache/ares/claude_limits.json")

R, C, G, W, A, D = "\033[38;2;255;31;61m", "\033[38;2;0;240;255m", "\033[38;2;122;111;115m", \
    "\033[38;2;232;226;228m", "\033[38;2;255;176;0m", "\033[38;2;42;74;80m"
X = "\033[0m"


def save_limits(rl):
    out = {"updated": int(time.time())}
    for k in ("five_hour", "seven_day"):
        w = rl.get(k)
        if isinstance(w, dict) and w.get("used_percentage") is not None:
            out[k] = {"used": float(w["used_percentage"]), "resets_at": w.get("resets_at")}
    if len(out) == 1:
        return
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    tmp = CACHE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f)
    os.replace(tmp, CACHE)


def meter(pct, n=8):
    full = max(0, min(n, round(pct / 100 * n)))
    col = R if pct >= 90 else A if pct >= 70 else C
    return f"{col}[{'█' * full}{D}{'░' * (n - full)}{col}]{X}"


def main():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        data = {}
    rl = data.get("rate_limits") or {}
    if rl:
        save_limits(rl)

    model = ((data.get("model") or {}).get("display_name") or "claude").upper()
    cwd = (data.get("workspace") or {}).get("current_dir") or data.get("cwd") or os.getcwd()
    home = os.path.expanduser("~")
    short = "~" + cwd[len(home):] if cwd.startswith(home) else cwd

    parts = [f"{R}▓▒░ {W}{model}{R} ░▒▓{X}", f"{C}{short}{X}"]
    try:
        br = subprocess.run(["git", "-C", cwd, "branch", "--show-current"], capture_output=True,
                            text=True, timeout=1).stdout.strip()
        if br:
            parts[-1] += f" {G} {br}{X}"
    except (OSError, subprocess.TimeoutExpired):
        pass

    ctx = (data.get("context_window") or {}).get("used_percentage")
    if ctx is not None:
        parts.append(f"{G}CTX{X} {meter(ctx)} {W}{ctx:.0f}%{X}")
    for key, label in (("five_hour", "5H"), ("seven_day", "7D")):
        w = rl.get(key)
        if isinstance(w, dict) and w.get("used_percentage") is not None:
            p = float(w["used_percentage"])
            parts.append(f"{G}{label}{X} {meter(p)} {W}{p:.0f}%{X}")
    print(f" {R}│{X} ".join(parts))


if __name__ == "__main__":
    main()
