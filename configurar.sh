#!/bin/sh
# Instalación del proyecto en un equipo nuevo. Se ejecuta una sola vez.
set -eu                 # Parar ante cualquier error o variable sin definir.
cd "$(dirname "$0")"    # Trabajar siempre desde la carpeta del proyecto.

# El instalador automático de Oracle solo está preparado para Mac con Apple Silicon.
if [ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = arm64 ]; then
    mac_arm=si
else
    mac_arm=no
fi

# 1. Driver Manager: unixODBC (odbcinst es uno de sus programas).
if [ "$mac_arm" = si ] && ! command -v odbcinst >/dev/null 2>&1; then
    HOMEBREW_NO_AUTO_UPDATE=1 brew install unixodbc
fi

# 2. Entorno virtual de Python con pyodbc, aislado del Python del sistema.
if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.txt

# 3. Configuración personal (sin contraseña) a partir de la plantilla.
if [ ! -f config.ini ]; then
    cp config.example.ini config.ini
fi

# 4. Driver ODBC de Oracle (Instant Client), dentro de la carpeta .local.
if [ "$mac_arm" = si ]; then
    .venv/bin/python scripts/install_oracle_macos.py
else
    echo 'Instala Oracle Instant Client Basic + ODBC y registra su driver; consulta README.md.'
fi
