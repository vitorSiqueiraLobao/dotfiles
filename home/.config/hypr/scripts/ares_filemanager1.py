#!/usr/bin/env python3
# ARES // org.freedesktop.FileManager1 no lugar do Dolphin
# É o serviço que os apps chamam em "mostrar na pasta" / "abrir pasta" (Firefox, Chromium,
# Electron, portal do xdg). Cada pedido abre o yazi via ares_files.sh. Sai sozinho depois de
# um tempo ocioso; o D-Bus o inicia de novo quando precisar.

import os
import subprocess

from gi.repository import Gio, GLib

LAUNCH = os.path.expanduser("~/.config/hypr/scripts/ares_files.sh")
IDLE_EXIT_S = 120

XML = """
<node>
  <interface name="org.freedesktop.FileManager1">
    <method name="ShowFolders"><arg type="as" direction="in"/><arg type="s" direction="in"/></method>
    <method name="ShowItems"><arg type="as" direction="in"/><arg type="s" direction="in"/></method>
    <method name="ShowItemProperties"><arg type="as" direction="in"/><arg type="s" direction="in"/></method>
  </interface>
</node>
"""

loop = GLib.MainLoop()
idle_id = 0


def arm_idle():
    global idle_id
    if idle_id:
        GLib.source_remove(idle_id)
    idle_id = GLib.timeout_add_seconds(IDLE_EXIT_S, lambda: (loop.quit(), False)[1])


def on_call(conn, sender, path, iface, method, params, invocation):
    uris, _startup = params.unpack()
    # uma janela por item (normalmente vem só um)
    for uri in uris[:4]:
        subprocess.Popen([LAUNCH, uri], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    invocation.return_value(None)
    arm_idle()


def on_bus(conn, name):
    node = Gio.DBusNodeInfo.new_for_xml(XML)
    conn.register_object("/org/freedesktop/FileManager1", node.interfaces[0], on_call, None, None)


Gio.bus_own_name(Gio.BusType.SESSION, "org.freedesktop.FileManager1",
                 Gio.BusNameOwnerFlags.REPLACE | Gio.BusNameOwnerFlags.ALLOW_REPLACEMENT,
                 on_bus, None, lambda *_: loop.quit())
arm_idle()
loop.run()
