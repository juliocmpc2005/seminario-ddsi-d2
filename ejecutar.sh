#!/bin/sh
# Arranca la aplicación con el Python del proyecto y el ODBC local configurado.
# Uso: ./ejecutar.sh [--consulta | --comprobar | --probar-oracle]
set -eu                 # Parar ante cualquier error o variable sin definir.
cd "$(dirname "$0")"    # Trabajar siempre desde la carpeta del proyecto.

if [ ! -x .venv/bin/python ]; then
    echo 'Primero ejecuta ./configurar.sh'
    exit 1
fi

# Si el Instant Client está instalado dentro del proyecto (macOS), se registra
# su driver en el Driver Manager (unixODBC) con el nombre "OracleSeminario",
# que es el que usa config.ini. El registro es el fichero odbcinst.ini; se
# escribe en cada arranque con la ruta actual, para que siga funcionando si la
# carpeta del proyecto se mueve de sitio.
if [ -d .local/instantclient ]; then
    printf '[OracleSeminario]\nDescription=Oracle Instant Client\nDriver=%s\n' \
        "$PWD/.local/instantclient/libsqora.dylib.23.1" > .local/odbcinst.ini
    # Estas variables hacen que unixODBC lea ESE fichero y no la configuración
    # global del sistema.
    export ODBCSYSINI="$PWD/.local"
    export ODBCINSTINI=odbcinst.ini
fi

# "python -m seminario" ejecuta seminario/__main__.py; "$@" le pasa las opciones.
exec .venv/bin/python -m seminario "$@"
