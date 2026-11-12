#!/bin/sh
# Arranca la aplicación (menú principal del seminario).
# Doble clic desde Finder: abre una Terminal y ejecuta lo siguiente.
cd "$(dirname "$0")" || exit 1
./ejecutar.sh
printf '\nPulsa Intro para cerrar.'
read -r cerrar
