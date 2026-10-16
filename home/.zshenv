# ==============================================================================
# ARES MAINFRAME // ZSHENV
# ==============================================================================
export PATH="$HOME/.local/bin:$HOME/bin:$PATH"

# Zsh module and function paths (userland + system fallback)
if [[ -d "$HOME/.local/lib/zsh/5.9.2" ]]; then
    module_path=("$HOME/.local/lib/zsh/5.9.2" /usr/lib/zsh/5.9.2 $module_path)
fi
if [[ -d "$HOME/.local/share/zsh/functions" ]]; then
    setopt nullglob
    fpath=("$HOME/.local/share/zsh/functions" "$HOME/.local/share/zsh/functions"/*(N/) "$HOME/.local/share/zsh/functions"/*/*(N/) "$HOME/.local/share/zsh/site-functions" $fpath)
    unsetopt nullglob
fi
