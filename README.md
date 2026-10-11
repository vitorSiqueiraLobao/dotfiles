# dotfiles

Configs do meu Arch Linux + Hyprland (ARES) — tema **Cyber-Red** (vermelho = estrutura,
ciano = dados), fonte IBM 3270 Nerd Font, visual retrô/cyberpunk.

## Destaques

- **Login/bloqueio Breach Protocol**: o greetd faz login automático e o Hyprland já abre
  travado no hyprlock no estilo do minigame do Cyberpunk 2077. Ao desbloquear, uma animação
  continua o HUD: a CODE MATRIX é resolvida, os daemons são instalados e aparece
  BREACH SUCCESSFUL. Logout cai no tuigreet.
- **Notificações próprias** (`ares_notifyd.py`): servidor org.freedesktop.Notifications em
  GTK4 com cantos cortados e o ícone do app numa moldura (substitui o dunst).
- **Waybar**: medidores ASCII, mixer de volume por app, toggle claro/escuro e menu do
  sistema no badge ARES (bloquear, suspender, logout, reiniciar, desligar).

## Instalar numa máquina nova

```bash
git clone https://github.com/vitorSiqueiraLobao/dotfiles.git ~/dotfiles
cd ~/dotfiles
./install.sh
```

O script:

1. instala os pacotes de `pkglist.txt` (pacman) e `pkglist-aur.txt` (yay);
2. cria symlinks de tudo que está em `home/` para o mesmo caminho em `~`
   (arquivos existentes vão para `~/.dotfiles-backup/<data>/`);
3. copia `system/etc/` para `/etc` e regera o initramfs;
4. aplica o modo escuro via gsettings.

Só os links, sem instalar nada: `./install.sh --links`

## Estrutura

| Caminho | O que é |
|---|---|
| `home/.config/hypr/` | Hyprland (Lua), hyprlock, hyprpaper, wallpaper |
| `home/.config/waybar/` | Barra + scripts (GPU, áudio, toggle claro/escuro) |
| `home/.config/{kitty,wofi,dunst,btop,fastfetch}/` | Terminal, launcher, notificações, monitores |
| `home/.config/gtk-{3,4}.0/` | Tema/CSS do GTK |
| `home/.XCompose` | `' + c` → `ç` no layout US internacional |
| `home/.bashrc`, `home/.bash_profile` | Shell |
| `home/.config/hypr/scripts/` | lock.sh + Breach Protocol (matriz, sequência, animação), notifyd, screenshot |
| `home/.config/systemd/user/`, `home/.local/share/dbus-1/` | Ativação do ARES notifyd no lugar do dunst |
| `system/etc/modprobe.d/amdgpu-frl.conf` | HDMI 2.1 FRL no amdgpu (5120x1440@240 via HDMI, kernel ≥ 7.2) |
| `system/etc/greetd/config.toml` | Login automático no Hyprland + tuigreet no logout |

## Notas

- Os caminhos assumem o usuário `w0lf` (ex.: `/home/w0lf/.config/hypr/wallpaper.png`).
- Como as configs são symlinks para este repo, qualquer mudança já aparece no `git status`.
  Para salvar: `git add -A && git commit -m "..." && git push`.
- Atualizar a lista de pacotes:
  `pacman -Qqen > pkglist.txt && pacman -Qqem | grep -v -- -debug > pkglist-aur.txt`
