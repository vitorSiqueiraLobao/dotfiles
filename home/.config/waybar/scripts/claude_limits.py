#!/usr/bin/env python3
# ARES // limites de uso do Claude (janela de 5h e semanal)
# Os números vêm de ~/.cache/ares/claude_limits.json, gravado pela barra de status do
# Claude Code (~/.claude/ares-statusline.py) sempre que ele recebe uma resposta da API.
# Uso: claude_limits.py --waybar  -> JSON para o módulo custom/claude
#      claude_limits.py           -> abre/fecha a gaveta com os detalhes
# Deps: python-gobject gtk4 gtk4-layer-shell

import json
import os
import sys
import time

CACHE = os.path.expanduser("~/.cache/ares/claude_limits.json")
STALE_S = 6 * 3600  # sem notícia há 6h: mostra apagado
N = 8


def load():
    try:
        with open(CACHE) as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    now = time.time()
    for k in ("five_hour", "seven_day"):
        w = d.get(k)
        # janela já resetou desde a última leitura -> uso voltou a zero
        if w and w.get("resets_at") and w["resets_at"] <= now:
            w["used"], w["expired"] = 0.0, True
    return d


def level(p):
    return "crit" if p >= 90 else "warn" if p >= 70 else "ok"


def human(seconds):
    s = max(0, int(seconds))
    d, h, m = s // 86400, s % 86400 // 3600, s % 3600 // 60
    return f"{d}d {h}h" if d else f"{h}h{m:02d}m" if h else f"{m}min"


def reset_text(w):
    ts = w.get("resets_at")
    if not ts or w.get("expired"):
        return "janela nova"
    lt = time.localtime(ts)
    when = time.strftime("%H:%M", lt)
    if ts - time.time() > 86400:
        when = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")[lt.tm_wday] + " " + when
    return f"reset em {human(ts - time.time())} · {when}"


def waybar():
    d = load()
    if not d or "five_hour" not in d:
        print(json.dumps({"text": "CLD <span color='#4a3a40'>[--------]</span> --",
                          "class": "stale",
                          "tooltip": "Sem dados ainda: abra o Claude Code (claude) e mande uma mensagem."}))
        return
    p = d["five_hour"]["used"]
    full = max(0, min(N, round(p / 100 * N)))
    col = {"ok": "#00f0ff", "warn": "#ffb000", "crit": "#ff1f3d"}[level(p)]
    stale = time.time() - d.get("updated", 0) > STALE_S
    if stale:
        col = "#4a3a40"
    text = (f"CLD <span color='{col}'>[{'█' * full}<span color='#2a4a50'>{'░' * (N - full)}</span>]</span> "
            f"{p:.0f}%")
    tip = [f"Sessão 5h: {p:.0f}% · {reset_text(d['five_hour'])}"]
    if "seven_day" in d:
        tip.append(f"Semanal: {d['seven_day']['used']:.0f}% · {reset_text(d['seven_day'])}")
    tip.append(f"sync há {human(time.time() - d.get('updated', 0))}")
    print(json.dumps({"text": text, "class": "stale" if stale else level(max(
        p, d.get("seven_day", {}).get("used", 0))), "tooltip": "\n".join(tip)}))


# --- gaveta ------------------------------------------------------------------
def drawer():
    from ctypes import CDLL
    CDLL("libgtk4-layer-shell.so")  # precisa carregar antes do GTK
    sys.path.insert(0, os.path.expanduser("~/.config/hypr/scripts"))
    import ares_sfx
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gdk, GLib, Gtk
    from gi.repository import Gtk4LayerShell as LayerShell

    css = """
    window.claude { background-color: transparent; border: none; box-shadow: none; }
    .panel { background-color: #100a0e; border: 1px solid #3a1018; border-top: 1px solid #ff1f3d;
             padding: 10px 14px 12px 14px; }
    .panel * { font-family: "3270 Nerd Font", "JetBrainsMono Nerd Font", monospace; font-size: 14px; }
    .title { background-color: #ff1f3d; color: #08060a; letter-spacing: 1px; padding: 2px 10px; margin-bottom: 6px; }
    .section { color: #ff1f3d; margin: 10px 0 2px 0; }
    .name { color: #e8e2e4; }
    .pct { color: #00f0ff; }
    .bar { color: #00f0ff; letter-spacing: 0px; }
    .warn .bar, .warn .pct { color: #ffb000; }
    .crit .bar, .crit .pct { color: #ff1f3d; }
    .sub { color: #7a6f73; font-size: 12px; }
    .foot { color: #4a3a40; font-size: 12px; margin-top: 10px; border-top: 1px solid #3a1018; padding-top: 4px; }
    """
    W = 24

    class App(Gtk.Application):
        def __init__(self):
            super().__init__(application_id="ares.claude.limits")
            self.win = None

        def do_activate(self):
            if self.win is not None:  # segunda execução = fechar
                ares_sfx.play("close")
                self.quit()
                return
            prov = Gtk.CssProvider()
            prov.load_from_string(css)
            Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), prov,
                                                      Gtk.STYLE_PROVIDER_PRIORITY_USER)
            self.win = Gtk.ApplicationWindow(application=self)
            self.win.add_css_class("claude")
            self.win.set_default_size(360, -1)
            LayerShell.init_for_window(self.win)
            LayerShell.set_namespace(self.win, "ares-claude")
            LayerShell.set_layer(self.win, LayerShell.Layer.TOP)
            LayerShell.set_anchor(self.win, LayerShell.Edge.TOP, True)
            LayerShell.set_anchor(self.win, LayerShell.Edge.RIGHT, True)
            LayerShell.set_margin(self.win, LayerShell.Edge.TOP, 6)
            LayerShell.set_margin(self.win, LayerShell.Edge.RIGHT, 12)
            LayerShell.set_keyboard_mode(self.win, LayerShell.KeyboardMode.ON_DEMAND)
            keys = Gtk.EventControllerKey()
            keys.connect("key-pressed", self.on_key)
            self.win.add_controller(keys)

            self.panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self.panel.add_css_class("panel")
            self.win.set_child(self.panel)
            self.refresh()
            GLib.timeout_add_seconds(20, self.refresh)
            self.win.present()
            ares_sfx.play("open")

        def on_key(self, _c, keyval, _code, _state):
            if keyval == Gdk.KEY_Escape:
                ares_sfx.play("close")
                self.quit()
                return True
            return False

        def lbl(self, text, cls, **kw):
            label = Gtk.Label(label=text, xalign=kw.pop("xalign", 0), **kw)
            label.add_css_class(cls)
            return label

        def refresh(self):
            while (child := self.panel.get_first_child()) is not None:
                self.panel.remove(child)
            self.panel.append(self.lbl("▓▒░ CLAUDE::USAGE ░▒▓", "title"))
            d = load()
            if not d or "five_hour" not in d:
                self.panel.append(self.lbl("> sem dados ainda_", "section"))
                self.panel.append(self.lbl("Abra o Claude Code (claude) no terminal e\nmande uma mensagem: "
                                           "os limites chegam\njunto com a resposta.", "sub"))
                return True
            for key, name in (("five_hour", "╔═[ SESSÃO 5H ]"), ("seven_day", "╔═[ SEMANAL ]")):
                w = d.get(key)
                if not w:
                    continue
                p = w["used"]
                box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                box.add_css_class(level(p))
                head = Gtk.Box()
                head.append(self.lbl(name, "section", hexpand=True))
                head.append(self.lbl(f"{p:.0f}%", "pct", xalign=1))
                box.append(head)
                full = max(0, min(W, round(p / 100 * W)))
                box.append(self.lbl("[" + "█" * full + "░" * (W - full) + "]", "bar"))
                box.append(self.lbl(reset_text(w), "sub"))
                self.panel.append(box)
            age = time.time() - d.get("updated", 0)
            foot = f"sync há {human(age)} · via Claude Code"
            if age > STALE_S:
                foot += "\n(desatualizado: use o claude pra atualizar)"
            self.panel.append(self.lbl(foot, "foot"))
            return True

    App().run(None)


if __name__ == "__main__":
    waybar() if "--waybar" in sys.argv else drawer()
