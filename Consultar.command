#!/bin/sh
# Cliente de consulta en otra sesión: solo ve los datos confirmados (COMMIT).
# Doble clic desde Finder: abre una Terminal y ejecuta lo siguiente.
cd "$(dirname "$0")" || exit 1
./ejecutar.sh --consulta
printf '\nPulsa Intro para cerrar.'
read -r cerrar
