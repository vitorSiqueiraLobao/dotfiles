#!/usr/bin/env python3
"""Filtro "clean" do git: tira "intersystems.servers" do settings.json do VS Code.

Os endereços dos servidores IRIS ficam só no arquivo local; o que vai pro
repositório sai sem eles. Uso: redact_vscode_settings.py < entrada > saída
"""
import re
import sys

text = sys.stdin.read()
m = re.search(r'[ \t]*"intersystems\.servers"\s*:\s*\{', text)
if m:
    depth, i = 1, m.end()
    while depth and i < len(text):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    end = re.compile(r"\s*,?[ \t]*\n").match(text, i)
    text = text[: m.start()] + text[end.end() if end else i :]
sys.stdout.write(text)
