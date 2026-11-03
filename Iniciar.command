#!/bin/sh
cd "$(dirname "$0")" || exit 1
./ejecutar.sh
printf '\nPulsa Intro para cerrar.'
read -r cerrar
