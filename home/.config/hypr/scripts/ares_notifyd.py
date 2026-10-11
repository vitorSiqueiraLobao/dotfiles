#!/usr/bin/env python3
# ARES // notifyd
# Servidor de notificações (org.freedesktop.Notifications) no estilo Cyberpunk:
# painel com cantos cortados, título em caixa alta, linha, etiqueta com o nome do
# app, mensagem em ciano e o ícone do app numa moldura quadrada à direita.
#
# Clique esquerdo: ação padrão do app (se houver) e fecha. Clique direito: fecha.
# Passar o mouse pausa o tempo de expiração.
# Deps: python-gobject gtk4 gtk4-layer-shell

import time
from ctypes import CDLL

CDLL("libgtk4-layer-shell.so")  # precisa carregar antes do GTK

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gsk", "4.0")
gi.require_version("Graphene", "1.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Graphene, Gsk, Gtk, Pango  # noqa: E402
from gi.repository import Gtk4LayerShell as LayerShell  # noqa: E402

# --- Aparência ---------------------------------------------------------------
WIDTH = 440
CUT = 14                 # tamanho do corte diagonal nos cantos
DEFAULT_TIMEOUT = 6000   # ms
MAX_VISIBLE = 5
MARGIN_TOP = 50
MARGIN_RIGHT = 14

BG = "#100a0e"
RED = "#ff1f3d"
CYAN = "#00f0ff"
TEXT = "#e8e2e4"
MUTED = "#4a3a40"
DARK = "#08060a"

CSS = f"""
window.ares-notify {{ background-color: transparent; border: none; box-shadow: none; }}
.ares-notify * {{ font-family: "3270 Nerd Font", "JetBrainsMono Nerd Font", monospace; }}
.slot {{ margin-bottom: 8px; }}
.title {{ color: {TEXT}; font-size: 19px; letter-spacing: 1px; }}
.rule {{ background-color: {RED}; min-height: 2px; margin: 4px 0 7px 0; }}
.tag {{ background-color: {RED}; color: {DARK}; font-size: 13px; padding: 0 6px; }}
.deco {{ color: {MUTED}; font-size: 11px; margin-left: 8px; }}
.body {{ color: {CYAN}; font-size: 15px; margin-top: 7px; }}
.meter {{ color: {CYAN}; font-size: 15px; margin-top: 4px; }}
.iconframe {{ border: 1px solid {CYAN}; min-width: 58px; min-height: 58px; margin-left: 14px; }}
.iconframe.critical {{ border-color: {RED}; }}
.glyph {{ color: {CYAN}; font-size: 28px; }}
.id {{ color: {MUTED}; font-size: 10px; margin-top: 3px; }}
.actions {{ margin-top: 8px; }}
.action {{ background: none; border: 1px solid {RED}; border-radius: 0; color: {TEXT};
           padding: 1px 8px; min-height: 0; box-shadow: none; margin-right: 6px; font-size: 13px; }}
.action:hover {{ background-color: {RED}; color: {DARK}; }}
"""

XML = """
<node>
  <interface name="org.freedesktop.Notifications">
    <method name="GetCapabilities"><arg type="as" direction="out"/></method>
    <method name="Notify">
      <arg type="s" direction="in"/><arg type="u" direction="in"/>
      <arg type="s" direction="in"/><arg type="s" direction="in"/>
      <arg type="s" direction="in"/><arg type="as" direction="in"/>
      <arg type="a{sv}" direction="in"/><arg type="i" direction="in"/>
      <arg type="u" direction="out"/>
    </method>
    <method name="CloseNotification"><arg type="u" direction="in"/></method>
    <method name="GetServerInformation">
      <arg type="s" direction="out"/><arg type="s" direction="out"/>
      <arg type="s" direction="out"/><arg type="s" direction="out"/>
    </method>
    <signal name="NotificationClosed"><arg type="u"/><arg type="u"/></signal>
    <signal name="ActionInvoked"><arg type="u"/><arg type="s"/></signal>
  </interface>
</node>
"""

# Motivos de fechamento (spec)
EXPIRED, DISMISSED, CLOSED_BY_CALL = 1, 2, 3


def rgba(hex_color):
    c = Gdk.RGBA()
    c.parse(hex_color)
    return c


class CutPanel(Gtk.Box):
    """Box com fundo e moldura de cantos cortados (superior esquerdo e inferior direito)."""

    def __init__(self, border, **kw):
        super().__init__(**kw)
        self.border = rgba(border)
        self.fill = rgba(BG)
        self.accent = rgba(RED)

    def do_snapshot(self, snapshot):
        w, h, c = self.get_width(), self.get_height(), CUT
        pb = Gsk.PathBuilder.new()
        pb.move_to(c, 1)
        pb.line_to(w - 1, 1)
        pb.line_to(w - 1, h - c)
        pb.line_to(w - c, h - 1)
        pb.line_to(1, h - 1)
        pb.line_to(1, c)
        pb.close()
        path = pb.to_path()
        snapshot.push_fill(path, Gsk.FillRule.WINDING)
        snapshot.append_color(self.fill, Graphene.Rect().init(0, 0, w, h))
        snapshot.pop()
        snapshot.append_stroke(path, Gsk.Stroke.new(2.0), self.border)
        # detalhes: faixa grossa no topo e marca na lateral, como na HUD do jogo
        snapshot.append_color(self.accent, Graphene.Rect().init(c + 6, 0, 70, 4))
        snapshot.append_color(self.accent, Graphene.Rect().init(0, c + 10, 4, 22))
        Gtk.Box.do_snapshot(self, snapshot)


class TintedIcon(Gtk.Widget):
    """Ícone redesenhado como holograma monocromático (igual ao lançador): a
    luminosidade vira a cor do HUD e uma silhueta fraca vem da transparência.
    Imagens não quadradas são encaixadas mantendo a proporção."""

    def __init__(self, paintable, size, color):
        super().__init__()
        self.paintable, self.size, self.color = paintable, size, rgba(color)

    def do_measure(self, orientation, for_size):
        return self.size, self.size, -1, -1

    def do_snapshot(self, snapshot):
        s = self.size
        ratio = self.paintable.get_intrinsic_aspect_ratio() or 1.0
        w, h = (s, s / ratio) if ratio >= 1 else (s * ratio, s)
        snapshot.save()
        snapshot.translate(Graphene.Point().init((s - w) / 2, (s - h) / 2))
        rect = Graphene.Rect().init(0, 0, w, h)
        snapshot.push_opacity(0.35)
        snapshot.push_mask(Gsk.MaskMode.ALPHA)
        self.paintable.snapshot(snapshot, w, h)
        snapshot.pop()
        snapshot.append_color(self.color, rect)
        snapshot.pop()
        snapshot.pop()
        snapshot.push_mask(Gsk.MaskMode.LUMINANCE)
        self.paintable.snapshot(snapshot, w, h)
        snapshot.pop()
        snapshot.append_color(self.color, rect)
        snapshot.pop()
        snapshot.restore()


class Notifyd(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="ares.notifyd")
        self.next_id = 1
        self.items = {}   # id -> dict(widget, revealer, timer, timeout, actions)
        self.conn = None

    # --- D-Bus ---------------------------------------------------------------
    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.hold()
        provider = Gtk.CssProvider()
        provider.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )
        self.build_window()
        self.node = Gio.DBusNodeInfo.new_for_xml(XML)
        Gio.bus_own_name(
            Gio.BusType.SESSION,
            "org.freedesktop.Notifications",
            Gio.BusNameOwnerFlags.ALLOW_REPLACEMENT | Gio.BusNameOwnerFlags.REPLACE,
            self.on_bus,
            None,
            lambda *a: self.quit(),  # outro servidor assumiu o nome
        )

    def do_activate(self):
        pass

    def on_bus(self, conn, name):
        self.conn = conn
        conn.register_object(
            "/org/freedesktop/Notifications", self.node.interfaces[0], self.on_call, None, None
        )

    def on_call(self, conn, sender, path, iface, method, params, inv):
        if method == "GetCapabilities":
            inv.return_value(GLib.Variant("(as)", (["body", "body-markup", "actions", "icon-static"],)))
        elif method == "GetServerInformation":
            inv.return_value(GLib.Variant("(ssss)", ("ares-notifyd", "ARES", "1.0", "1.2")))
        elif method == "CloseNotification":
            self.close(params.get_child_value(0).get_uint32(), CLOSED_BY_CALL)
            inv.return_value(None)
        elif method == "Notify":
            nid = self.notify(params)
            inv.return_value(GLib.Variant("(u)", (nid,)))

    def emit(self, signal, variant):
        if self.conn:
            self.conn.emit_signal(None, "/org/freedesktop/Notifications",
                                  "org.freedesktop.Notifications", signal, variant)

    # --- Janela --------------------------------------------------------------
    def build_window(self):
        self.win = Gtk.ApplicationWindow(application=self)
        self.win.add_css_class("ares-notify")
        self.win.set_default_size(WIDTH, 1)
        LayerShell.init_for_window(self.win)
        LayerShell.set_namespace(self.win, "ares-notify")
        LayerShell.set_layer(self.win, LayerShell.Layer.OVERLAY)
        LayerShell.set_anchor(self.win, LayerShell.Edge.TOP, True)
        LayerShell.set_anchor(self.win, LayerShell.Edge.RIGHT, True)
        LayerShell.set_margin(self.win, LayerShell.Edge.TOP, MARGIN_TOP)
        LayerShell.set_margin(self.win, LayerShell.Edge.RIGHT, MARGIN_RIGHT)
        LayerShell.set_keyboard_mode(self.win, LayerShell.KeyboardMode.NONE)
        self.stack = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.stack.set_size_request(WIDTH, -1)
        self.win.set_child(self.stack)

    def refresh_window(self):
        if self.items:
            self.win.set_default_size(WIDTH, 1)
            self.win.present()
        else:
            self.win.set_visible(False)

    # --- Notificações --------------------------------------------------------
    def notify(self, params):
        app_name = params.get_child_value(0).get_string() or "SISTEMA"
        replaces = params.get_child_value(1).get_uint32()
        app_icon = params.get_child_value(2).get_string()
        summary = params.get_child_value(3).get_string()
        body = params.get_child_value(4).get_string()
        actions = list(params.get_child_value(5).unpack())
        hints = params.get_child_value(6)
        timeout = params.get_child_value(7).get_int32()

        urgency = hints.lookup_value("urgency", None)
        critical = urgency is not None and urgency.get_byte() == 2
        value = hints.lookup_value("value", None)

        nid = replaces if replaces in self.items else self.next_id
        if nid == self.next_id:
            self.next_id += 1

        card = self.build_card(nid, app_name, app_icon, summary, body, actions, hints,
                               critical, value.get_int32() if value is not None else None)

        if nid in self.items:  # substituição: troca o conteúdo no mesmo lugar
            item = self.items[nid]
            item["revealer"].set_child(card)
            self.cancel_timer(item)
        else:
            revealer = Gtk.Revealer(transition_type=Gtk.RevealerTransitionType.SLIDE_DOWN,
                                    transition_duration=180)
            revealer.set_child(card)
            self.stack.prepend(revealer)
            item = {"revealer": revealer, "timer": None}
            self.items[nid] = item
            GLib.idle_add(revealer.set_reveal_child, True)

        if timeout < 0:
            timeout = DEFAULT_TIMEOUT
        item.update(timeout=0 if critical else timeout, actions=actions, started=time.monotonic())
        self.start_timer(nid)

        # limita a quantidade na tela (fecha as mais antigas)
        while len(self.items) > MAX_VISIBLE:
            self.close(min(self.items), EXPIRED)

        self.refresh_window()
        return nid

    def build_card(self, nid, app_name, app_icon, summary, body, actions, hints, critical, value):
        card = CutPanel(CYAN if critical else RED)
        inner = Gtk.Box(margin_top=14, margin_bottom=14, margin_start=20, margin_end=16, hexpand=True)
        card.append(inner)

        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        title = Gtk.Label(label=summary.upper(), xalign=0, wrap=True,
                          wrap_mode=Pango.WrapMode.WORD_CHAR, max_width_chars=26)
        title.add_css_class("title")
        rule = Gtk.Box(halign=Gtk.Align.START)
        rule.set_size_request(int(WIDTH * 0.55), 2)
        rule.add_css_class("rule")
        row = Gtk.Box()
        tag = Gtk.Label(label=app_name.upper())
        tag.add_css_class("tag")
        deco = Gtk.Label(label=f"ARES//NET ▓▒░ 0x{nid:04X}")
        deco.add_css_class("deco")
        row.append(tag)
        row.append(deco)
        left.append(title)
        left.append(rule)
        left.append(row)

        if body:
            lbl = Gtk.Label(xalign=0, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR,
                            max_width_chars=34, lines=4, ellipsize=Pango.EllipsizeMode.END)
            try:
                Pango.parse_markup(body, -1, "\0")
                lbl.set_markup(body)
            except GLib.Error:
                lbl.set_text(body)
            lbl.add_css_class("body")
            left.append(lbl)

        if value is not None:
            v = max(0, min(100, value))
            filled = round(v / 12.5)
            meter = Gtk.Label(xalign=0)
            meter.set_markup(f"[{'█' * filled}<span foreground='{MUTED}'>{'░' * (8 - filled)}</span>] {v}%")
            meter.add_css_class("meter")
            left.append(meter)

        labels = dict(zip(actions[::2], actions[1::2]))
        extra = {k: v for k, v in labels.items() if k != "default"}
        if extra:
            bar = Gtk.Box()
            bar.add_css_class("actions")
            for key, label in extra.items():
                b = Gtk.Button(label=f"[ {label.upper()} ]")
                b.add_css_class("action")
                b.connect("clicked", lambda _b, k=key: self.invoke(nid, k))
                bar.append(b)
            left.append(bar)

        frame = Gtk.Box(valign=Gtk.Align.START, halign=Gtk.Align.END)
        frame.add_css_class("iconframe")
        if critical:
            frame.add_css_class("critical")
        frame.append(self.icon_widget(app_name, app_icon, hints, critical))
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        right.append(frame)
        ident = Gtk.Label(label=f"{nid:02d}", xalign=1)
        ident.add_css_class("id")
        right.append(ident)

        inner.append(left)
        inner.append(right)

        click = Gtk.GestureClick(button=0)
        click.connect("released", self.on_click, nid)
        card.add_controller(click)
        motion = Gtk.EventControllerMotion()
        motion.connect("enter", lambda *_: self.cancel_timer(self.items.get(nid)))
        motion.connect("leave", lambda *_: self.start_timer(nid))
        card.add_controller(motion)
        slot = Gtk.Box()
        slot.add_css_class("slot")
        slot.append(card)
        return slot

    def icon_widget(self, app_name, app_icon, hints, critical):
        """Ícone no estilo holograma do HUD: ciano (ou vermelho se crítica)."""
        paintable = self.icon_paintable(app_name, app_icon, hints)
        if paintable is None:  # sem ícone: símbolo genérico
            glyph = Gtk.Label(label="\U000F009A", hexpand=True)  # nf-md-bell
            glyph.add_css_class("glyph")
            return glyph
        icon = TintedIcon(paintable, 40, RED if critical else CYAN)
        icon.set_halign(Gtk.Align.CENTER)
        icon.set_valign(Gtk.Align.CENTER)
        icon.set_hexpand(True)
        return icon

    def icon_paintable(self, app_name, app_icon, hints):
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())

        def themed(name):
            return theme.lookup_icon(name, None, 40, 2, Gtk.TextDirection.NONE, 0)

        # 1) imagem enviada pelo app (bytes)
        for key in ("image-data", "image_data", "icon_data"):
            v = hints.lookup_value(key, None)
            if v is not None:
                try:
                    w, h, stride = (v.get_child_value(i).get_int32() for i in range(3))
                    alpha = v.get_child_value(3).get_boolean()
                    data = v.get_child_value(6).get_data_as_bytes()
                    pix = GdkPixbuf.Pixbuf.new_from_bytes(data, GdkPixbuf.Colorspace.RGB, alpha, 8, w, h, stride)
                    return Gdk.Texture.new_for_pixbuf(pix)
                except (GLib.Error, TypeError, ValueError):
                    pass
        # 2) caminho de imagem ou nome de ícone
        p = hints.lookup_value("image-path", None) or hints.lookup_value("image_path", None)
        for src in ([p.get_string()] if p is not None else []) + [app_icon]:
            if not src:
                continue
            if src.startswith("file://"):
                src = src[7:]
            if src.startswith("/"):
                try:
                    return Gdk.Texture.new_from_filename(src)
                except GLib.Error:
                    continue
            if theme.has_icon(src):
                return themed(src)
        # 3) ícone pelo nome do app
        for guess in (app_name.lower(), app_name.lower().replace(" ", "-")):
            if theme.has_icon(guess):
                return themed(guess)
        return None

    def has_icon(self, name):
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        return theme.has_icon(name)

    # --- Tempo, cliques e fechamento -----------------------------------------
    def start_timer(self, nid):
        item = self.items.get(nid)
        if not item or item["timeout"] <= 0:
            return
        self.cancel_timer(item)
        item["timer"] = GLib.timeout_add(item["timeout"], self.on_timeout, nid)

    def cancel_timer(self, item):
        if item and item.get("timer"):
            GLib.source_remove(item["timer"])
            item["timer"] = None

    def on_timeout(self, nid):
        if nid in self.items:
            self.items[nid]["timer"] = None
            self.close(nid, EXPIRED)
        return False

    def on_click(self, gesture, n_press, x, y, nid):
        item = self.items.get(nid)
        if not item:
            return
        if gesture.get_current_button() == 1 and "default" in item["actions"][::2]:
            self.invoke(nid, "default")
        else:
            self.close(nid, DISMISSED)

    def invoke(self, nid, key):
        self.emit("ActionInvoked", GLib.Variant("(us)", (nid, key)))
        self.close(nid, DISMISSED)

    def close(self, nid, reason):
        item = self.items.pop(nid, None)
        if not item:
            return
        self.cancel_timer(item)
        rev = item["revealer"]
        rev.set_reveal_child(False)

        def remove():
            self.stack.remove(rev)
            self.refresh_window()
            return False

        GLib.timeout_add(rev.get_transition_duration() + 20, remove)
        self.emit("NotificationClosed", GLib.Variant("(uu)", (nid, reason)))


if __name__ == "__main__":
    Notifyd().run(None)
