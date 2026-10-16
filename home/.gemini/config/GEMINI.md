# Diretrizes de Interação e Notificações (Ambiente ARES)

## Alertas de Notificação para Atenção do Usuário
Sempre que você precisar de uma confirmação, resposta, aprovação ou "OK" do usuário para prosseguir, ou quando finalizar uma tarefa que requer retorno do usuário ao terminal:
1. Dispare uma notificação de sistema executando a ferramenta `run_command` com o comando:
   ```bash
   ares-alert "TERMINAL // OK REQUERIDO" "<breve resumo do que você precisa que o usuário aprove ou responda>"
   ```
2. Isso ativará o HUD de notificações Cyberpunk (ares-notifyd) e reproduzirá o som de alerta (alert.wav / ares_sfx), garantindo que o usuário seja avisado caso esteja em outra janela ou ausente.
