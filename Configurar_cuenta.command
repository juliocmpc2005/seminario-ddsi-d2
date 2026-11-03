#!/bin/sh
cd "$(dirname "$0")" || exit 1
.venv/bin/python scripts/configure_account.py && ./ejecutar.sh --comprobar
printf '\nPulsa Intro para cerrar.'
read -r cerrar
