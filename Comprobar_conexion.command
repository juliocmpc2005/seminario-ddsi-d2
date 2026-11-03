#!/bin/sh
cd "$(dirname "$0")" || exit 1
./ejecutar.sh --comprobar
printf '\nPulsa Intro para cerrar.'
read -r cerrar
