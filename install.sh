#!/usr/bin/env bash
# Instala os dotfiles: pacotes, links das configs e ajustes de sistema.
# Uso: ./install.sh            -> tudo
#      ./install.sh --links    -> só recria os links das configs

set -euo pipefail

DOTFILES="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP="$HOME/.dotfiles-backup/$(date +%Y%m%d-%H%M%S)"

info() { printf '\e[1;37m==> %s\e[0m\n' "$*"; }

# ---------------------------------------------------------------------------
# Links: cada arquivo em home/ vira um symlink no mesmo caminho em $HOME
# ---------------------------------------------------------------------------
link_home() {
    info "Linkando configs em $HOME"
    cd "$DOTFILES/home"
    find . -type f | while read -r f; do
        f="${f#./}"
        src="$DOTFILES/home/$f"
        dst="$HOME/$f"
        if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ]; then
            continue
        fi
        mkdir -p "$(dirname "$dst")"
        if [ -e "$dst" ] || [ -L "$dst" ]; then
            mkdir -p "$BACKUP/$(dirname "$f")"
            mv "$dst" "$BACKUP/$f"
            echo "  backup: ~/$f -> $BACKUP/$f"
        fi
        ln -s "$src" "$dst"
        echo "  link:   ~/$f"
    done
}

# ---------------------------------------------------------------------------
# Firefox: user.js no perfil padrão (o nome do perfil muda a cada instalação)
# ---------------------------------------------------------------------------
link_firefox() {
    local ini="$HOME/.config/mozilla/firefox/installs.ini"
    if [ ! -f "$ini" ]; then
        echo "  firefox: abra o Firefox uma vez e rode ./install.sh --links de novo"
        return
    fi
    local profile dst
    profile=$(grep -m1 '^Default=' "$ini" | cut -d= -f2)
    dst="$HOME/.config/mozilla/firefox/$profile/user.js"
    if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$DOTFILES/firefox/user.js" ]; then
        return
    fi
    [ -e "$dst" ] && mv "$dst" "$dst.bak"
    ln -s "$DOTFILES/firefox/user.js" "$dst"
    echo "  link:   firefox/$profile/user.js"
}

if [ "${1:-}" = "--links" ]; then
    link_home
    link_firefox
    exit 0
fi

# ---------------------------------------------------------------------------
# Pacotes
# ---------------------------------------------------------------------------
info "Instalando pacotes oficiais (pkglist.txt)"
sudo pacman -Syu --needed - < "$DOTFILES/pkglist.txt"

if ! command -v yay >/dev/null; then
    info "Instalando yay"
    tmp=$(mktemp -d)
    git clone https://aur.archlinux.org/yay-bin.git "$tmp/yay-bin"
    (cd "$tmp/yay-bin" && makepkg -si --noconfirm)
    rm -rf "$tmp"
fi

info "Instalando pacotes do AUR (pkglist-aur.txt)"
yay -S --needed - < "$DOTFILES/pkglist-aur.txt"

# ---------------------------------------------------------------------------
# Configs do usuário
# ---------------------------------------------------------------------------
link_home
link_firefox

info "VS Code: tema ARES Cyber-Red"
if command -v code >/dev/null; then
    python3 "$DOTFILES/tools/gen_vscode_theme.py" --install
else
    echo "  code não encontrado — depois rode: python3 tools/gen_vscode_theme.py --install"
fi

# ---------------------------------------------------------------------------
# Sistema (/etc) — HDMI 2.1 FRL no amdgpu (240 Hz via HDMI)
# ---------------------------------------------------------------------------
info "Copiando arquivos de sistema para /etc"
sudo cp -rv "$DOTFILES/system/etc/." /etc/
info "Regerando initramfs"
sudo mkinitcpio -P

info "Notificações: ARES notifyd no lugar do dunst"
systemctl --user daemon-reload
systemctl --user mask dunst.service
systemctl --user enable ares-agent-notifier.service

info "Login: greetd (autologin + hyprlock Breach Protocol)"
sudo systemctl disable cosmic-greeter.service 2>/dev/null || true
sudo systemctl enable greetd.service

# ---------------------------------------------------------------------------
# Preferências (dconf): modo escuro
# ---------------------------------------------------------------------------
info "Aplicando modo escuro"
gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'
gsettings set org.gnome.desktop.interface gtk-theme 'Adwaita-dark'

info "Pronto. Reinicie o PC para aplicar tudo."
