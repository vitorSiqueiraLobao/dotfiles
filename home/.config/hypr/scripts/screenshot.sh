#!/usr/bin/env bash
# ARES // Screenshot
# Uso: screenshot.sh        -> clique numa janela OU arraste para selecionar área (Esc cancela)
#      screenshot.sh full   -> tela inteira
# Salva em ~/Pictures/Screenshots e copia para a área de transferência.

DIR="$HOME/Pictures/Screenshots"
mkdir -p "$DIR"
FILE="$DIR/$(date +%Y-%m-%d_%H-%M-%S).png"

if [ "$1" = "full" ]; then
    grim "$FILE" || exit 1
else
    # Janelas visíveis como caixas para o slurp (flutuantes e mais recentes primeiro)
    BOXES=$(python3 - <<'EOF'
import json, subprocess
mons = json.loads(subprocess.check_output(["hyprctl", "-j", "monitors"]))
visible = {m["activeWorkspace"]["id"] for m in mons} | {m["specialWorkspace"]["id"] for m in mons}
clients = json.loads(subprocess.check_output(["hyprctl", "-j", "clients"]))
clients = [c for c in clients if c["mapped"] and not c["hidden"] and c["workspace"]["id"] in visible]
clients.sort(key=lambda c: (not c["floating"], c["focusHistoryID"]))
for c in clients:
    (x, y), (w, h) = c["at"], c["size"]
    print(f"{x},{y} {w}x{h}")
EOF
)
    GEOM=$(printf '%s\n' "$BOXES" | slurp -d \
        -b '#00000066' -c '#eaeaeaff' -s '#ffffff1a' -B '#ffffff0d' -w 1 \
        -F "JetBrainsMono Nerd Font") || exit 0
    sleep 0.15  # espera o overlay do slurp sumir
    grim -g "$GEOM" "$FILE" || exit 1
fi

wl-copy --type image/png < "$FILE"
notify-send -a screenshot -i "$FILE" "SCREENSHOT // CAPTURED" "$(basename "$FILE") — copiado para a área de transferência"
