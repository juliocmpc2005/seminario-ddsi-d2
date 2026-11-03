#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = arm64 ]; then
    if ! command -v odbcinst >/dev/null 2>&1; then
        HOMEBREW_NO_AUTO_UPDATE=1 brew install unixodbc
    fi
fi
if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.txt
if [ ! -f config.ini ]; then
    cp config.example.ini config.ini
fi
if [ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = arm64 ]; then
    .venv/bin/python scripts/install_oracle_macos.py
else
    echo 'Instala Oracle Instant Client Basic + ODBC y registra su driver; consulta README.md.'
fi
