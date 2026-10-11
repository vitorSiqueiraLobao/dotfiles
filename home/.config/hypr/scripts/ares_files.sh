#!/usr/bin/env bash
# ARES // explorador de arquivos: yazi dentro do kitty holograma (Super+E, pastas, "mostrar na pasta")
# Uso: ares_files.sh [pasta | arquivo | file://URI ...]
#   pasta   -> abre nela
#   arquivo -> abre a pasta dele com o arquivo selecionado
args=()
for a in "$@"; do
    [[ $a == file://* ]] && a=$(python3 -c 'import sys, urllib.parse as u; print(u.unquote(u.urlparse(sys.argv[1]).path))' "$a")
    [[ -n $a ]] && args+=("$a")
done
"$HOME/.config/hypr/scripts/ares_sfx.py" open &
exec kitty --class ares-files -o background_opacity=0.88 -e yazi "${args[@]}"
