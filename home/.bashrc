#
# ~/.bashrc
#

# Added by Antigravity CLI installer
export PATH="/home/w0lf/.local/bin:$PATH"

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

alias ls='ls --color=auto'
alias grep='grep --color=auto'
# Cyber-Brutalist Mainframe Prompt (Titanium Monolith)
PS1='\[\e[38;2;110;110;110m\]┌──[\[\e[38;2;240;240;240m\]\u@\h\[\e[38;2;110;110;110m\]]──[\[\e[38;2;160;160;160m\]\w\[\e[38;2;110;110;110m\]]\n└──╼ \[\e[38;2;240;240;240m\]\$ \[\e[0m\]'




# Fastfetch ao abrir o terminal
command -v fastfetch >/dev/null && fastfetch
