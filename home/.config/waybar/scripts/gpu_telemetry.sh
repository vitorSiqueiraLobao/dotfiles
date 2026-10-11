#!/usr/bin/env bash

# AMD GPU Telemetry
GPU_BUSY=$(cat /sys/class/drm/card1/device/gpu_busy_percent 2>/dev/null || echo "0")
VRAM_USED_B=$(cat /sys/class/drm/card1/device/mem_info_vram_used 2>/dev/null || echo "0")
VRAM_USED_GB=$(awk "BEGIN {printf \"%.1f\", $VRAM_USED_B / 1073741824}")
PWR_U=$(cat /sys/class/drm/card1/device/hwmon/hwmon3/power1_average 2>/dev/null || cat /sys/class/drm/card1/device/hwmon/hwmon3/power1_input 2>/dev/null || echo "0")
PWR_W=$(awk "BEGIN {printf \"%.0f\", $PWR_U / 1000000}")
TEMP_M=$(cat /sys/class/drm/card1/device/hwmon/hwmon3/temp1_input 2>/dev/null || echo "0")
TEMP_C=$(awk "BEGIN {printf \"%.0f\", $TEMP_M / 1000}")

# JSON output for Waybar
# Medidor ASCII de 8 blocos
FILLED=$(( (GPU_BUSY + 6) / 12 )); [ "$FILLED" -gt 8 ] && FILLED=8
BAR="[$(printf '%*s' "$FILLED" '' | sed 's/ /█/g')<span color='#2a4a50'>$(printf '%*s' $((8 - FILLED)) '' | sed 's/ /░/g')</span>]"
TEXT="GPU <span color='#00f0ff'>${BAR}</span> ${GPU_BUSY}% <span color='#7a6f73'>─</span> VRAM ${VRAM_USED_GB}G <span color='#7a6f73'>─</span> ${PWR_W}W"
TOOLTIP="AMD Radeon RX 9070 XT\nGPU Load: ${GPU_BUSY}%\nTemperature: ${TEMP_C}°C\nVRAM: ${VRAM_USED_GB} GB / 16.0 GB\nPower Draw: ${PWR_W} W"

echo "{\"text\": \"$TEXT\", \"tooltip\": \"$TOOLTIP\", \"class\": \"gpu\"}"
