#!/usr/bin/env bash
# ARES // wallpaper
# Animado: mpvpaper renderizando o shader do capacete de Ares em ASCII 3D sobre uma
# fonte de vídeo "vazia" (lavfi) do tamanho do monitor. Pausa sozinho quando o fundo
# está coberto por janelas (-p). Sem mpvpaper, cai no hyprpaper com a imagem estática.
# Uso: wallpaper.sh            -> inicia/reinicia
#      wallpaper.sh static     -> força o estático (hyprpaper)

SHADER="$HOME/.config/ares/wallpaper/ares_helmet.glsl"
FPS=30

pkill -x mpvpaper 2>/dev/null
pkill -x hyprpaper 2>/dev/null
sleep 0.2

if [ "$1" != "static" ] && command -v mpvpaper >/dev/null && [ -f "$SHADER" ]; then
    # resolução do primeiro monitor (ex.: 5120x1440)
    RES=$(hyprctl -j monitors | python3 -c 'import json,sys; m=json.load(sys.stdin)[0]; print("%dx%d" % (m["width"], m["height"]))')
    exec mpvpaper -p \
        -o "no-audio loop-file=inf hwdec=no glsl-shaders=$SHADER" \
        ALL "av://lavfi:color=c=0x08060a:s=${RES}:r=${FPS}"
else
    exec hyprpaper
fi
