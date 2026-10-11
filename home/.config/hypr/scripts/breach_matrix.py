#!/usr/bin/env python3
# ARES // CODE MATRIX animada do hyprlock (Breach Protocol)
# Uso: breach_matrix.py --static  -> gera uma matriz nova, parada (tela de bloqueio)
#      breach_matrix.py           -> avança um passo da simulação do minigame
# Imprime a matriz em markup pango. O estado fica em $XDG_RUNTIME_DIR, para a
# animação de desbloqueio (breach_success.py) resolver a mesma matriz.
#
# Ciclo: destaca uma linha -> cursor percorre -> escolhe um código (vira [ ])
#        -> destaca a coluna desse código -> ... alterna linha/coluna
#        -> depois de PICKS escolhas, recria a matriz.

import json
import os
import random
import sys

CODES = ["1C", "E9", "55", "BD", "7A", "FF"]
SIZE = 5
PICKS = 6
SCAN_RANGE = (2, 4)  # passos do cursor antes de cada escolha

RED = "#ff1f3d"
CYAN = "#00f0ff"
DARK = "#08060a"
LINE_BG = "#2a0a12"
CURSOR_BG = "#0a3a40"
USED = "#4a3a40"

STATE = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "ares-breach-matrix.json")


def new_state():
    return {
        "grid": [[random.choice(CODES) for _ in range(SIZE)] for _ in range(SIZE)],
        "used": [],
        "mode": "row",       # linha ou coluna destacada
        "line": 0,
        "cursor": 0,         # posição dentro da linha/coluna
        "steps": random.randint(*SCAN_RANGE),
        "phase": "scan",     # scan -> pick -> scan ... -> done
        "buffer": [],
    }


def load():
    try:
        with open(STATE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return new_state()


def cell_of(s, pos):
    return (s["line"], pos) if s["mode"] == "row" else (pos, s["line"])


def free_positions(s):
    used = {tuple(u) for u in s["used"]}
    return [p for p in range(SIZE) if cell_of(s, p) not in used]


def step(s):
    if s["phase"] == "done":
        return new_state()

    if s["phase"] == "pick":
        r, c = cell_of(s, s["cursor"])
        s["used"].append([r, c])
        s["buffer"].append(s["grid"][r][c])
        if len(s["buffer"]) >= PICKS:
            s["phase"] = "done"
            return s
        # alterna linha <-> coluna, como no jogo
        if s["mode"] == "row":
            s["mode"], s["line"] = "col", c
        else:
            s["mode"], s["line"] = "row", r
        free = free_positions(s)
        if not free:
            s["phase"] = "done"
            return s
        s["cursor"] = random.choice(free)
        s["steps"] = random.randint(*SCAN_RANGE)
        s["phase"] = "scan"
        return s

    # scan: cursor anda até a próxima célula livre
    free = free_positions(s)
    if not free:
        s["phase"] = "done"
        return s
    nxt = [p for p in free if p > s["cursor"]] or free
    s["cursor"] = nxt[0]
    s["steps"] -= 1
    if s["steps"] <= 0:
        s["phase"] = "pick"
    return s


def render(s):
    used = {tuple(u) for u in s["used"]}
    cur = cell_of(s, s["cursor"])
    rows = []
    for r in range(SIZE):
        cells = []
        for c in range(SIZE):
            text = "[]" if (r, c) in used else s["grid"][r][c]
            in_line = (s["mode"] == "row" and r == s["line"]) or (s["mode"] == "col" and c == s["line"])
            fg, bg = (USED if (r, c) in used else RED), None
            if s["phase"] != "done" and in_line:
                bg = LINE_BG
            if s["phase"] != "done" and (r, c) == cur:
                fg, bg = (DARK, CYAN) if s["phase"] == "pick" else (CYAN, CURSOR_BG)
            attrs = f"foreground='{fg}'" + (f" background='{bg}'" if bg else "")
            cells.append(f"<span {attrs}>   {text}   </span>")
        rows.append("".join(cells))

    slots = s["buffer"] + ["__"] * (PICKS - len(s["buffer"]))
    if s["phase"] == "done":
        buf = f"<span foreground='{CYAN}'>> UPLOAD OK // {' '.join(s['buffer'])}</span>"
    else:
        buf = f"<span foreground='{CYAN}'>> {' '.join(slots)}</span>"
    return f"<span line_height='1.9'>{chr(10).join(rows)}\n{buf}</span>"


def save(s):
    try:
        with open(STATE, "w") as f:
            json.dump(s, f)
    except OSError:
        pass


def main():
    s = new_state() if "--static" in sys.argv else step(load())
    save(s)
    print(render(s))


if __name__ == "__main__":
    main()
