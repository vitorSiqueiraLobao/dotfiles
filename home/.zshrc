# ==============================================================================
# ARES MAINFRAME // ZSH CONFIG
# Cyber-Red theme, developer plugins, fast autocomplete, history & git
# ==============================================================================

# Antigravity CLI & user binaries
export PATH="$HOME/.local/bin:$HOME/bin:$PATH"

# Se não estiver rodando interativamente, não faz nada
[[ $- != *i* ]] && return

# ------------------------------------------------------------------------------
# Oh My Zsh
# ------------------------------------------------------------------------------
export ZSH="$HOME/.oh-my-zsh"

# Desativa o tema padrão do OMZ para usarmos o nosso prompt nativo ARES Cyber-Red
ZSH_THEME=""

# Mostra pontinhos vermelhos enquanto aguarda autocompletar comandos longos
COMPLETION_WAITING_DOTS="true"

# Caminho para completions adicionais
fpath=(${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-completions/src $fpath)

# Plugins ativos para o dia a dia de desenvolvimento
# Ordem de carregamento: fzf-tab antes de syntax-highlighting/autosuggestions
plugins=(
    git
    sudo
    colored-man-pages
    extract
    fzf-tab
    history-substring-search
    zsh-autosuggestions
    zsh-syntax-highlighting
)

# Carrega Oh My Zsh se instalado
if [[ -f "$ZSH/oh-my-zsh.sh" ]]; then
    source "$ZSH/oh-my-zsh.sh"
fi

# ------------------------------------------------------------------------------
# Histórico rápido e persistente
# ------------------------------------------------------------------------------
HISTFILE="$HOME/.zsh_history"
HISTSIZE=50000
SAVEHIST=50000

setopt EXTENDED_HISTORY          # Grava timestamp e duração do comando
setopt SHARE_HISTORY             # Compartilha histórico entre todas as abas/janelas imediatamente
setopt HIST_EXPIRE_DUPS_FIRST    # Remove duplicados mais antigos quando atingir o limite
setopt HIST_IGNORE_DUPS          # Ignora comando idêntico ao imediatamente anterior
setopt HIST_IGNORE_ALL_DUPS      # Remove duplicatas mais antigas ao adicionar nova
setopt HIST_FIND_NO_DUPS         # Não mostra o mesmo comando repetidas vezes na busca
setopt HIST_IGNORE_SPACE         # Comandos iniciados com espaço não são gravados (senhas/segredos)
setopt HIST_SAVE_NO_DUPS         # Não grava duplicatas no arquivo de histórico
setopt HIST_REDUCE_BLANKS        # Remove espaços desnecessários
setopt HIST_VERIFY               # Permite editar comando antes de rodar após expansão de histórico

# ------------------------------------------------------------------------------
# FZF (Fuzzy finder) & fzf-tab (Autocomplete interativo com preview)
# ------------------------------------------------------------------------------
if command -v fzf >/dev/null 2>&1; then
    # Ativa integração oficial do fzf (Ctrl+R, Ctrl+T, Alt+C)
    source <(fzf --zsh)

    # Cores ARES Cyber-Red para o menu do fzf
    export FZF_DEFAULT_OPTS=" \
        --color=bg+:#1a0f14,bg:#08060a,spinner:#ff1f3d,hl:#ff1f3d \
        --color=fg:#e8e2e4,header:#ff1f3d,info:#00f0ff,pointer:#00f0ff \
        --color=marker:#00f0ff,fg+:#ffffff,prompt:#ff1f3d,hl+:#00f0ff \
        --border=rounded --layout=reverse --prompt='󰭎 ' --pointer='▶ ' --marker='✓ '"

    # Usa fd para buscas ultra rápidas respeitando .gitignore se disponível
    if command -v fd >/dev/null 2>&1; then
        export FZF_DEFAULT_COMMAND='fd --type f --strip-cwd-prefix --hidden --follow --exclude .git'
        export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
        export FZF_ALT_C_COMMAND='fd --type d --strip-cwd-prefix --hidden --follow --exclude .git'
    fi
fi

# Ajustes do plugin fzf-tab
zstyle ':completion:*:git-checkout:*' sort false
zstyle ':completion:*:descriptions' format '[%d]'
zstyle ':completion:*' list-colors ${(s.:.)LS_COLORS}
zstyle ':fzf-tab:complete:cd:*' fzf-preview 'ls -1 --color=always $realpath'
zstyle ':fzf-tab:complete:z:*' fzf-preview 'ls -1 --color=always $realpath'
zstyle ':completion:*:*:*:*:processes' command "ps -u $USER -o pid,user,%cpu,%mem,command -w"
zstyle ':fzf-tab:complete:(kill|ps):argument-rest' fzf-preview \
    '[[ $group == "[process ID]" ]] && ps --pid=$word -o cmd --no-headers -w -w'
zstyle ':fzf-tab:complete:(kill|ps):argument-rest' fzf-flags --preview-window=down:3:wrap

# ------------------------------------------------------------------------------
# zsh-autosuggestions (Sugestões estilo Fish)
# ------------------------------------------------------------------------------
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE="fg=244"
ZSH_AUTOSUGGEST_STRATEGY=(history completion)
ZSH_AUTOSUGGEST_USE_ASYNC=1
bindkey '^E' autosuggest-accept
bindkey '^ ' autosuggest-accept

# ------------------------------------------------------------------------------
# zsh-history-substring-search (Busca no histórico digitando parte do comando)
# ------------------------------------------------------------------------------
bindkey '^[[A' history-substring-search-up
bindkey '^[[B' history-substring-search-down
[[ -n "$terminfo[kcuu1]" ]] && bindkey "$terminfo[kcuu1]" history-substring-search-up
[[ -n "$terminfo[kcud1]" ]] && bindkey "$terminfo[kcud1]" history-substring-search-down
HISTORY_SUBSTRING_SEARCH_HIGHLIGHT_FOUND='fg=cyan,bold'
HISTORY_SUBSTRING_SEARCH_HIGHLIGHT_NOT_FOUND='fg=red,bold'

# ------------------------------------------------------------------------------
# Navegação e Atalhos de Teclado (Kitty / Terminal moderno)
# ------------------------------------------------------------------------------
bindkey '^[[H' beginning-of-line          # Home
bindkey '^[[F' end-of-line                # End
bindkey '^[[3~' delete-char               # Delete
bindkey '^[[1;5C' forward-word            # Ctrl+Right
bindkey '^[[1;5D' backward-word           # Ctrl+Left
bindkey '^H' backward-kill-word           # Ctrl+Backspace
bindkey '^[[3;5~' kill-word               # Ctrl+Delete

# ------------------------------------------------------------------------------
# Zoxide (cd inteligente com 'z')
# ------------------------------------------------------------------------------
if command -v zoxide >/dev/null 2>&1; then
    eval "$(zoxide init zsh)"
fi

# ------------------------------------------------------------------------------
# Prompt ARES Cyber-Red (Estrutura Vermelha, Dados Ciano + Git Dinâmico)
# ------------------------------------------------------------------------------
autoload -Uz vcs_info
setopt prompt_subst

zstyle ':vcs_info:*' enable git
zstyle ':vcs_info:git:*' check-for-changes true
zstyle ':vcs_info:git:*' stagedstr '%F{#2bd9a0}+%f'
zstyle ':vcs_info:git:*' unstagedstr '%F{#ffb000}*%f'
zstyle ':vcs_info:git:*' formats '──[%F{#00f0ff} %b%c%u%F{#ff1f3d}]'
zstyle ':vcs_info:git:*' actionformats '──[%F{#00f0ff} %b|%a%c%u%F{#ff1f3d}]'

precmd_cyber_red() {
    vcs_info
}
precmd_functions+=(precmd_cyber_red)

# Linha 1: ┌──[user@host]──[pasta]──[ git]
# Linha 2: └──╼ $ (se erro, mostra código em vermelho)
PROMPT='%F{#ff1f3d}┌──[%F{#00f0ff}%n@%m%F{#ff1f3d}]──[%F{#e8e2e4}%~%F{#ff1f3d}]${vcs_info_msg_0_}%f
%F{#ff1f3d}└──╼%(?.%F{#00f0ff}.%F{#ff1f3d}[%?] )%#%f '

# ------------------------------------------------------------------------------
# Aliases e Funções Úteis
# ------------------------------------------------------------------------------
alias ls='ls --color=auto'
alias grep='grep --color=auto'
alias g='git'
alias reload='source ~/.zshrc'
alias agy='agy --dangerously-skip-permissions'
alias agy-safe='command agy'
alias ports='ss -tulanp'
alias alert='ares-alert'
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'

# y: abre o yazi e, ao sair (q), o shell fica na pasta onde você estava
y() {
    local tmp cwd
    tmp=$(mktemp -t yazi-cwd.XXXXXX)
    yazi "$@" --cwd-file="$tmp"
    cwd=$(<"$tmp")
    [[ -n $cwd && $cwd != "$PWD" ]] && builtin cd -- "$cwd"
    rm -f -- "$tmp"
}

# pkg [busca]: procura/instala pacotes do pacman + AUR (fzf)
alias pkg='~/.config/hypr/scripts/ares_pkg.sh'

# Som de boot no kitty ao abrir o terminal
if [[ $TERM == xterm-kitty ]]; then
    for _d in ~/.local/share/ares/sounds ~/.config/ares/sounds; do
        for _e in wav ogg flac mp3; do
            if [[ -f "$_d/open.$_e" ]]; then
                ( pw-play -P '{ ares.sfx=true }' --latency 20ms "$_d/open.$_e" >/dev/null 2>&1 & )
                break 2
            fi
        done
    done
    unset _d _e
fi

# Fastfetch ao abrir o terminal
command -v fastfetch >/dev/null && fastfetch
