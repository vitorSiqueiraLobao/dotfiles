#!/usr/bin/env bash
# Quick Audio Output Switcher using pactl + wofi
SINKS=$(pactl list sinks | awk '/Sink #/{id=$2} /Description:/{sub(/^[ \t]*Description: /, ""); print id " │ " $0}')

if [ -z "$SINKS" ]; then
    exit 0
fi

CHOSEN=$(echo "$SINKS" | wofi --dmenu --prompt "SELECT_OUTPUT >" --width 500 --height 180 --location top_right --xoffset -20 --yoffset 40)

if [ -n "$CHOSEN" ]; then
    SINK_ID=$(echo "$CHOSEN" | grep -oE '[0-9]+' | head -n 1)
    if [ -n "$SINK_ID" ]; then
        pactl set-default-sink "$SINK_ID"
        which notify-send >/dev/null && notify-send "AUDIO // OUTPUT CHANGED" "Default output set to Sink #$SINK_ID"
    fi
fi
