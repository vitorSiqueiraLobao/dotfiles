#!/usr/bin/env bash

# Light/Dark mode toggle
# Usage: theme_toggle.sh         -> JSON status for Waybar
#        theme_toggle.sh toggle  -> switch mode and refresh the module

SCHEME=$(gsettings get org.gnome.desktop.interface color-scheme)

if [ "$1" = "toggle" ]; then
    if [ "$SCHEME" = "'prefer-dark'" ]; then
        gsettings set org.gnome.desktop.interface color-scheme 'prefer-light'
        gsettings set org.gnome.desktop.interface gtk-theme 'Adwaita'
    else
        gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'
        gsettings set org.gnome.desktop.interface gtk-theme 'Adwaita-dark'
    fi
    pkill -RTMIN+8 waybar
    exit 0
fi

# JSON output for Waybar
if [ "$SCHEME" = "'prefer-dark'" ]; then
    ICON=$(printf '\U000F0594')   # nf-md-weather_night
    echo "{\"text\": \"$ICON\", \"tooltip\": \"Modo escuro — clique para claro\", \"class\": \"dark\"}"
else
    ICON=$(printf '\U000F05A8')   # nf-md-white_balance_sunny
    echo "{\"text\": \"$ICON\", \"tooltip\": \"Modo claro — clique para escuro\", \"class\": \"light\"}"
fi
