#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
    echo 'Primero ejecuta ./configurar.sh'
    exit 1
fi
if [ -f .local/odbcinst.ini ]; then
    export ODBCSYSINI="$PWD/.local"
    export ODBCINSTINI=odbcinst.ini
    export ODBCINI="$PWD/.local/odbc.ini"
fi
exec .venv/bin/python -m seminario "$@"
