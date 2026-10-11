#!/usr/bin/env python3
# ARES // launcher
# Lançador de apps no estilo HUD (Breach Protocol): cantos cortados, ícones em
# molduras, painel DAEMON INFO com detalhes do app selecionado.
# Busca aproximada; apps mais usados aparecem primeiro (contagem em
# ~/.local/state/ares/launcher.json). Rodar de novo fecha (toggle).
# Teclado: digite para buscar, ↑↓ navegar, Enter executar, Esc fechar.
# Deps: python-gobject gtk4 gtk4-layer-shell

import json
import os
import sys
from ctypes import CDLL

CDLL("libgtk4-layer-shell.so")  # precisa carregar antes do GTK

sys.path.insert(0, os.path.expanduser("~/.config/hypr/scripts"))
import ares_sfx  # noqa: E402

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gsk", "4.0")
gi.require_version("Graphene", "1.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gdk, Gio, GLib, Graphene, Gsk, Gtk, Pango  # noqa: E402
from gi.repository import Gtk4LayerShell as LayerShell  # noqa: E402

STATE = os.path.join(GLib.get_user_state_dir(), "ares", "launcher.json")
MAX_RESULTS = 60
CUT = 16

BG, RED, CYAN, TEXT, MUTED, LINE, DARK = (
    "#100a0e", "#ff1f3d", "#00f0ff", "#e8e2e4", "#7a6f73", "#3a1018", "#08060a"
)

CSS = f"""
window.launcher {{ background-color: transparent; border: none; box-shadow: none; }}
.launcher * {{ font-family: "3270 Nerd Font", "JetBrainsMono Nerd Font", monospace; }}
.head {{ background-color: {RED}; color: {DARK}; font-size: 15px; padding: 3px 10px; letter-spacing: 1px; }}
.search {{ border: 1px solid {RED}; background-color: {DARK}; margin: 10px 0 8px 0; padding: 0 10px; }}
.prompt {{ color: {RED}; font-size: 18px; margin-right: 8px; }}
.search entry, .search text {{ background: none; border: none; box-shadow: none; outline: none;
    color: {CYAN}; caret-color: {CYAN}; font-size: 18px; padding: 8px 0; min-height: 0; }}
.search placeholder {{ color: #4a3a40; }}
list {{ background: none; }}
row {{ background: none; border-left: 3px solid transparent; padding: 5px 8px; outline: none; }}
row:hover {{ background-color: #1a0f14; }}
row:selected {{ background-color: #2a0a12; border-left-color: {CYAN}; }}
.iconframe {{ border: 1px solid {LINE}; margin-right: 12px; padding: 5px; }}
row:selected .iconframe {{ border-color: {CYAN}; }}
.name {{ color: {TEXT}; font-size: 16px; }}
row:selected .name {{ color: {CYAN}; }}
.hex {{ color: {MUTED}; font-size: 11px; }}
.hint {{ color: #4a3a40; font-size: 12px; margin-top: 8px; }}
.empty {{ color: {MUTED}; font-size: 14px; margin: 14px 4px; }}
.info-title {{ color: {RED}; font-size: 13px; }}
.bigframe {{ border: 1px solid {CYAN}; margin: 14px 0; padding: 10px; }}
.info-name {{ color: {CYAN}; font-size: 18px; }}
.info-desc {{ color: {TEXT}; font-size: 13px; margin-top: 6px; }}
.tag {{ background-color: {RED}; color: {DARK}; font-size: 11px; padding: 0 5px; margin: 0 4px 4px 0; }}
.cmd {{ color: {MUTED}; font-size: 11px; margin-top: 12px; }}
.stat {{ color: {MUTED}; font-size: 11px; margin-top: 4px; }}
scrollbar {{ background: none; border: none; }}
scrollbar slider {{ background-color: {LINE}; min-width: 3px; border-radius: 0; }}
"""


def rgba(hex_color):
    c = Gdk.RGBA()
    c.parse(hex_color)
    return c


class CutPanel(Gtk.Box):
    """Box com fundo e moldura de cantos cortados (sem padding no próprio painel)."""

    def __init__(self, border, accent=True, **kw):
        super().__init__(**kw)
        self.border, self.fill, self.red = rgba(border), rgba(BG), rgba(RED)
        self.accent = accent

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
        if self.accent:
            snapshot.append_color(self.red, Graphene.Rect().init(c + 8, 0, 90, 4))
            snapshot.append_color(self.red, Graphene.Rect().init(0, c + 12, 4, 26))
        Gtk.Box.do_snapshot(self, snapshot)


class TintedIcon(Gtk.Widget):
    """Ícone do app redesenhado como holograma monocromático na paleta do HUD.
    Usa a luminosidade do ícone como máscara (mantém os detalhes) + uma silhueta
    fraca pela transparência (para ícones escuros não sumirem).
    Cor: ciano quando a linha está selecionada (ou fixed=CYAN), vermelho nas demais."""

    def __init__(self, gicon, size, fixed=None):
        super().__init__()
        self.size, self.fixed = size, fixed
        self.paintable = None
        self.set_gicon(gicon)

    def set_gicon(self, gicon):
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        if gicon is None:
            gicon = Gio.ThemedIcon.new("application-x-executable")
        self.paintable = theme.lookup_by_gicon(gicon, self.size, 2, Gtk.TextDirection.NONE, 0)
        self.queue_draw()

    def do_measure(self, orientation, for_size):
        return self.size, self.size, -1, -1

    def do_snapshot(self, snapshot):
        if self.paintable is None:
            return
        row = self.get_ancestor(Gtk.ListBoxRow)
        color = self.fixed or (CYAN if row is not None and row.is_selected() else RED)
        c = rgba(color)
        rect = Graphene.Rect().init(0, 0, self.size, self.size)
        # silhueta fraca (transparência do ícone)
        snapshot.push_opacity(0.35)
        snapshot.push_mask(Gsk.MaskMode.ALPHA)
        self.paintable.snapshot(snapshot, self.size, self.size)
        snapshot.pop()
        snapshot.append_color(c, rect)
        snapshot.pop()
        snapshot.pop()
        # detalhes (luminosidade do ícone)
        snapshot.push_mask(Gsk.MaskMode.LUMINANCE)
        self.paintable.snapshot(snapshot, self.size, self.size)
        snapshot.pop()
        snapshot.append_color(c, rect)
        snapshot.pop()


def load_counts():
    try:
        with open(STATE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_counts(counts):
    try:
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        with open(STATE, "w") as f:
            json.dump(counts, f)
    except OSError:
        pass


def score(app, query):
    """Pontuação da busca: prefixo > início de palavra > trecho > subsequência."""
    name = (app.get_name() or "").lower()
    if not query:
        return 1
    best = 0
    fields = [name, (app.get_generic_name() or "").lower(), (app.get_executable() or "").lower(),
              " ".join(app.get_keywords() or []).lower()]
    for weight, text in zip((1.0, 0.7, 0.6, 0.5), fields):
        if not text:
            continue
        if text.startswith(query):
            s = 100
        elif f" {query}" in f" {text}":
            s = 80
        elif query in text:
            s = 60
        else:
            it = iter(text)
            s = 25 if all(ch in it for ch in query) else 0
        best = max(best, s * weight)
    return best


class Launcher(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="ares.launcher")
        self.win = None
        self.counts = load_counts()
        self.apps = [a for a in Gio.AppInfo.get_all()
                     if a.should_show() and hasattr(a, "get_categories")]
        self.results = []

    def do_activate(self):
        if self.win is not None:  # segunda execução = fechar
            ares_sfx.play("close")
            self.quit()
            return

        provider = Gtk.CssProvider()
        provider.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

        self.win = Gtk.ApplicationWindow(application=self)
        self.win.add_css_class("launcher")
        LayerShell.init_for_window(self.win)
        LayerShell.set_namespace(self.win, "ares-launcher")
        LayerShell.set_layer(self.win, LayerShell.Layer.OVERLAY)
        LayerShell.set_keyboard_mode(self.win, LayerShell.KeyboardMode.EXCLUSIVE)

        root = Gtk.Box(spacing=14)

        # --- painel principal ---
        main = CutPanel(RED)
        main.set_size_request(600, -1)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin_top=16, margin_bottom=14,
                        margin_start=18, margin_end=16, hexpand=True)
        head = Gtk.Box()
        head.add_css_class("head")
        head.append(Gtk.Label(label="▓▒░ ARES // EXECUTE", hexpand=True, xalign=0))
        self.count = Gtk.Label(xalign=1)
        head.append(self.count)
        inner.append(head)

        search = Gtk.Box()
        search.add_css_class("search")
        prompt = Gtk.Label(label=">")
        prompt.add_css_class("prompt")
        self.entry = Gtk.Text(hexpand=True, placeholder_text="buscar daemon_")
        self.entry.connect("changed", lambda *_: (ares_sfx.play("key"), self.refresh()))
        self.entry.connect("activate", lambda *_: self.launch_selected())
        keys = Gtk.EventControllerKey(propagation_phase=Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self.on_key)
        self.win.add_controller(keys)
        search.append(prompt)
        search.append(self.entry)
        inner.append(search)

        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.BROWSE)
        self.list.connect("row-selected", self.on_selected)
        self.list.connect("row-activated", lambda _l, row: self.launch(row.app))
        scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroll.set_size_request(-1, 460)
        scroll.set_child(self.list)
        self.scroll = scroll
        inner.append(scroll)
        self.empty = Gtk.Label(label="> nenhum daemon encontrado_", xalign=0)
        self.empty.add_css_class("empty")
        inner.append(self.empty)

        hint = Gtk.Label(label="↑↓ NAVEGAR · ENTER EXECUTAR · ESC FECHAR", xalign=0)
        hint.add_css_class("hint")
        inner.append(hint)
        main.append(inner)

        # --- painel DAEMON INFO ---
        side = CutPanel(LINE, accent=False)
        side.set_size_request(280, -1)
        sinner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin_top=16, margin_bottom=14,
                         margin_start=18, margin_end=16)
        t = Gtk.Label(label="╔═[ DAEMON INFO ]", xalign=0)
        t.add_css_class("info-title")
        sinner.append(t)
        frame = Gtk.CenterBox(halign=Gtk.Align.START)
        frame.set_size_request(86, 86)
        frame.add_css_class("bigframe")
        self.big_icon = TintedIcon(None, 60, fixed=CYAN)
        frame.set_center_widget(self.big_icon)
        sinner.append(frame)
        self.info_name = Gtk.Label(xalign=0, wrap=True, max_width_chars=22)
        self.info_name.add_css_class("info-name")
        self.info_desc = Gtk.Label(xalign=0, wrap=True, max_width_chars=28, lines=5,
                                   ellipsize=Pango.EllipsizeMode.END)
        self.info_desc.add_css_class("info-desc")
        self.tags = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=4, homogeneous=False,
                                margin_top=12, row_spacing=0, column_spacing=0)
        self.info_cmd = Gtk.Label(xalign=0, wrap=True, max_width_chars=30)
        self.info_cmd.add_css_class("cmd")
        self.info_stat = Gtk.Label(xalign=0)
        self.info_stat.add_css_class("stat")
        for w in (self.info_name, self.info_desc, self.tags, self.info_cmd, self.info_stat):
            sinner.append(w)
        side.append(sinner)

        root.append(main)
        root.append(side)
        self.win.set_child(root)

        self.win.connect("notify::is-active", self.on_active)
        self.refresh()
        self.win.present()
        self.entry.grab_focus()
        ares_sfx.play("open")

    # --- Lista ---------------------------------------------------------------
    def refresh(self):
        query = self.entry.get_text().strip().lower()
        scored = []
        for app in self.apps:
            s = score(app, query)
            if s > 0:
                scored.append((s + 3 * self.counts.get(app.get_id(), 0), app))
        scored.sort(key=lambda x: (-x[0], (x[1].get_name() or "").lower()))
        self.results = [a for _, a in scored[:MAX_RESULTS]]

        while (row := self.list.get_row_at_index(0)) is not None:
            self.list.remove(row)
        for i, app in enumerate(self.results):
            self.list.append(self.build_row(app, i + 1))

        self.count.set_text(f"{len(self.results):02d}/{len(self.apps):02d} APPS")
        self.empty.set_visible(not self.results)
        self.scroll.set_visible(bool(self.results))
        first = self.list.get_row_at_index(0)
        if first:
            self.list.select_row(first)
        else:
            self.show_info(None)

    def build_row(self, app, n):
        row = Gtk.ListBoxRow()
        row.app = app
        box = Gtk.Box()
        frame = Gtk.CenterBox(valign=Gtk.Align.CENTER, halign=Gtk.Align.START)
        frame.set_size_request(36, 36)
        frame.add_css_class("iconframe")
        row.icon = TintedIcon(app.get_icon(), 24)
        frame.set_center_widget(row.icon)
        name = Gtk.Label(label=(app.get_name() or "").upper(), xalign=0, hexpand=True,
                         ellipsize=Pango.EllipsizeMode.END)
        name.add_css_class("name")
        hexid = Gtk.Label(label=f"0x{n:02X}")
        hexid.add_css_class("hex")
        box.append(frame)
        box.append(name)
        box.append(hexid)
        row.set_child(box)
        return row

    def on_selected(self, _list, row):
        # redesenha os ícones da linha antiga e da nova (troca vermelho <-> ciano)
        for r in (getattr(self, "_last_row", None), row):
            if r is not None and hasattr(r, "icon"):
                r.icon.queue_draw()
        self._last_row = row
        self.show_info(row.app if row else None)

    def show_info(self, app):
        if app is None:
            self.big_icon.set_gicon(None)
            for w in (self.info_name, self.info_desc, self.info_cmd, self.info_stat):
                w.set_text("")
            self.info_name.set_text("— SEM ALVO —")
            self.tags.remove_all()
            return
        self.big_icon.set_gicon(app.get_icon())
        self.info_name.set_text((app.get_name() or "").upper())
        self.info_desc.set_text(app.get_description() or app.get_generic_name() or "sem descrição")
        self.tags.remove_all()
        cats = [c for c in (app.get_categories() or "").split(";")
                if c and not c.startswith("X-") and c not in ("GTK", "Qt", "KDE", "GNOME")]
        for c in cats[:6]:
            tag = Gtk.Label(label=c.upper(), halign=Gtk.Align.START)
            tag.add_css_class("tag")
            self.tags.append(tag)
        self.info_cmd.set_text("> " + (app.get_commandline() or app.get_executable() or ""))
        n = self.counts.get(app.get_id(), 0)
        self.info_stat.set_text(f"EXECUÇÕES: {n:03d}")

    # --- Ações ---------------------------------------------------------------
    def on_key(self, _ctrl, keyval, _code, _state):
        if keyval == Gdk.KEY_Escape:
            ares_sfx.play("close")
            self.quit()
            return True
        if keyval in (Gdk.KEY_Down, Gdk.KEY_Up, Gdk.KEY_Page_Down, Gdk.KEY_Page_Up):
            ares_sfx.play("nav")
            row = self.list.get_selected_row()
            i = row.get_index() if row else 0
            step = {Gdk.KEY_Down: 1, Gdk.KEY_Up: -1, Gdk.KEY_Page_Down: 8, Gdk.KEY_Page_Up: -8}[keyval]
            i = max(0, min(len(self.results) - 1, i + step))
            target = self.list.get_row_at_index(i)
            if target:
                self.list.select_row(target)
                target.grab_focus()
                self.entry.grab_focus_without_selecting()
            return True
        return False

    def launch_selected(self):
        row = self.list.get_selected_row()
        if row:
            self.launch(row.app)

    def launch(self, app):
        ares_sfx.play("select")
        self.counts[app.get_id()] = self.counts.get(app.get_id(), 0) + 1
        save_counts(self.counts)
        ctx = Gdk.Display.get_default().get_app_launch_context()
        self.win.set_visible(False)
        try:
            app.launch([], ctx)
        except GLib.Error as e:
            print("falha ao abrir:", e.message)
        self.quit()

    def on_active(self, win, _pspec):
        # clicou fora / outra janela pegou o foco: fecha
        if not win.is_active() and getattr(self, "_was_active", False):
            ares_sfx.play("close")
            self.quit()
        self._was_active = win.is_active() or getattr(self, "_was_active", False)


if __name__ == "__main__":
    Launcher().run(None)
