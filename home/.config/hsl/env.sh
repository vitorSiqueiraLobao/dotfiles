# Credenciais de rede do HSL (AD) para o shell. Carregado pelo ~/.bashrc, inclusive em shells
# não interativos (scripts, Claude Code). Este arquivo não contém segredo: o usuário vem de
# ~/.config/hsl/hsl.conf (local, fora do git) e a senha do gnome-keyring (service=hsl-ad).
# Só consulta o keyring se ele já estiver destravado, para nunca abrir prompt nem travar o shell.
# Para gravar ou trocar a senha: hsl-senha

if [[ -r $HOME/.config/hsl/hsl.conf ]]; then
    HSL_USER=$(sed -n 's/^HSL_USER=//p' "$HOME/.config/hsl/hsl.conf" | tr -d "\"'")
    [[ -n $HSL_USER ]] && export HSL_USER || unset HSL_USER
fi

if [[ -n ${HSL_USER:-} && -z ${HSL_PASSWORD:-} ]] && command -v secret-tool >/dev/null \
    && [[ $(busctl --user get-property org.freedesktop.secrets /org/freedesktop/secrets/aliases/default \
            org.freedesktop.Secret.Collection Locked 2>/dev/null) == "b false" ]]; then
    HSL_PASSWORD=$(timeout 3 secret-tool lookup service hsl-ad account "$HSL_USER" 2>/dev/null)
    [[ -n $HSL_PASSWORD ]] && export HSL_PASSWORD || unset HSL_PASSWORD
fi
