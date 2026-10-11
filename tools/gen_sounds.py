#!/usr/bin/env python3
# ARES // gerador do pacote de efeitos sonoros (sintetizados, sem samples de terceiros)
# Gera WAVs curtos estilo interface cyberpunk em home/.config/ares/sounds/.
# Uso: python3 tools/gen_sounds.py
# Para usar outros sons (ex.: do jogo, só na sua máquina), coloque arquivos com os
# mesmos nomes em ~/.local/share/ares/sounds/ — eles têm prioridade e não vão pro repo.

import math
import os
import random
import struct
import wave

RATE = 48000
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "home", ".config", "ares", "sounds")
random.seed(2077)


def tone(freq, dur, wave_type="sine", vol=0.5, attack=0.002, decay=None, sweep_to=None):
    """Oscilador simples com envelope (ataque linear + queda exponencial)."""
    n = int(RATE * dur)
    out, phase = [], 0.0
    decay = decay or dur / 4
    for i in range(n):
        t = i / RATE
        f = freq if sweep_to is None else freq + (sweep_to - freq) * (i / n)
        phase += 2 * math.pi * f / RATE
        if wave_type == "sine":
            s = math.sin(phase)
        elif wave_type == "square":
            s = 1.0 if math.sin(phase) >= 0 else -1.0
        elif wave_type == "saw":
            s = 2 * ((phase / (2 * math.pi)) % 1) - 1
        else:  # noise
            s = random.uniform(-1, 1)
        env = min(1.0, t / attack) * math.exp(-t / decay)
        out.append(s * env * vol)
    return out


def mix(*tracks, offsets=None):
    offsets = offsets or [0] * len(tracks)
    length = max(int(o * RATE) + len(t) for t, o in zip(tracks, offsets))
    out = [0.0] * length
    for t, o in zip(tracks, offsets):
        start = int(o * RATE)
        for i, s in enumerate(t):
            out[start + i] += s
    return out


def crush(samples, bits=6, hold=3):
    """Bit-crush + sample-and-hold: o 'digital sujo' das interfaces do jogo."""
    q = 2 ** (bits - 1)
    out, last = [], 0.0
    for i, s in enumerate(samples):
        if i % hold == 0:
            last = round(s * q) / q
        out.append(last)
    return out


def stutter(samples, chunk=0.012, gaps=(2, 5)):
    """Cortes rápidos (glitch)."""
    n = int(RATE * chunk)
    out = []
    for i in range(0, len(samples), n):
        block = samples[i:i + n]
        out.extend([0.0] * len(block) if (i // n) % random.randint(*gaps) == 0 else block)
    return out


def save(name, samples, gain=0.9):
    peak = max(1e-9, max(abs(s) for s in samples))
    k = gain / peak
    os.makedirs(OUT, exist_ok=True)
    with wave.open(os.path.join(OUT, f"{name}.wav"), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s * k)) * 32767)) for s in samples))
    print(f"  {name}.wav  {len(samples) / RATE * 1000:.0f} ms")


# --- Sons --------------------------------------------------------------------
# tecla: clique seco e agudo
save("key", mix(tone(2600, 0.018, "square", 0.4, decay=0.004),
                tone(0, 0.012, "noise", 0.25, decay=0.003)), gain=0.55)
# navegar: bipe curto
save("nav", crush(tone(1500, 0.045, "sine", 0.6, decay=0.012, sweep_to=1300), bits=7), gain=0.6)
# selecionar/executar: dois tons subindo
save("select", crush(mix(tone(900, 0.06, "square", 0.35, decay=0.02),
                         tone(1800, 0.09, "square", 0.35, decay=0.03), offsets=[0, 0.055]), bits=6), gain=0.7)
# abrir painel: varredura subindo com glitch
save("open", stutter(crush(mix(tone(260, 0.18, "saw", 0.4, decay=0.08, sweep_to=2200),
                               tone(0, 0.18, "noise", 0.12, decay=0.05)), bits=5, hold=4)), gain=0.65)
# fechar painel: varredura descendo
save("close", crush(mix(tone(1800, 0.14, "saw", 0.4, decay=0.05, sweep_to=220),
                        tone(0, 0.08, "noise", 0.1, decay=0.02)), bits=5, hold=4), gain=0.55)
# erro/negado: zumbido grave picotado
save("error", stutter(crush(mix(tone(140, 0.28, "square", 0.5, decay=0.15),
                                tone(147, 0.28, "square", 0.4, decay=0.15)), bits=4, hold=6),
                      chunk=0.03, gaps=(2, 3)), gain=0.6)
# código escolhido na matriz: bipe agudo e limpo
save("pick", mix(tone(2400, 0.05, "sine", 0.5, decay=0.015),
                 tone(4800, 0.03, "sine", 0.15, decay=0.008)), gain=0.6)
# BREACH SUCCESSFUL: arpejo subindo + brilho
notes = [659.3, 830.6, 987.8, 1318.5]  # E5 G#5 B5 E6
arp = [tone(f, 0.32, "square", 0.25, decay=0.12) for f in notes]
shine = tone(2637, 0.6, "sine", 0.12, attack=0.05, decay=0.3)
save("success", crush(mix(*arp, shine, offsets=[0, 0.07, 0.14, 0.21, 0.21]), bits=7, hold=2), gain=0.75)
# notificação: dois bipes descendo
save("notify", crush(mix(tone(1760, 0.07, "square", 0.3, decay=0.025),
                         tone(1320, 0.11, "square", 0.3, decay=0.04), offsets=[0, 0.08]), bits=6), gain=0.6)
# notificação crítica: alarme em três pulsos
pulse = tone(980, 0.09, "square", 0.4, decay=0.05)
save("alert", crush(mix(pulse, pulse, pulse, offsets=[0, 0.14, 0.28]), bits=5, hold=3), gain=0.7)
# bloquear: queda com glitch + baque grave
save("lock", mix(stutter(crush(tone(1600, 0.22, "saw", 0.35, decay=0.1, sweep_to=120), bits=5, hold=5)),
                 tone(60, 0.35, "sine", 0.6, attack=0.01, decay=0.12), offsets=[0, 0.12]), gain=0.7)
# slider do mixer: tique bem leve
save("tick", tone(3200, 0.012, "sine", 0.3, decay=0.003), gain=0.35)
