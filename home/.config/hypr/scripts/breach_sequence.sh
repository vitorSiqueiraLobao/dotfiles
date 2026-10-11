#!/usr/bin/env bash
# SEQUENCE REQUIRED TO UPLOAD do hyprlock (Breach Protocol)
r="<span foreground='#ff1f3d'>"; c="<span foreground='#00f0ff'>"; m="<span foreground='#7a6f73'>"; e="</span>"
cat <<OUT
<span line_height='1.6'>${r}55 1C     ${e}  ${c}DATAMINE_V1${e}
${m}           extrai dados da sessão${e}
${r}1C 1C E9  ${e}  ${c}SESSION_UNLOCK${e}
${m}           libera o desktop${e}
${r}BD E9 55  ${e}  ${c}ROOT_ACCESS${e}
${m}           acesso total ao ARES${e}</span>
OUT
