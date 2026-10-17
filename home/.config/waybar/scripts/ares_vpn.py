#!/usr/bin/env python3
# ARES // VPN (FortiClient)
# Gaveta layer-shell abaixo da barra para conectar/desconectar a VPN do FortiClient.
# Usa o CLI (`forticlient vpn ...`): a GUI oficial do Linux (7.4.3) não mostra o campo do FortiToken.
# O CLI só lê senha/token de um TTY, então o `connect` roda dentro de um PTY aqui.
# Nada é gravado em disco: a senha vive só na memória até ser enviada ao CLI.
# Uso: ares_vpn.py            -> abre/fecha a gaveta (rodar de novo fecha)
#      ares_vpn.py --waybar   -> JSON para o módulo custom/vpn
# Teclado: ENTER envia, ESC cancela a tentativa em curso ou fecha a gaveta.
# Deps: python-gobject gtk4 gtk4-layer-shell, forticlient-vpn (AUR), util-linux (setsid)
# Teste: ARES_VPN_CLI=/caminho/mock troca o executável `forticlient` por outro.

import json
import os
import re
import signal
import subprocess
import sys
import termios
import threading

CLI = os.environ.get("ARES_VPN_CLI", "forticlient")
ICON = "\U000F0582"  # nf-md-vpn
GAP = "  "  # o glifo é mais largo que a célula e vaza sobre o texto: um espaço só não basta
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
PASSWORD_PROMPT = re.compile(r"^\s*password\s*:$", re.I)
SECRET_HINT = re.compile(r"pass|senha|pin|secret", re.I)  # o resto (FortiToken, código) aparece em claro
SEPARATOR = re.compile(r"^[=\-]{3,}$")
NOISE = re.compile(r"^(connect vpn:|status:|authentication required|done\.?$)", re.I)  # andamento, não é erro
ERROR_HINT = re.compile(r"error|fail|invalid|wrong|already|not found|denied|esgotado|timeout", re.I)
CONNECT_TIMEOUT = 120  # segundos no total, incluindo a espera do token
TOKEN_WINDOW = 30      # o serviço desiste do token em ~30s (só para a barrinha de contagem)
LOG_COLS = 38          # largura (em caracteres) do log e das mensagens de erro na gaveta
PROMPT_COLS = 34       # idem para a mensagem do servidor no pedido de token (fonte maior)


# ---------------------------------------------------------------- CLI

def cli(*args, timeout=8):
    """Roda `forticlient vpn <args>` sem TTY. Devolve (código, saída)."""
    try:
        r = subprocess.run([CLI, "vpn", *args], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)
    return r.returncode, ANSI.sub("", r.stdout + r.stderr)


def parse_status(text):
    """`Status: Connected` + linhas `  chave: valor` -> dict. state: on | busy | off."""
    info = {"state": "off", "raw": ""}
    keys = {"vpn name": "name", "username": "user", "ip": "ip", "duration": "duration"}
    for line in text.splitlines():
        if ":" not in line:
            continue
        k, v = (s.strip() for s in line.split(":", 1))
        k = k.lower()
        if k == "status":
            info["raw"] = v
            low = v.lower()
            if low.startswith("connected"):
                info["state"] = "on"
            elif low.startswith(("connecting", "disconnecting")):
                info["state"] = "busy"
        elif k in keys:
            info[keys[k]] = v
        elif k in ("sent bytes", "recv bytes") and v.isdigit():
            info["sent" if k == "sent bytes" else "recv"] = int(v)
    return info


def fmt_bytes(n):
    n = float(n)
    for unit in ("B", "KB", "MB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.2f} GB"


def error_text(lines):
    """Do log do CLI, só o que explica a falha: as linhas de erro ou, sem elas, as 2 últimas úteis."""
    useful = [ln for ln in lines if not SEPARATOR.match(ln) and not NOISE.match(ln)]
    return "\n".join(([ln for ln in useful if ERROR_HINT.search(ln)] or useful)[-2:])


def list_profiles():
    """Nomes dos perfis: linhas com 4 espaços de recuo em `vpn list`."""
    _rc, out = cli("list")
    return [ln.strip() for ln in out.splitlines()
            if ln.startswith("    ") and ln.strip() and not ln.strip().endswith(":")]


def profile_user(name):
    _rc, out = cli("view", name)
    for ln in out.splitlines():
        if ln.strip().lower().startswith("username:"):
            return ln.split(":", 1)[1].strip()
    return ""


def waybar():
    rc, out = cli("status", timeout=4)
    info = parse_status(out) if rc == 0 else {"state": "off"}
    state = info["state"]
    if state == "on":
        text = f"{ICON}{GAP}<span color='#00f0ff'>{info.get('ip', 'ON')}</span>"
        tip = [f"VPN {info.get('name', '?')} conectada", f"Usuário  {info.get('user', '?')}",
               f"IP       {info.get('ip', '?')}", f"Tempo    {info.get('duration', '?')}",
               f"↑ {fmt_bytes(info.get('sent', 0))}   ↓ {fmt_bytes(info.get('recv', 0))}"]
    elif state == "busy":
        text = f"{ICON}{GAP}<span color='#ffb000'>...</span>"
        tip = [info.get("raw") or "Conectando..."]
    else:
        text = f"{ICON}{GAP}<span color='#4a3a40'>OFF</span>"
        tip = ["VPN desconectada", "Clique para conectar"]
        if rc != 0:
            tip = ["forticlient indisponível", out.strip()[:120]]
    print(json.dumps({"text": text, "class": state, "tooltip": "\n".join(tip)}))


if __name__ == "__main__" and "--waybar" in sys.argv:
    waybar()
    sys.exit(0)

# ---------------------------------------------------------------- GUI

from ctypes import CDLL  # noqa: E402

CDLL("libgtk4-layer-shell.so")  # precisa carregar antes do GTK

sys.path.insert(0, os.path.expanduser("~/.config/hypr/scripts"))
try:
    import ares_sfx  # noqa: E402
except ImportError:  # sem o pacote de sons a gaveta funciona igual, só calada
    class ares_sfx:  # noqa: N801
        play = staticmethod(lambda *_a, **_k: None)

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gdk, GLib, Gtk, Pango  # noqa: E402
from gi.repository import Gtk4LayerShell as LayerShell  # noqa: E402

CSS = """
window.vpn { background-color: transparent; border: none; box-shadow: none; }
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
.state { font-size: 18px; margin: 8px 2px 6px 2px; }
.state-on { color: #00f0ff; }
.state-off { color: #8a7a80; }
.state-busy { color: #ffb000; }
.field { color: #4a3a40; font-size: 12px; margin: 8px 2px 2px 2px; }
.msg { color: #e8e2e4; margin: 4px 2px; }
.log { color: #4a3a40; font-size: 13px; margin: 4px 2px 8px 2px; }
.err { color: #ff1f3d; font-size: 13px; margin: 8px 2px 0 2px; }
.key { color: #4a3a40; font-size: 13px; }
.val { color: #e8e2e4; font-size: 14px; }
.val.accent { color: #00f0ff; }
entry, passwordentry {
    background: #160d12;
    background-image: none;
    border: 1px solid #3a1018;
    border-radius: 0;
    box-shadow: none;
    color: #e8e2e4;
    caret-color: #00f0ff;
    padding: 4px 8px;
    min-height: 0;
    outline: none;
}
entry:focus-within, passwordentry:focus-within { border-color: #ff1f3d; }
entry text, passwordentry text { color: #e8e2e4; }
dropdown > button {
    background: #160d12; background-image: none; border: 1px solid #3a1018; border-radius: 0;
    box-shadow: none; color: #e8e2e4; padding: 4px 8px;
}
dropdown > button:hover { border-color: #ff1f3d; }
progressbar.countdown trough { background: #160d12; min-height: 3px; border-radius: 0; border: none; }
progressbar.countdown progress { background: #ffb000; min-height: 3px; border-radius: 0; }
progressbar.countdown.low progress { background: #ff1f3d; }
button.item {
    background: #160d12;
    background-image: none;
    border: 1px solid #3a1018;
    border-radius: 0;
    box-shadow: none;
    color: #e8e2e4;
    padding: 6px 12px;
    margin-top: 8px;
}
button.item:hover, button.item:focus {
    border-color: #ff1f3d;
    background: #2a0a12;
    outline: none;
}
button.item.primary { border-color: #00f0ff; color: #00f0ff; }
button.item.primary:hover, button.item.primary:focus { background: #00f0ff; color: #08060a; border-color: #00f0ff; }
button.item.danger { color: #ff1f3d; }
.hint { color: #4a3a40; font-size: 12px; margin-top: 10px; }
"""


class Connector:
    """`forticlient vpn connect` dentro de um PTY.

    A primeira pergunta de senha é respondida sozinha com a senha que a UI já tem; qualquer outra
    pergunta (FortiToken, nova senha...) sobe para a UI via on_prompt. Uma pergunta é uma linha parcial
    terminada em ':' que ficou parada na tela por um instante (o CLI não imprime newline depois dela).
    """

    IDLE_MS = 300

    def __init__(self, on_line, on_prompt, on_done):
        self.on_line, self.on_prompt, self.on_done = on_line, on_prompt, on_done
        self.proc = None
        self.master = None
        self.password = None
        self.buf = ""
        self.lines = []
        self.finished = True
        self._src = {}

    @property
    def active(self):
        return not self.finished

    # -- ciclo de vida
    def start(self, profile, user, password):
        self.password, self.buf, self.lines, self.finished = password, "", [], False
        master, slave = os.openpty()
        attrs = termios.tcgetattr(slave)
        attrs[3] &= ~termios.ECHO  # segredo nunca volta pelo eco do TTY
        termios.tcsetattr(slave, termios.TCSANOW, attrs)
        try:
            self.proc = subprocess.Popen(
                ["setsid", "-c", CLI, "vpn", "connect", profile, "-u", user, "-p"],
                stdin=slave, stdout=slave, stderr=slave, close_fds=True)
        except OSError as e:
            os.close(master)
            os.close(slave)
            self.lines = [str(e)]
            self._finish(-1)
            return
        os.close(slave)
        self.master = master
        os.set_blocking(master, False)
        self._src["io"] = GLib.io_add_watch(master, GLib.PRIORITY_DEFAULT, GLib.IO_IN | GLib.IO_HUP, self._on_io)
        self._src["poll"] = GLib.timeout_add(250, self._poll_exit)
        self._src["limit"] = GLib.timeout_add_seconds(CONNECT_TIMEOUT, self._on_timeout)

    def answer(self, text):
        if self.master is not None and not self.finished:
            os.write(self.master, (text + "\n").encode())

    def cancel(self):
        if self.finished:
            return
        self._kill()
        self._finish(None)

    # -- internos
    def _kill(self):
        proc = self.proc
        if proc is None or proc.poll() is not None:
            return
        try:
            os.killpg(proc.pid, signal.SIGTERM)  # setsid -c fez dele líder de sessão/grupo
        except OSError:
            proc.terminate()

        def reap():
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        threading.Thread(target=reap, daemon=True).start()

    def _finish(self, rc):
        if self.finished:
            return
        self.finished = True
        self.password = None
        for src in self._src.values():
            GLib.source_remove(src)
        self._src = {}
        if self.master is not None:
            try:
                os.close(self.master)
            except OSError:
                pass
            self.master = None
        self.on_done(rc, list(self.lines))

    def _on_timeout(self):
        self._src.pop("limit", None)
        self.lines.append("Tempo esgotado: o CLI não respondeu.")
        self._kill()
        self._finish(-1)
        return False

    def _read_all(self):
        """Lê tudo o que está pendente. Devolve False no EOF."""
        while self.master is not None:
            try:
                data = os.read(self.master, 4096)
            except BlockingIOError:
                return True
            except OSError:  # EIO: o outro lado do PTY fechou
                return False
            if not data:
                return False
            self._feed(data.decode("utf-8", "replace"))
        return False

    def _on_io(self, _fd, _cond):
        if self._read_all():
            return True
        self._src.pop("io", None)  # EOF; o _poll_exit fecha quando o processo sair
        return False

    def _poll_exit(self):
        rc = self.proc.poll()
        if rc is None:
            return True
        self._src.pop("poll", None)
        self._read_all()  # esvazia o que sobrou antes de fechar
        self._finish(rc)
        return False

    def _feed(self, text):
        text = ANSI.sub("", text).replace("\r\n", "\n").replace("\r", "")
        *done, self.buf = (self.buf + text).split("\n")
        for ln in done:
            ln = ln.strip()
            if ln:
                self.lines.append(ln)
                self.on_line(ln)
        if "idle" in self._src:
            GLib.source_remove(self._src.pop("idle"))
        if self.buf.strip():
            self._src["idle"] = GLib.timeout_add(self.IDLE_MS, self._check_prompt)

    def _check_prompt(self):
        self._src.pop("idle", None)
        label = self.buf.strip()
        if self.finished or not label.endswith(":"):
            return False
        self.buf = ""
        if self.password is not None and PASSWORD_PROMPT.match(label):
            self.answer(self.password)
            self.password = None
            return False
        context = [ln for ln in self.lines if not SEPARATOR.match(ln) and not ln.lower().startswith(("status:", "connect vpn"))]
        self.on_prompt(label, context[-2:], bool(SECRET_HINT.search(label)))
        return False


class VpnPanel(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="ares.vpn.panel")
        self.win = None
        self.info = {"state": "off"}
        self.gen = 0            # descarta respostas de status que chegam atrasadas
        self.busy_op = False    # desconectando
        self.cancelling = False
        self.countdown_src = None
        self.connector = Connector(self.on_line, self.on_prompt, self.on_done)

    # ---------------------------------------------------------- construção
    def do_activate(self):
        if self.win is not None:  # segunda execução = fechar
            ares_sfx.play("close")
            self.quit()
            return

        provider = Gtk.CssProvider()
        provider.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

        self.win = Gtk.ApplicationWindow(application=self)
        self.win.add_css_class("vpn")
        self.win.set_resizable(False)  # sem isso a janela cresce com um texto longo e nunca volta a encolher
        LayerShell.init_for_window(self.win)
        LayerShell.set_namespace(self.win, "ares-vpn")
        LayerShell.set_layer(self.win, LayerShell.Layer.TOP)
        LayerShell.set_anchor(self.win, LayerShell.Edge.TOP, True)
        LayerShell.set_anchor(self.win, LayerShell.Edge.RIGHT, True)
        LayerShell.set_margin(self.win, LayerShell.Edge.TOP, 6)
        LayerShell.set_margin(self.win, LayerShell.Edge.RIGHT, 12)
        LayerShell.set_keyboard_mode(self.win, LayerShell.KeyboardMode.ON_DEMAND)

        keys = Gtk.EventControllerKey()
        keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self.on_key)
        self.win.add_controller(keys)

        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        panel.add_css_class("panel")
        panel.set_size_request(330, -1)

        title = Gtk.Label(label="▓▒░ ARES // VPN ░▒▓", xalign=0)
        title.add_css_class("title")
        self.state_lbl = Gtk.Label(label="", xalign=0)
        self.state_lbl.add_css_class("state")
        panel.append(title)
        panel.append(self.state_lbl)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.NONE, vhomogeneous=True)
        self.stack.add_named(self.build_off(), "off")
        self.stack.add_named(self.build_busy(), "busy")
        self.stack.add_named(self.build_prompt(), "prompt")
        self.stack.add_named(self.build_on(), "on")
        self.stack.connect("notify::visible-child-name", self.on_page)
        panel.append(self.stack)

        self.hint = Gtk.Label(label="", xalign=0)
        self.hint.add_css_class("hint")
        panel.append(self.hint)

        self.win.set_child(panel)
        self.win.present()
        ares_sfx.play("open")

        self.set_state("off")
        self.on_page()  # a página inicial ("off") não dispara notify: aplica foco e dica na mão
        self.load_profiles()
        self.refresh()
        GLib.timeout_add_seconds(2, self.refresh)

    def label(self, text, css, **kw):
        lbl = Gtk.Label(label=text, xalign=0, **kw)
        lbl.add_css_class(css)
        return lbl

    def wrapped(self, css, cols):
        """Rótulo com quebra e largura FIXA em caracteres. Só com max_width_chars o GTK renegocia a largura a cada
        texto novo e a gaveta alargava (e não encolhia mais) ao mostrar a mensagem longa do servidor."""
        lbl = self.label("", css, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR, width_chars=cols, max_width_chars=cols)
        return lbl

    def button(self, text, handler, *css):
        btn = Gtk.Button(label=text)
        btn.add_css_class("item")
        for c in css:
            btn.add_css_class(c)
        btn.connect("clicked", handler)
        return btn

    def build_off(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(self.label("PERFIL", "field"))
        self.profile_box = Gtk.Box()  # recebe um label ou um dropdown em load_profiles()
        box.append(self.profile_box)
        box.append(self.label("USUÁRIO", "field"))
        self.user = Gtk.Entry(placeholder_text="usuário")
        self.user.connect("activate", lambda *_: self.password.grab_focus())
        box.append(self.user)
        box.append(self.label("SENHA", "field"))
        self.password = Gtk.PasswordEntry(show_peek_icon=True, placeholder_text="senha")
        self.password.connect("activate", self.on_connect)
        box.append(self.password)
        self.err = self.wrapped("err", LOG_COLS)
        self.err.set_visible(False)
        box.append(self.err)
        box.append(self.button("CONECTAR", self.on_connect, "primary"))
        return box

    def build_busy(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.busy_title = self.label("CONECTANDO...", "msg")
        self.busy_log = self.wrapped("log", LOG_COLS)
        self.cancel_btn = self.button("CANCELAR", self.on_cancel, "danger")
        box.append(self.busy_title)
        box.append(self.busy_log)
        box.append(self.cancel_btn)
        return box

    def build_prompt(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.prompt_msg = self.wrapped("msg", PROMPT_COLS)
        self.prompt_field = self.label("", "field")
        self.prompt_entry = Gtk.Entry()
        self.prompt_entry.connect("activate", self.on_prompt_submit)
        self.countdown = Gtk.ProgressBar()
        self.countdown.add_css_class("countdown")
        self.countdown.set_margin_top(8)
        box.append(self.prompt_msg)
        box.append(self.prompt_field)
        box.append(self.prompt_entry)
        box.append(self.countdown)
        box.append(self.button("ENVIAR", self.on_prompt_submit, "primary"))
        box.append(self.button("CANCELAR", self.on_cancel, "danger"))
        return box

    def build_on(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        grid = Gtk.Grid(column_spacing=14, row_spacing=3)
        self.on_vals = {}
        for i, (key, label, accent) in enumerate([("name", "PERFIL", False), ("user", "USUÁRIO", False),
                                                  ("ip", "IP", True), ("duration", "TEMPO", False),
                                                  ("sent", "↑ ENVIADO", False), ("recv", "↓ RECEBIDO", False)]):
            grid.attach(self.label(label, "key"), 0, i, 1, 1)
            val = self.label("-", "val", hexpand=True)
            if accent:
                val.add_css_class("accent")
            grid.attach(val, 1, i, 1, 1)
            self.on_vals[key] = val
        box.append(grid)
        box.append(self.button("DESCONECTAR", self.on_disconnect, "danger"))
        return box

    # ---------------------------------------------------------- páginas e estado
    def show(self, page):
        self.stack.set_visible_child_name(page)

    def on_page(self, *_):
        page = self.stack.get_visible_child_name()
        # EXCLUSIVE só enquanto há campo para digitar: o foco chega sem precisar clicar
        typing = page in ("off", "prompt")
        LayerShell.set_keyboard_mode(
            self.win, LayerShell.KeyboardMode.EXCLUSIVE if typing else LayerShell.KeyboardMode.ON_DEMAND)
        self.hint.set_text({"off": "ENTER conectar · ESC fechar", "prompt": "ENTER enviar · ESC cancelar",
                            "busy": "ESC cancelar", "on": "ESC fechar"}.get(page, ""))
        if page == "off":
            self.focus_later(self.password if self.user.get_text() else self.user)
        elif page == "prompt":
            self.focus_later(self.prompt_entry)

    @staticmethod
    def focus_later(widget):
        GLib.idle_add(lambda: bool(widget.grab_focus()) and False)

    def set_state(self, state):
        for c in ("state-on", "state-off", "state-busy"):
            self.state_lbl.remove_css_class(c)
        self.state_lbl.add_css_class(f"state-{state}")
        self.state_lbl.set_text({"on": "● CONECTADO", "busy": "◌ CONECTANDO", "off": "○ DESCONECTADO"}[state])

    def load_profiles(self):
        self.profiles = list_profiles()
        for child in list(iter_children(self.profile_box)):
            self.profile_box.remove(child)
        if len(self.profiles) > 1:
            self.dropdown = Gtk.DropDown.new_from_strings(self.profiles)
            self.dropdown.set_hexpand(True)
            self.dropdown.connect("notify::selected", lambda *_: self.fill_user())
            self.profile_box.append(self.dropdown)
        else:
            self.dropdown = None
            lbl = self.label(self.profiles[0] if self.profiles else "nenhum perfil (forticlient vpn edit)", "val", hexpand=True)
            self.profile_box.append(lbl)
        self.fill_user()

    def selected_profile(self):
        if self.dropdown is not None:
            return self.profiles[self.dropdown.get_selected()]
        return self.profiles[0] if self.profiles else ""

    def fill_user(self):
        name = self.selected_profile()
        if name:
            threading.Thread(target=lambda: GLib.idle_add(self.set_user, profile_user(name)), daemon=True).start()

    def set_user(self, user):
        if user and not self.user.get_text():
            self.user.set_text(user)
        self.on_page()  # reavalia o foco: com o usuário preenchido o cursor vai para a senha

    # ---------------------------------------------------------- status
    def busy(self):
        return self.connector.active or self.busy_op

    def refresh(self, *_):
        if self.win is None:
            return False
        if not self.busy():
            self.gen += 1
            gen = self.gen

            def work():
                rc, out = cli("status", timeout=5)
                GLib.idle_add(self.apply_status, parse_status(out) if rc == 0 else {"state": "off"}, gen)
            threading.Thread(target=work, daemon=True).start()
        return True

    def apply_status(self, info, gen):
        if gen != self.gen or self.busy() or self.win is None:
            return
        self.info = info
        state = info["state"]
        self.set_state(state)
        if state == "on":
            for key, val in self.on_vals.items():
                v = info.get(key)
                val.set_text(fmt_bytes(v) if key in ("sent", "recv") and v is not None else (v or "-"))
            self.show("on")
        elif state == "busy":
            self.busy_title.set_text("CONECTANDO...")
            self.busy_log.set_text(info.get("raw", ""))
            self.cancel_btn.set_visible(False)  # não é uma tentativa nossa: sem processo para cancelar
            self.show("busy")
        elif self.stack.get_visible_child_name() != "off":  # inclui um "prompt" que ficou para trás
            self.show("off")

    # ---------------------------------------------------------- conectar
    def on_connect(self, *_):
        profile = self.selected_profile()
        user, pw = self.user.get_text().strip(), self.password.get_text()
        if not profile:
            return self.fail("Nenhum perfil configurado. Crie um com: forticlient vpn edit")
        if not user or not pw:
            return self.fail("Informe usuário e senha.")
        if self.connector.active:
            return
        self.password.set_text("")  # a senha segue só dentro do Connector, até ser enviada
        self.err.set_visible(False)
        self.cancelling = False
        self.busy_title.set_text("CONECTANDO...")
        self.busy_log.set_text("")
        self.cancel_btn.set_visible(True)
        self.set_state("busy")
        self.show("busy")
        ares_sfx.play("select")
        self.connector.start(profile, user, pw)

    def fail(self, msg):
        self.err.set_text(msg)
        self.err.set_visible(True)
        ares_sfx.play("error")

    def on_line(self, line):
        if SEPARATOR.match(line):
            return
        # linhas curtas: uma linha longa do servidor alargava a gaveta e ela não voltava a encolher
        shown = [ln if len(ln) <= LOG_COLS else ln[:LOG_COLS - 1] + "…"
                 for ln in self.connector.lines if not SEPARATOR.match(ln)][-3:]
        self.busy_log.set_text("\n".join(shown))

    def on_prompt(self, label, context, secret):
        self.prompt_msg.set_text("\n".join(context) or "O servidor pediu uma informação.")
        self.prompt_field.set_text(label.rstrip(":").upper())
        self.prompt_entry.set_visibility(not secret)
        self.prompt_entry.set_text("")
        self.set_state("busy")
        self.show("prompt")
        self.start_countdown()
        ares_sfx.play("notify")

    def on_prompt_submit(self, *_):
        text = self.prompt_entry.get_text().strip()
        if not text or not self.connector.active:
            return
        self.prompt_entry.set_text("")
        self.stop_countdown()
        self.busy_title.set_text("ENVIANDO...")
        self.busy_log.set_text("")
        self.cancel_btn.set_visible(True)
        self.show("busy")
        ares_sfx.play("select")
        self.connector.answer(text)

    def on_cancel(self, *_):
        if not self.connector.active:
            return
        self.cancelling = True
        self.stop_countdown()
        self.connector.cancel()

    def on_done(self, rc, lines):
        self.stop_countdown()
        cancelled, self.cancelling = self.cancelling, False
        self.busy_op = True  # segura o refresh até conferirmos o resultado

        def work():
            _rc, out = cli("status", timeout=6)
            info = parse_status(out)
            if cancelled and info["state"] == "busy":
                cli("disconnect", timeout=10)  # não deixa o serviço preso em "conectando"
                _rc, out = cli("status", timeout=6)
                info = parse_status(out)
            GLib.idle_add(self.after_connect, info, cancelled, rc, lines)
        threading.Thread(target=work, daemon=True).start()

    def after_connect(self, info, cancelled, rc, lines):
        self.busy_op = False
        if self.win is None:
            return
        if info["state"] == "on":
            ares_sfx.play("success")
        elif not cancelled:
            self.fail(error_text(lines)[-220:] or f"Falha ao conectar (código {rc}).")
        self.gen += 1
        self.apply_status(info, self.gen)

    # ---------------------------------------------------------- contagem do token
    def start_countdown(self):
        self.stop_countdown()
        self.t0 = GLib.get_monotonic_time()

        def tick():
            frac = 1 - (GLib.get_monotonic_time() - self.t0) / (TOKEN_WINDOW * 1e6)
            self.countdown.set_fraction(max(frac, 0))
            (self.countdown.add_css_class if frac < 0.3 else self.countdown.remove_css_class)("low")
            return frac > 0
        self.countdown.set_fraction(1)
        self.countdown_src = GLib.timeout_add(100, tick)

    def stop_countdown(self):
        if self.countdown_src is not None:
            GLib.source_remove(self.countdown_src)
            self.countdown_src = None

    # ---------------------------------------------------------- desconectar
    def on_disconnect(self, *_):
        self.busy_op = True
        self.busy_title.set_text("DESCONECTANDO...")
        self.busy_log.set_text("")
        self.cancel_btn.set_visible(False)
        self.show("busy")
        ares_sfx.play("select")

        def work():
            cli("disconnect", timeout=15)
            GLib.idle_add(self.after_disconnect)
        threading.Thread(target=work, daemon=True).start()

    def after_disconnect(self):
        self.busy_op = False
        ares_sfx.play("close")
        self.refresh()

    # ---------------------------------------------------------- teclado / saída
    def on_key(self, _ctrl, keyval, _code, _state):
        if keyval == Gdk.KEY_Escape:
            if self.connector.active:
                self.on_cancel()
            else:
                ares_sfx.play("close")
                self.quit()
            return True
        return False

    def do_shutdown(self):
        self.connector.cancel()
        Gtk.Application.do_shutdown(self)


def iter_children(widget):
    child = widget.get_first_child()
    while child is not None:
        nxt = child.get_next_sibling()
        yield child
        child = nxt


if __name__ == "__main__":
    VpnPanel().run(None)
