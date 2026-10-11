#!/usr/bin/env python3
# ARES // menu do sistema
# Drawer abaixo do badge ARES na barra: bloquear, suspender, logout, reiniciar, desligar.
# Ações destrutivas pedem confirmação (segundo clique). Rodar de novo fecha (toggle).
# Teclado: setas para navegar, Enter executa, Esc fecha.
# Deps: python-gobject gtk4 gtk4-layer-shell

import os
import subprocess
from ctypes import CDLL

CDLL("libgtk4-layer-shell.so")  # precisa carregar antes do GTK

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402
from gi.repository import Gtk4LayerShell as LayerShell  # noqa: E402

LOCK = os.path.expanduser("~/.config/hypr/scripts/lock.sh")

# (ícone, rótulo, comando, pede confirmação)
ACTIONS = [
    ("\U000F033E", "BLOQUEAR", [LOCK], False),                                   # nf-md-lock
    ("\U000F04B2", "SUSPENDER", ["sh", "-c", f"{LOCK} & sleep 1; systemctl suspend"], False),  # nf-md-sleep
    ("\U000F0343", "LOGOUT", ["sh", "-c", "command -v hyprshutdown >/dev/null && hyprshutdown || hyprctl dispatch 'hl.dsp.exit()'"], True),  # nf-md-logout
    ("\U000F0709", "REINICIAR", ["systemctl", "reboot"], True),                  # nf-md-restart
    ("\U000F0425", "DESLIGAR", ["systemctl", "poweroff"], True),                 # nf-md-power
]

CSS = """
window.power { background-color: transparent; border: none; box-shadow: none; }
.panel {
    background-color: #100a0e;
    border: 1px solid #3a1018;
    border-top: 1px solid #ff1f3d;
    padding: 10px 10px 12px 10px;
}
.panel * { font-family: "3270 Nerd Font", "JetBrainsMono Nerd Font", monospace; font-size: 16px; }
.title {
    background-color: #ff1f3d;
    color: #08060a;
    letter-spacing: 1px;
    padding: 2px 10px;
}
.uptime { color: #00f0ff; font-size: 13px; margin: 6px 2px 8px 2px; }
button.item {
    background: #160d12;
    background-image: none;
    border: 1px solid #3a1018;
    border-radius: 0;
    box-shadow: none;
    color: #e8e2e4;
    padding: 6px 12px;
    margin-top: 4px;
}
button.item:hover, button.item:focus {
    border-color: #ff1f3d;
    background: #2a0a12;
    outline: none;
}
.item .icon { color: #00f0ff; font-size: 18px; min-width: 28px; }
.item.danger .icon { color: #ff1f3d; }
button.item.confirm { background: #ff1f3d; border-color: #ff5a6e; }
.item.confirm, .item.confirm .icon { color: #08060a; }
.hint { color: #4a3a40; font-size: 12px; margin-top: 8px; }
"""


def uptime():
    try:
        secs = int(float(open("/proc/uptime").read().split()[0]))
    except OSError:
        return ""
    d, rem = divmod(secs, 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    parts = ([f"{d}d"] if d else []) + [f"{h}h", f"{m:02d}m"]
    return "> UPTIME " + " ".join(parts) + f" // {GLib.get_user_name()}@{GLib.get_host_name()}"


class PowerMenu(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="ares.power.menu")
        self.win = None
        self.armed = None  # botão aguardando confirmação

    def do_activate(self):
        if self.win is not None:  # segunda execução = fechar
            self.quit()
            return

        provider = Gtk.CssProvider()
        provider.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

        self.win = Gtk.ApplicationWindow(application=self)
        self.win.add_css_class("power")
        LayerShell.init_for_window(self.win)
        LayerShell.set_namespace(self.win, "ares-power")
        LayerShell.set_layer(self.win, LayerShell.Layer.TOP)
        LayerShell.set_anchor(self.win, LayerShell.Edge.TOP, True)
        LayerShell.set_anchor(self.win, LayerShell.Edge.LEFT, True)
        LayerShell.set_margin(self.win, LayerShell.Edge.TOP, 6)
        LayerShell.set_margin(self.win, LayerShell.Edge.LEFT, 12)
        LayerShell.set_keyboard_mode(self.win, LayerShell.KeyboardMode.ON_DEMAND)

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self.on_key)
        self.win.add_controller(keys)

        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        panel.add_css_class("panel")
        panel.set_size_request(300, -1)

        title = Gtk.Label(label="▓▒░ ARES // SYSTEM ░▒▓", xalign=0)
        title.add_css_class("title")
        up = Gtk.Label(label=uptime(), xalign=0)
        up.add_css_class("uptime")
        panel.append(title)
        panel.append(up)

        self.buttons = []
        for icon, label, cmd, confirm in ACTIONS:
            btn = Gtk.Button()
            btn.add_css_class("item")
            if confirm:
                btn.add_css_class("danger")
            row = Gtk.Box(spacing=8)
            ic = Gtk.Label(label=icon, xalign=0)
            ic.add_css_class("icon")
            txt = Gtk.Label(label=label, xalign=0, hexpand=True)
            row.append(ic)
            row.append(txt)
            btn.set_child(row)
            btn.label_widget = txt
            btn.label_text = label
            btn.connect("clicked", self.on_click, cmd, confirm)
            panel.append(btn)
            self.buttons.append(btn)

        hint = Gtk.Label(label="↑↓ navegar · ENTER executar · ESC fechar", xalign=0)
        hint.add_css_class("hint")
        panel.append(hint)

        self.win.set_child(panel)
        self.win.present()
        self.buttons[0].grab_focus()

    def disarm(self):
        if self.armed is not None:
            self.armed.remove_css_class("confirm")
            self.armed.label_widget.set_text(self.armed.label_text)
            self.armed = None
        return False

    def on_click(self, btn, cmd, confirm):
        if confirm and self.armed is not btn:
            self.disarm()
            self.armed = btn
            btn.add_css_class("confirm")
            btn.label_widget.set_text(f"{btn.label_text} — CONFIRMAR?")
            GLib.timeout_add(3000, lambda: self.disarm() if self.armed is btn else False)
            return
        self.win.set_visible(False)
        subprocess.Popen(cmd, start_new_session=True)
        self.quit()

    def on_key(self, _ctrl, keyval, _code, _state):
        if keyval == Gdk.KEY_Escape:
            self.quit()
            return True
        if keyval in (Gdk.KEY_Down, Gdk.KEY_Up, Gdk.KEY_j, Gdk.KEY_k):
            focused = self.win.get_focus()
            i = self.buttons.index(focused) if focused in self.buttons else 0
            step = 1 if keyval in (Gdk.KEY_Down, Gdk.KEY_j) else -1
            self.buttons[(i + step) % len(self.buttons)].grab_focus()
            return True
        return False


if __name__ == "__main__":
    PowerMenu().run(None)
