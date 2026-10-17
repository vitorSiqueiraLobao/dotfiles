# ARES // som de digitação no prompt do bash (mesmo "key" do lançador Super+Space)
# Carregado pelo ~/.bashrc só dentro do kitty. Toca ao digitar caracteres no prompt;
# nvim, htop etc. ficam em silêncio (é o readline do bash que dispara o som).
# Respeita ~/.config/ares/sfx.conf (volume / enabled).
# Comando: sfx [on|off]  -> liga/desliga nesta sessão

__ares_sfx_file() {  # $1 = nome do som -> caminho (sons do jogo primeiro)
    local d e
    for d in ~/.local/share/ares/sounds ~/.config/ares/sounds; do
        for e in wav ogg flac mp3; do
            [[ -f $d/$1.$e ]] && { printf '%s' "$d/$1.$e"; return; }
        done
    done
}

__ares_sfx_vol=0.5
__ares_sfx_on=1
if [[ -f ~/.config/ares/sfx.conf ]]; then
    while IFS='=' read -r __k __v; do
        __k=${__k//[[:space:]]/}; __v=${__v%%#*}; __v=${__v//[[:space:]]/}
        case $__k in
            volume) __ares_sfx_vol=$__v ;;
            enabled) [[ ${__v,,} =~ ^(0|false|no|off|nao|não)$ ]] && __ares_sfx_on=0 ;;
        esac
    done < ~/.config/ares/sfx.conf
    unset __k __v
fi
__ares_sfx_key=$(__ares_sfx_file key)

__ares_play() {  # $1 = caminho; toca solto, sem mensagens de job
    [[ $__ares_sfx_on == 1 && -n $1 ]] || return
    # -P marca o stream: o mixer de volume ignora quem tem ares.sfx
    ( pw-play -P '{ ares.sfx=true }' --latency 20ms --volume "$__ares_sfx_vol" "$1" >/dev/null 2>&1 & )
}

__ares_ins() {  # $1 = código hex do caractere digitado
    local ch
    printf -v ch "\\x$1"
    READLINE_LINE=${READLINE_LINE:0:READLINE_POINT}$ch${READLINE_LINE:READLINE_POINT}
    ((READLINE_POINT++))
    __ares_play "$__ares_sfx_key"
}

# liga cada caractere imprimível (espaço até ~) ao __ares_ins
for ((__i = 32; __i < 127; __i++)); do
    printf -v __h '%02x' "$__i"
    bind -x "\"\\x$__h\": __ares_ins $__h"
done
unset __i __h

sfx() {
    case $1 in
        on) __ares_sfx_on=1 ;;
        off) __ares_sfx_on=0 ;;
        *) ((__ares_sfx_on ^= 1)) ;;
    esac
    echo "sfx: $([[ $__ares_sfx_on == 1 ]] && echo on || echo off)"
}

# som de boot ao abrir o terminal
__ares_play "$(__ares_sfx_file open)"
