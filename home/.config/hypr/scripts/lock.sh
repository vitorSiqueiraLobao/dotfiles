#!/usr/bin/env bash
# ARES // lock
# Bloqueia com o hyprlock (Breach Protocol). A animação de desbloqueio abre antes,
# preta e escondida atrás do hyprlock; se a senha for aceita ela recebe SIGUSR1 e
# começa na hora (sem o desktop piscar). Usado no Super+L e no início da sessão.
# Argumentos extras vão para o hyprlock (ex.: --immediate-render).

pgrep -x hyprlock >/dev/null && exit 0

# ARES_SILENT=1: bloqueio automático (hypridle), sem som
[[ -z $ARES_SILENT ]] && "$HOME/.config/hypr/scripts/ares_sfx.py" lock

"$HOME/.config/hypr/scripts/breach_success.py" --wait &
anim=$!

# Só trava depois que a animação já está mapeada na tela (máx. 2 s), para ela
# estar pintada por baixo no momento em que o hyprlock liberar a sessão.
for _ in $(seq 1 40); do
    hyprctl layers 2>/dev/null | grep -q 'namespace: ares-breach' && break
    sleep 0.05
done

if hyprlock "$@"; then
    kill -USR1 "$anim"
    wait "$anim"
else
    kill "$anim"
fi
