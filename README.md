# dotfiles

Configs do meu Arch Linux + Hyprland (ARES).

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
| `system/etc/modprobe.d/amdgpu-frl.conf` | HDMI 2.1 FRL no amdgpu (5120x1440@240 via HDMI, kernel ≥ 7.2) |

## Notas

- Os caminhos assumem o usuário `w0lf` (ex.: `/home/w0lf/.config/hypr/wallpaper.png`).
- Como as configs são symlinks para este repo, qualquer mudança já aparece no `git status`.
  Para salvar: `git add -A && git commit -m "..." && git push`.
- Atualizar a lista de pacotes:
  `pacman -Qqen > pkglist.txt && pacman -Qqem | grep -v -- -debug > pkglist-aur.txt`
