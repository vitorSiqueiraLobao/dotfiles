#!/usr/bin/env python3
# ARES // Bluetooth drawer
# Painel layer-shell abaixo da barra: liga/desliga o adaptador, procura dispositivos e
# conecta/desconecta/pareia com um clique. Rodar de novo fecha o painel (Gtk.Application única).
# Uso: bluetooth_menu.py --waybar  -> JSON para o módulo custom/bluetooth
#      bluetooth_menu.py           -> abre/fecha a gaveta
# Deps: python-gobject gtk4 gtk4-layer-shell, bluez-utils (bluetoothctl)

import json
import os
import re
import subprocess
import sys
import threading
from ctypes import CDLL

ICON_OFF = "\U000F00B2"   # nf-md-bluetooth_off
ICON_ON = "\U000F00AF"    # nf-md-bluetooth
ICON_CONN = "\U000F00B1"  # nf-md-bluetooth_connect

MAC_RE = re.compile(r"^([0-9A-F]{2}[:-]){5}[0-9A-F]{2}$", re.I)


def btctl(*args, timeout=20):
    try:
        return subprocess.run(["bluetoothctl", *args], capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


BATTERY_RE = re.compile(r"Battery Percentage: 0x[0-9a-f]+ \((\d+)\)", re.I)


def read_battery(mac, info):
    """Bateria em %: o BlueZ (fones, BLE) ou o driver hid-playstation (DualSense), senão None."""
    m = BATTERY_RE.search(info)
    if m:
        return int(m.group(1))
    try:
        with open(f"/sys/class/power_supply/ps-controller-battery-{mac.lower()}/capacity") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def read_devices():
    """Dispositivos conhecidos pelo BlueZ: [{mac, name, paired, connected, battery}]."""
    devices = []
    for line in btctl("devices").splitlines():
        parts = line.split(" ", 2)
        if len(parts) < 3 or parts[0] != "Device":
            continue
        mac, name = parts[1], parts[2].strip()
        info = btctl("info", mac)
        connected = "Connected: yes" in info
        devices.append({
            "mac": mac,
            "name": name,
            "paired": "Paired: yes" in info,
            "connected": connected,
            "battery": read_battery(mac, info) if connected else None,
        })
    return devices


def powered():
    return "Powered: yes" in btctl("show")


def waybar():
    if not os.path.exists("/sys/class/bluetooth"):
        print(json.dumps({"text": ICON_OFF, "class": "off", "tooltip": "Sem adaptador bluetooth"}, ensure_ascii=False))
        return
    if not powered():
        print(json.dumps({"text": ICON_OFF, "class": "off", "tooltip": "Bluetooth desligado"}, ensure_ascii=False))
        return
    connected = [d["name"] + (f"  {d['battery']}%" if d["battery"] is not None else "")
                 for d in read_devices() if d["connected"]]
    if connected:
        print(json.dumps({"text": ICON_CONN, "class": "connected",
                          "tooltip": "Conectado:\n" + "\n".join(connected)}, ensure_ascii=False))
    else:
        print(json.dumps({"text": ICON_ON, "class": "on", "tooltip": "Bluetooth ligado, nada conectado"}, ensure_ascii=False))


if "--waybar" in sys.argv:
    waybar()
    sys.exit(0)

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

APP_ID = "ares.bluetooth.menu"

CSS = """
window.bluetooth {
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
.btn {
    background: none;
    background-color: #160d12;
    border: 1px solid #3a1018;
    border-radius: 0;
    box-shadow: none;
    color: #7a6f73;
    padding: 2px 8px;
    margin-top: 4px;
    min-height: 0;
}
.btn:hover {
    border-color: #8f1426;
    color: #e8e2e4;
}
.btn.active {
    border-color: #00f0ff;
    color: #00f0ff;
}
.btn.new {
    color: #e8e2e4;
}
.btn.busy {
    border-color: #ffb000;
    color: #ffb000;
}
.status {
    color: #7a6f73;
    margin-top: 8px;
}
.empty {
    color: #7a6f73;
    margin-top: 6px;
}
"""


class Menu(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.win = None
        self.scan = None
        self.busy = set()  # MACs com pareamento/conexão em andamento
        self._sig = None
        self._polling = False

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
        self.win.add_css_class("bluetooth")
        self.win.set_default_size(380, -1)

        LayerShell.init_for_window(self.win)
        LayerShell.set_namespace(self.win, "ares-bluetooth")
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
        title = Gtk.Label(label="▓▒░ BLUETOOTH::LINK ░▒▓", xalign=0)
        title.add_css_class("title")
        panel.append(title)

        self.power_btn = Gtk.Button()
        self.power_btn.add_css_class("btn")
        self.power_btn.connect("clicked", self.on_power)
        panel.append(self.power_btn)

        dev_label = Gtk.Label(label="╔═[ DISPOSITIVOS ]", xalign=0)
        dev_label.add_css_class("section")
        panel.append(dev_label)
        self.dev_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        panel.append(self.dev_box)
        self.empty = Gtk.Label(label="> procurando dispositivos_", xalign=0)
        self.empty.add_css_class("empty")
        panel.append(self.empty)

        self.status = Gtk.Label(label="", xalign=0)
        self.status.add_css_class("status")
        self.status.set_wrap(True)
        self.status.set_max_width_chars(40)
        panel.append(self.status)

        self.win.set_child(panel)
        self.win.present()
        ares_sfx.play("open")

        self.start_scan()
        self.poll()
        GLib.timeout_add_seconds(2, self.poll)

    def do_shutdown(self):
        if self.scan is not None:
            self.scan.terminate()  # o bluetoothctl desliga o discovery ao sair
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

    def start_scan(self):
        if self.scan is None or self.scan.poll() is not None:
            self.scan = subprocess.Popen(
                ["bluetoothctl", "--timeout", "600", "scan", "on"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )

    def set_status(self, text):
        self.status.set_text(text)

    def poll(self):
        """Lê o estado numa thread (cada bluetoothctl leva ~dezenas de ms) e atualiza a UI."""
        if self._polling:
            return True
        self._polling = True

        def work():
            on = powered()
            devs = read_devices() if on else []
            GLib.idle_add(self.render, on, devs)

        threading.Thread(target=work, daemon=True).start()
        return True

    def render(self, on, devices):
        self._polling = False
        self.power_btn.set_label("● ADAPTADOR LIGADO" if on else "○ ADAPTADOR DESLIGADO")
        if on:
            self.power_btn.add_css_class("active")
        else:
            self.power_btn.remove_css_class("active")

        # Dispositivos sem nome (só o MAC) são ruído de anúncios BLE: some, a não ser que já pareados
        devices = [d for d in devices if d["paired"] or d["connected"] or not MAC_RE.match(d["name"])]
        devices.sort(key=lambda d: (not d["connected"], not d["paired"], d["name"].lower()))

        sig = (on, tuple((d["mac"], d["name"], d["paired"], d["connected"], d["battery"]) for d in devices), tuple(sorted(self.busy)))
        if sig != self._sig:
            self._sig = sig
            while (child := self.dev_box.get_first_child()) is not None:
                self.dev_box.remove(child)
            for d in devices:
                busy = d["mac"] in self.busy
                if d["connected"]:
                    mark = "●"
                elif d["paired"]:
                    mark = "○"
                else:
                    mark = "·"
                label = f"{mark} {d['name']}"
                if d["battery"] is not None:
                    label += f"  󰁹 {d['battery']}%"
                if busy:
                    label += "  …"
                btn = Gtk.Button(label=label)
                btn.add_css_class("btn")
                if busy:
                    btn.add_css_class("busy")
                elif d["connected"]:
                    btn.add_css_class("active")
                elif not d["paired"]:
                    btn.add_css_class("new")
                btn.get_child().set_xalign(0)
                btn.get_child().set_ellipsize(3)
                btn.set_tooltip_text(d["mac"])
                btn.connect("clicked", self.on_device, d)
                self.dev_box.append(btn)

        self.empty.set_visible(on and not devices)
        self.empty.set_label("> procurando dispositivos_" if on else "> adaptador desligado_")
        return False

    def on_power(self, _btn):
        ares_sfx.play("nav")

        def work():
            new = "off" if powered() else "on"
            btctl("power", new)
            GLib.idle_add(self.after_power, new == "on")

        threading.Thread(target=work, daemon=True).start()

    def after_power(self, now_on):
        if now_on:
            self.start_scan()
        self._sig = None
        self.poll()

    def on_device(self, _btn, dev):
        mac = dev["mac"]
        if mac in self.busy:
            return
        ares_sfx.play("nav")
        self.busy.add(mac)
        self._sig = None

        def work():
            if dev["connected"]:
                msg = f"desconectando {dev['name']}"
                GLib.idle_add(self.set_status, f"> {msg}…")
                out = btctl("disconnect", mac)
                ok = "Successful" in out
            else:
                if not dev["paired"]:
                    GLib.idle_add(self.set_status, f"> pareando {dev['name']}… (coloque o dispositivo em modo de pareamento)")
                    out = btctl("pair", mac, timeout=40)
                    if "Pairing successful" not in out and "AlreadyExists" not in out:
                        self.finish(mac, f"> falha ao parear {dev['name']}")
                        return
                    btctl("trust", mac)
                GLib.idle_add(self.set_status, f"> conectando {dev['name']}…")
                out = btctl("connect", mac, timeout=30)
                ok = "Connection successful" in out
            self.finish(mac, f"> {dev['name']}: " + ("ok" if ok else "falhou"))

        threading.Thread(target=work, daemon=True).start()

    def finish(self, mac, status):
        def apply():
            self.busy.discard(mac)
            self._sig = None
            self.set_status(status)
            self.poll()
            return False

        GLib.idle_add(apply)


if __name__ == "__main__":
    Menu().run(None)
