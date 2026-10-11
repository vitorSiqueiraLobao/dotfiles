#!/usr/bin/env python3
# ARES // efeitos sonoros
# Uso em Python:  import ares_sfx; ares_sfx.play("select")
# Uso no shell:   ares_sfx.py lock
#
# Sons: key nav select open close error pick success notify alert lock tick
# Procura primeiro em ~/.local/share/ares/sounds/<nome>.(wav|ogg|flac|mp3) (seus sons,
# fora do repo) e depois em ~/.config/ares/sounds/<nome>.wav (pacote sintetizado).
# Config em ~/.config/ares/sfx.conf:
#   volume = 0.5     (0 a 1)
#   enabled = true   (false desliga tudo)

import os
import subprocess
import sys
import time

DIRS = [os.path.expanduser("~/.local/share/ares/sounds"), os.path.expanduser("~/.config/ares/sounds")]
CONF = os.path.expanduser("~/.config/ares/sfx.conf")
EXTS = ("wav", "ogg", "flac", "mp3")  # formatos aceitos (o pw-play lê todos)
MIN_GAP = {"key": 0.025, "tick": 0.04, "nav": 0.03}  # evita metralhadora de sons
_last = {}


def _config():
    cfg = {"volume": 0.5, "enabled": True}
    try:
        with open(CONF) as f:
            for line in f:
                line = line.split("#", 1)[0].strip()
                if "=" not in line:
                    continue
                k, v = (x.strip() for x in line.split("=", 1))
                if k == "volume":
                    cfg["volume"] = max(0.0, min(1.0, float(v)))
                elif k == "enabled":
                    cfg["enabled"] = v.lower() in ("1", "true", "yes", "sim", "on")
    except (OSError, ValueError):
        pass
    return cfg


def play(name, volume=None):
    cfg = _config()
    if not cfg["enabled"]:
        return
    now = time.monotonic()
    if now - _last.get(name, 0) < MIN_GAP.get(name, 0):
        return
    _last[name] = now
    for d in DIRS:
        path = next((os.path.join(d, f"{name}.{ext}") for ext in EXTS
                     if os.path.exists(os.path.join(d, f"{name}.{ext}"))), None)
        if path:
            vol = cfg["volume"] if volume is None else volume * cfg["volume"]
            try:
                subprocess.Popen(
                    ["pw-play", "--latency", "20ms", "--volume", f"{vol:.2f}", path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
                )
            except OSError:
                pass
            return


if __name__ == "__main__":
    if len(sys.argv) > 1:
        play(sys.argv[1])
