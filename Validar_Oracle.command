#!/bin/sh
# Validación automática de las transacciones en Oracle (reinicia las tablas).
# Doble clic desde Finder: abre una Terminal y ejecuta lo siguiente.
cd "$(dirname "$0")" || exit 1
./ejecutar.sh --probar-oracle
printf '\nPulsa Intro para cerrar.'
read -r cerrar
