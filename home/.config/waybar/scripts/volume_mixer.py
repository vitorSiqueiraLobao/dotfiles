#!/usr/bin/env python3
# ARES // Volume mixer drawer
# Painel layer-shell abaixo da barra com um slider por app tocando som.
# Rodar de novo fecha o painel (Gtk.Application única = toggle).
# Deps: python-gobject gtk4 gtk4-layer-shell, pactl (pipewire-pulse)

import json
import os
import subprocess
import sys
import threading
from ctypes import CDLL

CDLL("libgtk4-layer-shell.so")  # precisa carregar antes do GTK

sys.path.insert(0, os.path.expanduser("~/.config/hypr/scripts"))
import ares_sfx  # noqa: E402

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402
from gi.repository import Gtk4LayerShell as LayerShell  # noqa: E402
import ares_backdrop  # noqa: E402

APP_ID = "ares.volume.mixer"
MAX_VOLUME = 150
ICON_ON = "\U000F057E"   # nf-md-volume_high
ICON_OFF = "\U000F075F"  # nf-md-volume_mute

CSS = """
window.mixer {
    background-color: transparent;
    border: none;
    box-shadow: none;
}
.panel {
    background-color: #100a0e;
    border: 1px solid #3a1018;
    border-top: 1px solid #ff1f3d;
    padding: 10px 12px 12px 12px;
}
.panel * {
    font-family: "3270 Nerd Font", "JetBrainsMono Nerd Font", monospace;
    font-size: 14px;
}
.title {
    background-color: #ff1f3d;
    color: #08060a;
    letter-spacing: 1px;
    padding: 2px 10px;
    margin-bottom: 8px;
}
.section {
    color: #ff1f3d;
    margin: 8px 0 2px 0;
}
.row {
    background-color: #160d12;
    border: 1px solid #3a1018;
    padding: 4px 8px;
    margin-top: 4px;
}
.row:hover {
    border-color: #8f1426;
}
.name {
    color: #e8e2e4;
}
.muted .name, .muted .pct {
    color: #4a3a40;
}
.pct {
    color: #00f0ff;
    min-width: 44px;
}
.mute {
    background: none;
    border: none;
    box-shadow: none;
    color: #00f0ff;
    padding: 0 6px;
    min-height: 0;
    font-size: 16px;
}
.muted .mute {
    color: #ff1f3d;
}
.empty {
    color: #7a6f73;
    margin-top: 6px;
}
scale trough {
    background-color: #2a141c;
    background-image: none;
    border: none;
    outline: none;
    min-height: 4px;
    border-radius: 0;
}
scale highlight {
    background-color: #00f0ff;
    background-image: none;
    border: none;
    border-radius: 0;
}
.muted scale highlight {
    background-color: #4a3a40;
}
scale slider {
    background-color: #ff1f3d;
    background-image: none;
    border: 1px solid #ff5a6e;
    border-radius: 0;
    min-width: 10px;
    min-height: 14px;
    margin: -6px 0;
    box-shadow: none;
}
scale marks {
    color: #4a3a40;
}
"""


def pactl(*args):
    return subprocess.run(["pactl", *args], capture_output=True, text=True).stdout


def pactl_json(*args):
    try:
        return json.loads(pactl("-f", "json", *args) or "[]")
    except json.JSONDecodeError:
        return []


def volume_percent(vol):
    channels = list(vol.values())
    if not channels:
        return 0
    return round(sum(int(c["value_percent"].rstrip("%")) for c in channels) / len(channels))


def read_playing():
    """Títulos de mídia tocando agora via MPRIS: {app em minúsculas: [títulos]}.
    O Firefox não diz qual stream é de qual aba; o MPRIS só dá a mídia ativa."""
    out = subprocess.run(
        ["playerctl", "-a", "metadata", "--format", "{{playerName}}\t{{status}}\t{{title}}"],
        capture_output=True, text=True,
    ).stdout
    playing = {}
    for line in out.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3 and parts[1] == "Playing" and parts[2].strip():
            playing.setdefault(parts[0].lower(), []).append(parts[2].strip())
    return playing


def label_apps(apps):
    """Põe o título da mídia no nome quando dá pra ter certeza (1 stream ↔ 1 player);
    com vários streams do mesmo app, numera as linhas (#1 = mais antigo)."""
    groups = {}
    for a in apps:
        groups.setdefault(a["app"], []).append(a)
    playing = read_playing() if apps else {}
    for app, streams in groups.items():
        titles = playing.get(app, [])
        if len(streams) == 1:
            if len(titles) == 1 and not streams[0]["detailed"]:
                streams[0]["name"] += f" — {titles[0]}"
        else:
            for n, a in enumerate(streams, 1):
                a["name"] += f" #{n}"


def read_state():
    """Saída padrão + streams de apps."""
    default = pactl("get-default-sink").strip()
    sink = None
    for s in pactl_json("list", "sinks"):
        if s["name"] == default:
            sink = {
                "key": "sink",
                "id": s["index"],
                "name": s.get("description", s["name"]),
                "volume": volume_percent(s["volume"]),
                "mute": s["mute"],
            }
    apps = []
    for s in pactl_json("list", "sink-inputs"):
        p = s.get("properties", {})
        if p.get("ares.sfx"):  # efeitos sonoros do próprio ARES (ares_sfx.py / keysfx.bash)
            continue
        name = p.get("application.name") or p.get("media.name") or f"Stream {s['index']}"
        media = p.get("media.name", "")
        detailed = bool(media) and media not in (name, "(null)", "AudioStream", "Playback", "audio stream")
        if detailed:
            name = f"{name} — {media}"
        apps.append({
            "key": f"in{s['index']}",
            "id": s["index"],
            "name": name,
            "detailed": detailed,  # o app já informa a mídia no media.name (ex.: Spotify)
            "app":(p.get("application.process.binary") or p.get("application.name") or "").lower(),
            "volume": volume_percent(s["volume"]),
            "mute": s["mute"],
        })
    label_apps(apps)
    return sink, apps


class Row(Gtk.Box):
    def __init__(self, item, kind):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.add_css_class("row")
        self.kind = kind  # "sink" ou "sink-input"
        self.id = item["id"]
        self._updating = False

        top = Gtk.Box(spacing=6)
        self.name = Gtk.Label(xalign=0, hexpand=True)
        self.name.add_css_class("name")
        self.name.set_ellipsize(3)  # END
        self.name.set_max_width_chars(34)
        self.pct = Gtk.Label(xalign=1)
        self.pct.add_css_class("pct")
        top.append(self.name)
        top.append(self.pct)

        bottom = Gtk.Box(spacing=4)
        self.mute = Gtk.Button()
        self.mute.add_css_class("mute")
        self.mute.connect("clicked", self.on_mute)
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, MAX_VOLUME, 1)
        self.scale.set_draw_value(False)
        self.scale.set_hexpand(True)
        self.scale.add_mark(100, Gtk.PositionType.BOTTOM, None)
        self.scale.connect("value-changed", self.on_scale)
        bottom.append(self.mute)
        bottom.append(self.scale)

        self.append(top)
        self.append(bottom)
        self.update(item)

    def update(self, item):
        self.name.set_text(item["name"])
        self.name.set_tooltip_text(item["name"])
        self.mute.set_label(ICON_OFF if item["mute"] else ICON_ON)
        if item["mute"]:
            self.add_css_class("muted")
        else:
            self.remove_css_class("muted")
        if abs(self.scale.get_value() - item["volume"]) >= 1:
            self._updating = True
            self.scale.set_value(item["volume"])
            self._updating = False
        self.pct.set_text(f"{item['volume']}%")

    def on_scale(self, scale):
        value = int(scale.get_value())
        self.pct.set_text(f"{value}%")
        if not self._updating:
            ares_sfx.play("tick")
            subprocess.Popen(["pactl", f"set-{self.kind}-volume", str(self.id), f"{value}%"])

    def on_mute(self, _btn):
        ares_sfx.play("nav")
        subprocess.Popen(["pactl", f"set-{self.kind}-mute", str(self.id), "toggle"])


class Mixer(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.win = None
        self.sub = None
        self.rows = {}
        self._refresh_pending = False

    def do_activate(self):
        # Segunda execução = fechar (toggle pelo ícone da barra)
        if self.win is not None:
            ares_sfx.play("close")
            self.quit()
            return

        provider = Gtk.CssProvider()
        provider.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

        ares_backdrop.attach(self, self.dismiss)  # antes do painel, para ficar por baixo
        self.win = Gtk.ApplicationWindow(application=self)
        self.win.add_css_class("mixer")
        self.win.set_default_size(380, -1)

        LayerShell.init_for_window(self.win)
        LayerShell.set_namespace(self.win, "ares-mixer")
        LayerShell.set_layer(self.win, LayerShell.Layer.TOP)
        LayerShell.set_anchor(self.win, LayerShell.Edge.TOP, True)
        LayerShell.set_anchor(self.win, LayerShell.Edge.RIGHT, True)
        LayerShell.set_margin(self.win, LayerShell.Edge.TOP, 6)
        LayerShell.set_margin(self.win, LayerShell.Edge.RIGHT, 12)
        LayerShell.set_keyboard_mode(self.win, LayerShell.KeyboardMode.ON_DEMAND)

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self.on_key)
        self.win.add_controller(keys)

        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        panel.add_css_class("panel")
        title = Gtk.Label(label="▓▒░ AUDIO::MIXER ░▒▓", xalign=0)
        title.add_css_class("title")
        panel.append(title)

        out_label = Gtk.Label(label="╔═[ SAÍDA ]", xalign=0)
        out_label.add_css_class("section")
        panel.append(out_label)
        self.sink_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        panel.append(self.sink_box)

        apps_label = Gtk.Label(label="╔═[ APPS ]", xalign=0)
        apps_label.add_css_class("section")
        panel.append(apps_label)
        self.apps_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        panel.append(self.apps_box)
        self.empty = Gtk.Label(label="> nenhum app tocando som_", xalign=0)
        self.empty.add_css_class("empty")
        panel.append(self.empty)

        self.win.set_child(panel)
        self.refresh()
        self.win.present()
        ares_sfx.play("open")

        threading.Thread(target=self.watch, daemon=True).start()

    def do_shutdown(self):
        if self.sub is not None:
            self.sub.terminate()
        Gtk.Application.do_shutdown(self)

    def dismiss(self):
        """Clique fora do painel."""
        ares_sfx.play("close")
        self.quit()

    def on_key(self, _ctrl, keyval, _code, _state):
        if keyval == Gdk.KEY_Escape:
            ares_sfx.play("close")
            self.quit()
            return True
        return False

    def watch(self):
        """Atualiza ao vivo quando apps abrem/fecham ou mudam volume."""
        self.sub = subprocess.Popen(["pactl", "subscribe"], stdout=subprocess.PIPE, text=True)
        for line in self.sub.stdout:
            if "sink" in line or "server" in line:
                GLib.idle_add(self.schedule_refresh)

    def schedule_refresh(self):
        if not self._refresh_pending:
            self._refresh_pending = True
            GLib.timeout_add(80, self.refresh)
        return False

    def refresh(self):
        self._refresh_pending = False
        sink, apps = read_state()

        wanted = {}
        if sink:
            wanted[sink["key"]] = (sink, "sink", self.sink_box)
        for a in apps:
            wanted[a["key"]] = (a, "sink-input", self.apps_box)

        for key in list(self.rows):
            row = self.rows[key]
            if key not in wanted or (key == "sink" and row.id != sink["id"]):
                row.get_parent().remove(row)
                del self.rows[key]

        for key, (item, kind, box) in wanted.items():
            if key in self.rows:
                self.rows[key].update(item)
            else:
                row = Row(item, kind)
                self.rows[key] = row
                box.append(row)

        self.empty.set_visible(not apps)
        return False


if __name__ == "__main__":
    Mixer().run(None)
