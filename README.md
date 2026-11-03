# Seminario 1 DDSI — subgrupo D2

Aplicación de consola en **Python + ODBC + Oracle**, con los menús del enunciado,
10 productos predefinidos y gestión explícita de transacciones.

Integrantes: Julio, Juanjo, Jesús, Laura y David.

## Compartir y trabajar desde GitHub

Repositorio: [juliocmpc2005/seminario-ddsi-d2](https://github.com/juliocmpc2005/seminario-ddsi-d2).
El código se puede clonar con:

```sh
git clone https://github.com/juliocmpc2005/seminario-ddsi-d2.git
cd seminario-ddsi-d2
```

En otro equipo, sigue la instalación reproducible descrita más abajo antes de
arrancar. Cada persona configura su propia cuenta Oracle en `config.ini`.
La configuración personal y las contraseñas quedan fuera del repositorio.

La [versión v0.1.0](https://github.com/juliocmpc2005/seminario-ddsi-d2/releases/tag/v0.1.0)
incluye el ZIP y la memoria PDF. La memoria aún necesita que el grupo complete el
reparto real de trabajo antes de entregar en Prado.

## Arranque en este Mac

El entorno ya está instalado dentro del proyecto. Abre `Configurar_cuenta.command`
para guardar tu **usuario Oracle** y comprobar el acceso. No se guarda la contraseña.
Después abre `Iniciar.command` o ejecuta:

```sh
./ejecutar.sh
```

La opción 1 borra y vuelve a crear **STOCK, PEDIDO y DETALLE_PEDIDO** de tu esquema.
Exige escribir `BORRAR`. Oracle confirma el DDL implícitamente: este reinicio no se
puede deshacer. No lo ejecutes en un esquema donde debas conservar esas tablas.

Para consultar los cambios desde otra sesión, abre `Consultar.command` en otra
ventana. También puedes usar SQL*Plus, ya instalado:

```sh
.local/instantclient/sqlplus /nolog
```

En SQL*Plus escribe `CONNECT tu_usuario@//oracle0.ugr.es:1521/practbd` y proporciona
la contraseña cuando la pida. Después ejecuta `@sql/consultas.sql` y termina con
`EXIT ROLLBACK`. Hay un límite de sesiones en la UGR: cierra los clientes al acabar.

## Cuenta Oracle y red

La conexión apunta a `oracle0.ugr.es`, puerto `1521`, servicio `practbd`.
Usa Eduroam o la VPN de la UGR cuando corresponda. Según el anexo I del enunciado,
el usuario inicial es el DNI sin letra final, cambiando el primer dígito por una
`x` minúscula; la contraseña inicial coincide con ese usuario, si no se ha cambiado.
Ejemplo ficticio: `12345678Z` → `x2345678`. La cuenta Oracle puede ser distinta del
usuario del correo UGR. Si cambiaste la contraseña y la olvidaste, consulta al profesor.

`config.ini` contiene solo datos de conexión y el usuario. Puedes editarlo o usar
`Configurar_cuenta.command`. La contraseña se solicita con `getpass`, con entrada
oculta. No la pongas en argumentos, código, documentación ni en el ZIP.
El controlador Oracle ODBC instalado no admite punto y coma ni saltos de línea en
los valores de conexión; la aplicación los detecta antes de conectar.

## Instalación reproducible en otro Mac Apple Silicon

Requiere Python 3.11 o posterior, Homebrew y acceso a Internet:

```sh
chmod +x *.sh *.command
./configurar.sh
./ejecutar.sh --comprobar
```

El instalador crea `.venv`, instala `pyodbc==5.3.0`, instala unixODBC si falta,
descarga Oracle Instant Client **Basic + ODBC + SQL*Plus 23.26.3.0.0** y verifica sus
SHA256 publicados por Oracle. Las librerías y el registro ODBC quedan en `.local`;
no se modifica el registro ODBC global ni la configuración de tu shell.

Para Windows/Linux/macOS Intel: instala Python y unixODBC (en Unix), Oracle Instant
Client Basic y ODBC para tu arquitectura, y registra el driver siguiendo las
instrucciones de Oracle. Crea un entorno con `python -m venv .venv`, instala
`pip install -r requirements.txt`, copia `config.example.ini` a `config.ini` y
rellena `usuario` y el nombre de `driver` que muestre `pyodbc.drivers()`.
Ejecuta `python -m seminario` desde el entorno. En Windows, activa el entorno con
`.venv\Scripts\activate` y usa el administrador ODBC de la misma arquitectura que
Python. También puedes indicar la ruta/nombre del controlador mediante
`ORACLE_ODBC_DRIVER`. El instalador automático está limitado a macOS ARM64.

## Comprobación

```sh
.venv/bin/python -m unittest discover -s tests -v
./ejecutar.sh --comprobar
./ejecutar.sh --probar-oracle
```

Las 12 pruebas locales usan SQLite exclusivamente como soporte de pruebas de la
lógica, sin cambiar el SGBD de la aplicación. No acreditan por sí solas el
funcionamiento de Oracle/ODBC. La prueba Oracle necesita credenciales válidas y
abre dos sesiones; crea tablas con un prefijo aleatorio `T1xxxxxx_`, comprueba
aislamiento, commit, rollback, savepoints y errores SQL, y las elimina al terminar.
No utiliza las tablas de la aplicación. Un éxito queda registrado sin credenciales
en `.local/oracle-validation.json`. No se ejecuta automáticamente al arrancar.

## Código y defensa

- `seminario/db.py`: configuración, conexión ODBC, consultas e impresión.
- `seminario/orders.py`: creación de tablas y ciclo de vida de cada pedido.
- `seminario/__main__.py`: menús y cierre de la conexión.
- `sql/schema.sql`: plantilla DDL que carga la aplicación; `{prefix}` se sustituye
  por vacío en ejecución normal y por un prefijo aislado en las pruebas Oracle.
- `docs/DEFENSA.md`: demostración paso a paso y explicación de las transacciones.
- `docs/equipo.json`: integrantes, subgrupo y reparto real pendiente de completar.

Se acumulan las cantidades cuando se añade el mismo producto varias veces. Se
permiten pedidos sin detalles porque el enunciado no exige al menos uno. Todos
los códigos y cantidades se validan como enteros positivos de hasta 9 cifras;
el stock puede quedar a cero. Las sentencias DML usan parámetros ODBC `?`.

## Memoria y ZIP de entrega

Completa el reparto real en `docs/equipo.json`. Para regenerar memoria y ZIP:

```sh
.venv/bin/python -m pip install -r requirements-docs.txt
.venv/bin/python scripts/preparar_entrega.py
```

Se generan `docs/Memoria_D2.pdf` y `entrega/Seminario1_DDSI_D2.zip`, con fuentes,
documentación y una configuración vacía de usuario. Se excluyen el entorno,
librerías descargadas, cachés, la configuración personal y credenciales.
El documento indica de forma explícita lo que queda pendiente; no atribuye tareas
al grupo sin que se haya confirmado el reparto. La entrega por Prado es manual.

## Fuentes

Implementación nueva preparada con asistencia de Codex para este enunciado;
no se han reutilizado proyectos de otros cursos. Bibliotecas de terceros:
pyodbc (MIT), unixODBC y Oracle Instant Client con sus licencias propias; ReportLab
se utiliza solo para generar la memoria. Referencias de documentación, no código
copiado de otras entregas:

- Enunciado `Seminario1_DDSI_2026_2027.pdf`, páginas de implementación y anexos.
- [Oracle Instant Client ARM64: paquetes, instalación y sumas SHA256](https://www.oracle.com/database/technologies/instant-client/macos-arm64-downloads.html).
- [pyodbc: conexiones y transacciones](https://github.com/mkleehammer/pyodbc/wiki/Connection).
- [Oracle ODBC: formato de la cadena de conexión](https://docs.oracle.com/en/database/oracle/oracle-database/19/adfns/odbc-driver.html).
- [Oracle: SAVEPOINT](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/SAVEPOINT.html).
- [Oracle: ROLLBACK](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/ROLLBACK.html).
- [Oracle: transacciones y commits implícitos del DDL](https://docs.oracle.com/en/database/oracle/oracle-database/21/cncpt/transactions.html).
