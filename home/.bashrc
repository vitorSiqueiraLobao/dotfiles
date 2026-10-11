#
# ~/.bashrc
#

# Added by Antigravity CLI installer
export PATH="/home/w0lf/.local/bin:$PATH"

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

alias ls='ls --color=auto'
alias grep='grep --color=auto'
# ARES Cyber-Red Prompt (vermelho = estrutura, ciano = dados)
PS1='\[\e[38;2;255;31;61m\]┌──[\[\e[38;2;0;240;255m\]\u@\h\[\e[38;2;255;31;61m\]]──[\[\e[38;2;232;226;228m\]\w\[\e[38;2;255;31;61m\]]\n└──╼ \[\e[38;2;0;240;255m\]\$ \[\e[0m\]'




# Sons ARES no kitty: digitação no prompt + som ao abrir
[[ $TERM == xterm-kitty && -f ~/.config/ares/keysfx.bash ]] && source ~/.config/ares/keysfx.bash

# Fastfetch ao abrir o terminal
command -v fastfetch >/dev/null && fastfetch
