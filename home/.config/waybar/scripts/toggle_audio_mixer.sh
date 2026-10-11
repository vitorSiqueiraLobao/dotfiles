#!/usr/bin/env bash
# Toggle pavucontrol dropdown panel
if pgrep -x "pavucontrol" >/dev/null; then
    pkill -x "pavucontrol"
else
    nohup pavucontrol >/dev/null 2>&1 &
    disown
fi
