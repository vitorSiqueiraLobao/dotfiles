#!/usr/bin/env bash
# ARES // busca de pacotes (pacman + AUR) com fzf
# Uso: ares_pkg.sh [busca inicial]      (comando "pkg" no bash, Super+Shift+P)
#   Enter   instala os marcados (Tab marca vários) com yay
#   Ctrl-R  remove os marcados (pacman -Rns)
#   Ctrl-I  alterna: todos / só instalados
# Ordem: nome exato > começa com a busca > palavra do nome > contém a busca; dentro de
# cada grupo, os mais instalados primeiro (estatísticas públicas do pkgstats.archlinux.de).
# Nomes do AUR e popularidade ficam em cache por 1 dia em ~/.cache/ares/.
# Deps: fzf yay curl python3

SELF=$(readlink -f "$0")
CACHE=~/.cache/ares
AUR_LIST=$CACHE/aur-packages.txt
STATS=$CACHE/pkgstats.tsv
INDEX=$CACHE/pkg-index.txt
R=$'\e[38;2;255;31;61m' C=$'\e[38;2;0;240;255m' G=$'\e[38;2;122;111;115m' A=$'\e[38;2;255;176;0m'
W=$'\e[38;2;232;226;228m' X=$'\e[0m'

refresh_aur() {
    mkdir -p "$CACHE"
    if [[ ! -s $AUR_LIST || -n $(find "$AUR_LIST" -mmin +1440 2>/dev/null) ]]; then
        curl -fsSL --max-time 20 https://aur.archlinux.org/packages.gz | gunzip > "$AUR_LIST.tmp" 2>/dev/null \
            && mv "$AUR_LIST.tmp" "$AUR_LIST" || rm -f "$AUR_LIST.tmp"
    fi
}

refresh_stats() {  # nome<TAB>nº de máquinas que têm o pacote
    if [[ ! -s $STATS || -n $(find "$STATS" -mmin +1440 2>/dev/null) ]]; then
        python3 - "$STATS" <<'EOF' 2>/dev/null
import json, os, sys, urllib.request
rows, off, total = [], 0, 1
while off < total:
    with urllib.request.urlopen(f"https://pkgstats.archlinux.de/api/packages?limit=10000&offset={off}", timeout=20) as r:
        d = json.load(r)
    page = d["packagePopularities"]
    if not page:
        break
    rows += [f'{p["name"]}\t{p["count"]}' for p in page]
    off, total = off + len(page), d["total"]
with open(sys.argv[1] + ".tmp", "w") as f:
    f.write("\n".join(rows) + "\n")
os.replace(sys.argv[1] + ".tmp", sys.argv[1])
EOF
    fi
}

# índice completo, já ordenado do mais para o menos instalado
build_index() {
    local stats=$STATS
    [[ -s $stats ]] || stats=/dev/null
    list_all | awk -F'\t' 'FILENAME != "-" { c[$1] = $2; next } { print (c[$1] + 0) "\t" $0 }' \
        "$stats" - | sort -t$'\t' -k1,1nr -s | cut -f2- > "$INDEX.tmp" \
        && mv "$INDEX.tmp" "$INDEX"
}

# filtra o índice pela busca ($1) e ordena por relevância; só instalados se o prompt for "✔ › "
rank() {
    local only=0
    [[ $FZF_PROMPT == ✔* ]] && only=1
    awk -F'\t' -v q="$1" -v only="$only" -v C="$C" -v X="$X" -v MAX=500 '
        BEGIN { n = split(tolower(q), w, " ") }
        only && $0 !~ /✔/ { next }
        {
            name = tolower($1)
            for (i = 1; i <= n; i++) if (!index(name, w[i])) next
            if (n == 0) t = 1
            else if (name == w[1]) t = 0
            else if (index(name, w[1]) == 1) t = 1
            else if (name ~ ("[-_.]" w[1])) t = 2
            else t = 3
            if (cnt[t] >= MAX) next
            line = $0
            if (n) {  # destaca o trecho encontrado no nome
                p = index(name, w[1]); L = length(w[1])
                line = substr($1, 1, p - 1) C substr($1, p, L) X substr($1, p + L) "\t" $2
            }
            buf[t, ++cnt[t]] = line
        }
        END { for (t = 0; t <= 3; t++) for (i = 1; i <= cnt[t]; i++) if (out++ < MAX) print buf[t, i] }
    ' "$INDEX"
}

# uma linha por pacote: "nome<TAB>✔   [repo]" (largura fixa depois do nome, para o fzf
# desempatar só pelo tamanho do nome; a versão aparece na prévia)
list_all() {
    pacman -Sl 2>/dev/null | awk -v G="$G" -v C="$C" -v X="$X" '{
        mark = ($4 ~ /installed/) ? "✔" : " "
        printf "%s\t%s%s%s%s%10s%s\n", $2, C, mark, X, G, "[" $1 "]", X }'
    if [[ -s $AUR_LIST ]]; then
        local foreign
        foreign=$(pacman -Qmq 2>/dev/null | tr '\n' ' ')
        awk -v A="$A" -v C="$C" -v X="$X" -v inst=" $foreign" '
            NF { mark = index(inst, " " $1 " ") ? "✔" : " "
                 printf "%s\t%s%s%s%s%10s%s\n", $1, C, mark, X, A, "[aur]", X }' "$AUR_LIST"
    fi
}

preview() {  # $1 = nome, $2 = [repo]
    local name=$1 repo=${2//[\[\] ✔]/}
    if [[ $repo == aur ]]; then
        curl -fsS --max-time 8 "https://aur.archlinux.org/rpc/v5/info?arg[]=$name" | python3 -c '
import json, sys, time
R, C, G, W, X = "\033[38;2;255;31;61m", "\033[38;2;0;240;255m", "\033[38;2;122;111;115m", "\033[38;2;232;226;228m", "\033[0m"
try:
    p = json.load(sys.stdin)["results"][0]
except Exception:
    print("sem informações (offline?)"); sys.exit()
def row(k, v):
    if v: print(f"{R}{k:<12}{X}{v}")
name, ver, votes, pop = p["Name"], p["Version"], p.get("NumVotes", 0), p.get("Popularity", 0)
print(f"{C}{name}{X} {G}{ver}{X}  \033[38;2;255;176;0m[AUR]{X}\n")
row("Descrição", p.get("Description"))
row("Votos", f"{votes}  ·  popularidade {pop:.2f}")
row("Mantenedor", p.get("Maintainer") or "órfão!")
row("Atualizado", time.strftime("%d/%m/%Y", time.localtime(p.get("LastModified", 0))))
if p.get("OutOfDate"): row("Status", "\033[38;2;255;31;61mdesatualizado\033[0m")
row("URL", p.get("URL"))
row("Depende de", "  ".join(p.get("Depends", [])))
row("Make deps", "  ".join(p.get("MakeDepends", [])))
'
    else
        pacman -Si "$repo/$name" 2>/dev/null | sed -E "s/^([A-Z][^:]*[^ ])( *): /$R\1$X\2: /"
        if pacman -Qq "$name" &>/dev/null; then
            printf '\n%s── INSTALADO ──%s\n' "$C" "$X"
            pacman -Qi "$name" | grep -E '^(Install Date|Install Reason|Required By)' \
                | sed -E "s/^([A-Z][^:]*[^ ])( *): /$C\1$X\2: /"
        fi
    fi
}

act() {  # $1 = install|remove, resto = linhas marcadas
    local mode=$1; shift
    local pkgs=() l
    for l in "$@"; do pkgs+=("${l%%$'\t'*}"); done
    ((${#pkgs[@]})) || return
    clear
    if [[ $mode == install ]]; then
        printf '%s▓▒░ INSTALANDO ░▒▓%s %s\n\n' "$R" "$X" "${pkgs[*]}"
        yay -S --needed "${pkgs[@]}"
    else
        printf '%s▓▒░ REMOVENDO ░▒▓%s %s\n\n' "$R" "$X" "${pkgs[*]}"
        sudo pacman -Rns "${pkgs[@]}"
    fi
    printf '\n%s[ Enter para voltar à busca ]%s' "$G" "$X"
    read -r _
}

case $1 in
    --rank) shift; rank "$*"; exit ;;
    --rebuild) build_index; exit ;;
    --preview) shift; preview "$@"; exit ;;
    --act) shift; act "$@"; exit ;;
esac

if ! command -v fzf >/dev/null; then
    printf '%sfzf não está instalado.%s Rode:\n\n  sudo pacman -S --needed fzf\n\n%s[ Enter para sair ]%s' "$R" "$X" "$G" "$X"
    read -r _; exit 1
fi

export SHELL=bash
printf '%s▓▒░ ARES // PKG ░▒▓%s %scarregando índice…%s\n' "$R" "$X" "$G" "$X"
refresh_aur
refresh_stats
build_index

fzf --ansi --multi --query "$*" --disabled \
    --delimiter=$'\t' --tabstop=36 \
    --layout=reverse --border=sharp --border-label=' ▓▒░ ARES // PKG.SEARCH ░▒▓ ' --border-label-pos=3 \
    --prompt='› ' --pointer='▌' --marker='▶ ' --info=inline-right \
    --header=$'Enter instalar · Tab marcar · Ctrl-R remover · Ctrl-I só instalados · Esc sair\n' \
    --preview "'$SELF' --preview {1} {2}" --preview-window='right,55%,border-left,wrap' \
    --color='bg:-1,bg+:#1a0f14,fg:#c9c0c4,fg+:#e8e2e4,hl:#00f0ff,hl+:#00f0ff,info:#7a6f73' \
    --color='prompt:#ff1f3d,pointer:#ff1f3d,marker:#ffb000,spinner:#ff1f3d,header:#7a6f73' \
    --color='border:#3a1018,label:#ff1f3d,query:#e8e2e4,gutter:-1,preview-border:#3a1018' \
    --bind "start,change:reload-sync('$SELF' --rank {q})" \
    --bind "enter:execute('$SELF' --act install {+})+reload-sync('$SELF' --rebuild; '$SELF' --rank {q})" \
    --bind "ctrl-r:execute('$SELF' --act remove {+})+reload-sync('$SELF' --rebuild; '$SELF' --rank {q})" \
    --bind "ctrl-i:transform-prompt([[ \$FZF_PROMPT == '› ' ]] && echo '✔ › ' || echo '› ')+reload-sync('$SELF' --rank {q})"
