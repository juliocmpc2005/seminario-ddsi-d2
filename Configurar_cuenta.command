#!/bin/sh
# Guarda tu usuario de Oracle en config.ini y comprueba la conexión.
# Doble clic desde Finder: abre una Terminal y ejecuta lo siguiente.
cd "$(dirname "$0")" || exit 1
.venv/bin/python scripts/configure_account.py && ./ejecutar.sh --comprobar
printf '\nPulsa Intro para cerrar.'
read -r cerrar
