#!/usr/bin/env bash
# Data em português para o hyprlock (o sistema não tem locale pt_BR)
dias=(domingo segunda-feira terça-feira quarta-feira quinta-feira sexta-feira sábado)
meses=(janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro)
echo "${dias[$(date +%w)]}, $(date +%-d) de ${meses[$(( $(date +%-m) - 1 ))]}"
