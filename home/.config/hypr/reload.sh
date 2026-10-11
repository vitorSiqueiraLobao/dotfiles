#!/usr/bin/env bash
hyprctl reload
pkill -x waybar 2>/dev/null
sleep 0.2
nohup waybar >/dev/null 2>&1 &
pkill -x hyprpaper 2>/dev/null
sleep 0.2
nohup hyprpaper >/dev/null 2>&1 &
disown -a 2>/dev/null
