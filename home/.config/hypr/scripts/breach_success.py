#!/usr/bin/env python3
# ARES // BREACH SUCCESSFUL
# Animação de desbloqueio que continua a partir da tela de bloqueio: reproduz o HUD
# do hyprlock.conf nas mesmas posições (moldura, cabeçalho, painéis, relógio, buffer,
# rodapé) e então anima no lugar:
#   1. a CODE MATRIX é resolvida e o BUFFER enche com os códigos escolhidos
#   2. os daemons da SEQUENCE vão sendo marcados como INSTALLED
#   3. o centro troca o relógio por BREACH SUCCESSFUL + barra de upload
#   4. fade out
#
# Uso: breach_success.py         -> toca a animação agora
#      breach_success.py --wait  -> abre invisível atrás do hyprlock e só começa ao
#                                   receber SIGUSR1 (é o que o lock.sh faz)
# Se mudar posições no hyprlock.conf, ajuste a tabela de layout em build_hud().
# Deps: python-gobject gtk4 gtk4-layer-shell

import datetime
import importlib.util
import os
import random
import signal
import subprocess
import sys
from ctypes import CDLL

CDLL("libgtk4-layer-shell.so")  # precisa carregar antes do GTK

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402
from gi.repository import Gtk4LayerShell as LayerShell  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("breach_matrix", os.path.join(HERE, "breach_matrix.py"))
matrix = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(matrix)
matrix.SCAN_RANGE = (1, 2)  # cursor anda pouco antes de cada escolha = mais rápido

WALLPAPER = os.path.expanduser("~/.config/hypr/wallpaper.png")

TITLE = "BREACH SUCCESSFUL"
INFO = "DAEMONS UPLOADED: DATAMINE_V1 · SESSION_UNLOCK · ROOT_ACCESS"
FOOTER = "> ACCESS GRANTED // WELCOME BACK, {user}_"
GLITCH = "▓▒░█#@$%&01ABCDEF"

# (código, nome, descrição) — igual ao breach_sequence.sh
DAEMONS = [
    ("55 1C   ", "DATAMINE_V1", "extrai dados da sessão"),
    ("1C 1C E9", "SESSION_UNLOCK", "libera o desktop"),
    ("BD E9 55", "ROOT_ACCESS", "acesso total ao ARES"),
]

TICK_MS = 30
MATRIX_STEP_MS = 60   # um passo da matriz a cada 60 ms
MATRIX_HOLD_MS = 250  # pausa com "UPLOAD OK" antes do título
GLITCH_MS = 350
BAR_MS = 600
HOLD_MS = 1000        # tempo do BREACH SUCCESSFUL na tela antes de sumir
FADE_MS = 300

RED, CYAN, TEXT, MUTED, DARK = "#ff1f3d", "#00f0ff", "#e8e2e4", "#7a6f73", "#08060a"

CSS = f"""
window.breach {{ background-color: {DARK}; border: none; box-shadow: none; }}
.breach * {{ font-family: "3270 Nerd Font", "JetBrainsMono Nerd Font", monospace; }}
.bg {{ filter: blur(14px) brightness(18%); }}
.outer {{ border: 1px solid rgba(255, 31, 61, 0.35); }}
.redbar {{ background-color: {RED}; }}
.panel {{ background-color: rgba(16, 10, 14, 0.85); border: 1px solid {RED}; }}
.outline {{ border: 1px solid {RED}; }}
.outline.ok {{ border-color: {CYAN}; }}
.l-red {{ color: {RED}; }}
.l-cyan {{ color: {CYAN}; }}
.l-text {{ color: {TEXT}; }}
.l-muted {{ color: {MUTED}; }}
.l-dark {{ color: {DARK}; }}
.s12 {{ font-size: 12pt; }} .s13 {{ font-size: 13pt; }} .s16 {{ font-size: 16pt; }}
.s18 {{ font-size: 18pt; }} .s20 {{ font-size: 20pt; }} .s22 {{ font-size: 22pt; }}
.s120 {{ font-size: 120pt; }}
.title {{ color: {CYAN}; font-size: 54pt; letter-spacing: 8px; }}
.title.glitch {{ color: {RED}; }}
.info {{ color: {TEXT}; font-size: 15pt; margin: 6px 0 16px 0; }}
.barframe {{ border: 1px solid {CYAN}; padding: 3px; }}
.bar {{ background-color: {CYAN}; min-height: 10px; }}
.footer {{ color: {RED}; font-size: 14pt; margin-top: 12px; }}
"""

BAR_WIDTH = 1100


def label(text="", *classes, markup=False):
    w = Gtk.Label()
    if markup:
        w.set_markup(text)
    else:
        w.set_text(text)
    for c in classes:
        w.add_css_class(c)
    return w


def shape(width, height, *classes):
    w = Gtk.Box()
    w.set_size_request(width, height)
    for c in classes:
        w.add_css_class(c)
    return w


def sequence_markup(installed):
    lines = []
    for i, (code, name, desc) in enumerate(DAEMONS):
        if i < installed:
            lines.append(f"<span foreground='{MUTED}'>{code}  </span>  <span foreground='{CYAN}'>{name}</span>")
            lines.append(f"<span foreground='{CYAN}'>           ✔ INSTALLED</span>")
        else:
            lines.append(f"<span foreground='{RED}'>{code}  </span>  <span foreground='{CYAN}'>{name}</span>")
            lines.append(f"<span foreground='{MUTED}'>           {desc}</span>")
    return "<span line_height='1.6'>" + "\n".join(lines) + "</span>"


class Breach(Gtk.Application):
    def __init__(self, wait):
        super().__init__(application_id="ares.breach.success")
        self.wait = wait
        self.started = False
        self.state = None
        self.matrix_acc = 0
        self.matrix_done_at = None
        self.t = 0
        self.items = []  # (widget, x, y, halign, valign) no sistema de coordenadas do hyprlock

    # --- Layout no estilo hyprlock -------------------------------------------
    def place(self, widget, x, y, halign="center", valign="center"):
        self.fixed.put(widget, 0, 0)
        self.items.append((widget, x, y, halign, valign))
        return widget

    def relayout(self):
        W, H = self.W, self.H
        for w, x, y, ha, va in self.items:
            ww = w.measure(Gtk.Orientation.HORIZONTAL, -1)[1]
            hh = w.measure(Gtk.Orientation.VERTICAL, -1)[1]
            left = {"left": x, "right": W + x - ww}.get(ha, W / 2 + x - ww / 2)
            top = {"top": -y, "bottom": H - y - hh}.get(va, H / 2 - y - hh / 2)
            self.fixed.move(w, left, top)
        return False

    def build_hud(self):
        user = GLib.get_user_name()
        now = datetime.datetime.now().strftime("%H:%M")
        try:
            date = subprocess.run([os.path.join(HERE, "lock_date.sh")], capture_output=True, text=True).stdout.strip()
        except OSError:
            date = ""

        p = self.place
        p(shape(4960, 1200, "outer"), 0, -30)
        # cabeçalho
        p(label("ARES ▓▒░ NETTECH", "l-red", "s18"), 90, -38, "left", "top")
        p(shape(1600, 26, "redbar"), 0, -40, "center", "top")
        self.header = p(label("BREACH PROTOCOL INTERFACE", "l-dark", "s12"), 0, -43, "center", "top")
        p(label("DAEMON 4F2A-ARES-0X1F", "l-muted", "s12"), -90, -42, "right", "top")
        # painel esquerdo
        p(label("BREACH TIME REMAINING", "l-red", "s18"), -1610, 250)
        p(shape(150, 44, "outline"), -1290, 250)
        p(label(now, "l-cyan", "s20"), -1290, 250)
        p(shape(640, 5, "redbar"), -1500, 208)
        p(shape(640, 460, "panel"), -1500, -40)
        p(shape(640, 38, "redbar"), -1500, 171)
        p(label("▦  CODE MATRIX", "l-dark", "s16"), -1500, 171)
        self.matrix_label = p(label(matrix.render(self.state), "l-red", "s22", markup=True), -1500, -60)
        # centro
        self.clock = p(label(now, "l-cyan", "s120"), 0, 170)
        self.date = p(label(date, "l-text", "s18"), 0, 60)
        self.buffer_title = p(label("BUFFER", "l-red", "s16"), 0, -10)
        self.buffer_box = p(shape(560, 58, "panel", "outline", "ok"), 0, -70)
        self.buffer = p(label("▪ ▪ ▪ ▪ ▪ ▪ ▪ ▪", "l-cyan", "s20"), 0, -70)
        self.hint = p(label("> senha aceita // executando daemons_", "l-cyan", "s13"), 0, -130)
        # painel direito
        p(shape(760, 460, "panel"), 1500, -40)
        p(shape(760, 38, "redbar"), 1500, 171)
        p(label("SEQUENCE REQUIRED TO UPLOAD", "l-dark", "s16"), 1500, 171)
        self.sequence = p(label(sequence_markup(0), "l-text", "s18", markup=True), 1500, -60)
        self.sequence.set_xalign(0)
        # rodapé
        p(label(f"USER // {user}@{GLib.get_host_name()}", "l-muted", "s12"), 110, 110, "left", "bottom")
        p(label("[ENTER] UPLOAD    [ESC] LIMPAR", "l-red", "s12"), -110, 110, "right", "bottom")

        # BREACH SUCCESSFUL (no lugar do relógio, aparece depois da matriz)
        self.success = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.success.set_size_request(BAR_WIDTH + 8, -1)
        self.success.set_opacity(0)
        self.title = label(TITLE, "title")
        info = label(INFO, "info")
        frame = Gtk.Box()
        frame.add_css_class("barframe")
        self.bar = Gtk.Box(halign=Gtk.Align.START)
        self.bar.add_css_class("bar")
        self.bar.set_size_request(0, -1)
        frame.append(self.bar)
        self.footer = label("", "footer")
        self.footer.set_xalign(0)
        self.footer_text = FOOTER.format(user=user.upper())
        for w in (self.title, info, frame, self.footer):
            self.success.append(w)
        p(self.success, 0, 150)

    # --- App -----------------------------------------------------------------
    def do_activate(self):
        provider = Gtk.CssProvider()
        provider.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

        geo = Gdk.Display.get_default().get_monitors().get_item(0).get_geometry()
        self.W, self.H = geo.width, geo.height
        self.state = matrix.load()

        self.win = Gtk.ApplicationWindow(application=self)
        self.win.add_css_class("breach")
        LayerShell.init_for_window(self.win)
        LayerShell.set_namespace(self.win, "ares-breach")
        LayerShell.set_layer(self.win, LayerShell.Layer.OVERLAY)
        for edge in (LayerShell.Edge.TOP, LayerShell.Edge.BOTTOM, LayerShell.Edge.LEFT, LayerShell.Edge.RIGHT):
            LayerShell.set_anchor(self.win, edge, True)
        LayerShell.set_exclusive_zone(self.win, -1)
        LayerShell.set_keyboard_mode(self.win, LayerShell.KeyboardMode.NONE)

        overlay = Gtk.Overlay()
        bg = Gtk.Picture.new_for_file(Gio.File.new_for_path(WALLPAPER))
        bg.set_content_fit(Gtk.ContentFit.COVER)
        bg.add_css_class("bg")
        overlay.set_child(bg)
        self.fixed = Gtk.Fixed()
        overlay.add_overlay(self.fixed)
        self.root = overlay
        self.win.set_child(overlay)

        self.build_hud()

        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, self.start)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, self.stop)

        self.win.present()
        GLib.idle_add(self.relayout)
        if self.wait:
            self.root.set_opacity(0)  # só o preto, escondido atrás do hyprlock
        else:
            GLib.idle_add(self.start)

    def stop(self):
        self.quit()
        return False

    def start(self):
        if self.started:
            return False
        self.started = True
        # a matriz pode ter sido regerada pelo hyprlock depois que abrimos
        self.state = matrix.load()
        self.matrix_label.set_markup(matrix.render(self.state))
        self.relayout()
        self.root.set_opacity(1)
        GLib.timeout_add(TICK_MS, self.tick)
        return False

    # --- Animação ------------------------------------------------------------
    def tick(self):
        self.t += TICK_MS

        # 1) matriz resolvendo + buffer + daemons
        if self.matrix_done_at is None:
            self.matrix_acc += TICK_MS
            while self.matrix_acc >= MATRIX_STEP_MS and self.state["phase"] != "done":
                self.matrix_acc -= MATRIX_STEP_MS
                self.state = matrix.step(self.state)
            self.matrix_label.set_markup(matrix.render(self.state))
            picked = self.state["buffer"]
            slots = picked + ["__"] * (matrix.PICKS - len(picked))
            self.buffer.set_text(" ".join(slots))
            self.sequence.set_markup(sequence_markup(len(picked) // 2))
            if self.state["phase"] == "done":
                self.matrix_done_at = self.t
                self.hint.set_text("> upload concluído // 3/3 daemons instalados_")
                self.header.set_text("BREACH PROTOCOL // UPLOAD COMPLETE")
            self.relayout()
            return True

        t = self.t - self.matrix_done_at - MATRIX_HOLD_MS
        if t < 0:
            return True

        # 2) BREACH SUCCESSFUL no lugar do relógio
        if self.clock.get_opacity() > 0:
            for w in (self.clock, self.date):
                w.set_opacity(0)
            self.success.set_opacity(1)
            self.relayout()
        if t < GLITCH_MS:
            self.title.set_text("".join(
                random.choice(GLITCH) if ch != " " and random.random() < 0.45 else ch for ch in TITLE
            ))
            if random.random() < 0.5:
                self.title.add_css_class("glitch")
            else:
                self.title.remove_css_class("glitch")
        else:
            self.title.set_text(TITLE)
            self.title.remove_css_class("glitch")

        progress = min(t / BAR_MS, 1.0)
        self.bar.set_size_request(int(BAR_WIDTH * progress), -1)
        self.footer.set_text(self.footer_text[: int(len(self.footer_text) * progress)])

        # 3) fade out
        if t > HOLD_MS:
            self.win.set_opacity(max(0.0, 1 - (t - HOLD_MS) / FADE_MS))
        if t >= HOLD_MS + FADE_MS:
            self.quit()
            return False
        return True


if __name__ == "__main__":
    Breach(wait="--wait" in sys.argv).run(None)
