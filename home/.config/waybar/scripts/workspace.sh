#!/usr/bin/env bash
# Botão de workspace do Hyprland para a Waybar.
# O módulo nativo hyprland/workspaces envia o dispatcher antigo ("dispatch workspace N"),
# que o Hyprland com config em Lua rejeita; por isso o clique é feito aqui.
# Uso: workspace.sh N          -> imprime o estado e atualiza a cada evento do Hyprland
#      workspace.sh N focus    -> troca para o workspace N

N="$1"

if [ "$2" = "focus" ]; then
    exec hyprctl dispatch "hl.dsp.focus({ workspace = $N })"
fi

render() {
    local active windows
    active=$(hyprctl activeworkspace -j | jq -r '.id')
    windows=$(hyprctl workspaces -j | jq -r --argjson n "$N" '[.[] | select(.id == $n)][0].windows // 0')

    if [ "$active" = "$N" ]; then
        echo "{\"text\": \"[$N]\", \"class\": \"active\"}"
    elif [ "$windows" -gt 0 ]; then
        echo "{\"text\": \"[$N]\", \"class\": \"occupied\"}"
    else
        echo "{\"text\": \"\"}"
    fi
}

render
socat -u "UNIX-CONNECT:$XDG_RUNTIME_DIR/hypr/$HYPRLAND_INSTANCE_SIGNATURE/.socket2.sock" - 2>/dev/null |
    while read -r _; do render; done
