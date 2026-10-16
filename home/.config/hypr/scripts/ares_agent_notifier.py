#!/usr/bin/env python3
# ==============================================================================
# ARES // AGENT TERMINAL NOTIFIER DAEMON
# Monitora os logs do Antigravity CLI e dispara alertas sonoros e visuais no HUD
# NO EXATO MOMENTO em que o terminal estiver aguardando aprovação ("OK") do usuário.
# ==============================================================================

import os
import re
import sys
import time
import subprocess

# Adiciona o diretório dos scripts para importar ares_sfx se disponível
sys.path.insert(0, os.path.expanduser("~/.config/hypr/scripts"))
try:
    import ares_sfx
except ImportError:
    ares_sfx = None

CLI_LOG_SYMLINK = os.path.expanduser("~/.gemini/antigravity-cli/cli.log")
LOG_DIR = os.path.expanduser("~/.gemini/antigravity-cli/log")

RE_CONFIRMATION = re.compile(r'Surfacing tool confirmation:\s*"([^"]+)"')
RE_QUESTION = re.compile(r'Surfacing ask_question')

def trigger_alert(title, body):
    # Envia notificação D-Bus para o ares-notifyd
    # Nível normal toca notify.wav (som padrão do sistema ARES) e expira automaticamente após 5 segundos
    try:
        subprocess.run([
            "notify-send",
            "-a", "ARES // TERMINAL",
            "-u", "normal",
            "-t", "5000",
            "-i", "utilities-terminal",
            title,
            body
        ], check=False)
    except Exception:
        pass

def get_current_log_file():
    if os.path.islink(CLI_LOG_SYMLINK):
        return os.path.realpath(CLI_LOG_SYMLINK)
    if os.path.exists(CLI_LOG_SYMLINK):
        return CLI_LOG_SYMLINK
    # Fallback: pega o arquivo de log mais recente no diretório de logs
    if os.path.isdir(LOG_DIR):
        files = [os.path.join(LOG_DIR, f) for f in os.listdir(LOG_DIR) if f.startswith("cli-")]
        if files:
            return max(files, key=os.path.getmtime)
    return None

def main():
    current_path = None
    file_obj = None
    last_alert_time = 0.0

    while True:
        target_path = get_current_log_file()

        # Se o arquivo de log mudou (nova sessão do agy ou reinício do CLI)
        if target_path and target_path != current_path:
            if file_obj:
                try:
                    file_obj.close()
                except Exception:
                    pass
            current_path = target_path
            try:
                file_obj = open(current_path, "r", encoding="utf-8", errors="replace")
                # Vai para o fim do arquivo para não disparar alertas de logs antigos
                file_obj.seek(0, os.SEEK_END)
            except Exception:
                file_obj = None
                time.sleep(1)
                continue

        if not file_obj:
            time.sleep(1)
            continue

        line = file_obj.readline()
        if not line:
            # Verifica se o link do log apontou para um novo arquivo
            if os.path.islink(CLI_LOG_SYMLINK):
                real_target = os.path.realpath(CLI_LOG_SYMLINK)
                if real_target != current_path:
                    continue
            time.sleep(0.15)
            continue

        now = time.monotonic()
        # Evita flood de notificações consecutivas em menos de 1.5s
        if now - last_alert_time < 1.5:
            continue

        # Detecta quando o terminal abre a tela pedindo OK/Aprovação de comando
        m_conf = RE_CONFIRMATION.search(line)
        if m_conf:
            tool_name = m_conf.group(1)
            last_alert_time = now
            trigger_alert(
                "TERMINAL // OK REQUERIDO",
                f"O terminal está aguardando sua autorização para prosseguir com [{tool_name}]."
            )
            continue

        # Detecta quando o assistente abre o modal de pergunta (ask_question)
        if RE_QUESTION.search(line):
            last_alert_time = now
            trigger_alert(
                "TERMINAL // RESPOSTA REQUERIDA",
                "O assistente aguarda sua seleção ou resposta no terminal."
            )
            continue

if __name__ == "__main__":
    main()
