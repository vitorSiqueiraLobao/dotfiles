# ARES // backdrop dos painéis da barra
# Superfície layer-shell transparente em tela cheia por baixo do painel: clique fora = fechar.
# Precisa ser criada ANTES do painel (mesma camada, a ordem de mapeamento decide quem fica em cima).
# Deps: python-gobject gtk4 gtk4-layer-shell (o chamador já carregou a lib antes do GTK)

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gdk, Gtk  # noqa: E402
from gi.repository import Gtk4LayerShell as LayerShell  # noqa: E402

# Não pode ser 100% transparente: o Hyprland às vezes deixa uma camada assim com alpha 0 e não manda
# clique para ela. 1% de preto é invisível e garante que ela receba input.
CSS = "window.ares-backdrop { background-color: rgba(0, 0, 0, 0.01); border: none; box-shadow: none; }"


def attach(app, on_dismiss):
    """Uma janela por monitor cobrindo tudo (inclusive a barra); qualquer clique chama on_dismiss()."""
    provider = Gtk.CssProvider()
    provider.load_from_string(CSS)
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

    monitors = Gdk.Display.get_default().get_monitors()
    windows = []
    for i in range(monitors.get_n_items()):
        win = Gtk.ApplicationWindow(application=app)
        win.add_css_class("ares-backdrop")
        LayerShell.init_for_window(win)
        LayerShell.set_namespace(win, "ares-backdrop")
        LayerShell.set_monitor(win, monitors.get_item(i))
        LayerShell.set_layer(win, LayerShell.Layer.TOP)
        for edge in (LayerShell.Edge.TOP, LayerShell.Edge.BOTTOM, LayerShell.Edge.LEFT, LayerShell.Edge.RIGHT):
            LayerShell.set_anchor(win, edge, True)
        LayerShell.set_exclusive_zone(win, -1)  # ignora a zona da waybar e cobre ela também
        LayerShell.set_keyboard_mode(win, LayerShell.KeyboardMode.NONE)

        click = Gtk.GestureClick(button=0)  # qualquer botão
        click.connect("pressed", lambda *_: on_dismiss())
        win.add_controller(click)
        win.set_child(Gtk.Box(hexpand=True, vexpand=True))
        win.present()
        windows.append(win)
    return windows
