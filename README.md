# Seminario 1 DDSI — subgrupo D2

Aplicación de consola en **Python + ODBC + Oracle** con los menús del enunciado,
10 productos predefinidos y control explícito de transacciones
(`COMMIT`, `ROLLBACK`, `SAVEPOINT`).

Integrantes: Julio, Juanjo, Jesús, Laura y David.
Repositorio: <https://github.com/juliocmpc2005/seminario-ddsi-d2>

## Qué hay en cada fichero

| Fichero | Contenido |
| --- | --- |
| `seminario/db.py` | Conexión ODBC (autocommit desactivado), consultas y mostrar tablas. |
| `seminario/orders.py` | Creación de tablas y **todas las transacciones** del pedido. Es el fichero importante. |
| `seminario/__main__.py` | Menú principal, submenú del pedido y cierre de la conexión. |
| `sql/schema.sql` | Los tres `CREATE TABLE`. |
| `sql/consultas.sql` | Consultas para el cliente de consulta de la defensa. |
| `tests/test_orders.py` | Pruebas automáticas de la lógica (con SQLite, sin red). |
| `tests/oracle_integration.py` | Validación real en Oracle con dos sesiones. |
| `docs/GUIA_DE_USO.html` / `.pdf` | Guía de uso paso a paso, con capturas, y estructura del proyecto. |
| `docs/DEFENSA.md` | Guion de la demostración y preguntas habituales. |
| `docs/equipo.json` | Integrantes y reparto de trabajo (va a la memoria). |
| `scripts/` | Instalación del driver de Oracle, configuración del usuario y generación de memoria + ZIP. |
| `configurar.sh`, `ejecutar.sh`, `*.command` | Instalación y arranque. |

## Instalación (una vez por equipo)

En un Mac con Apple Silicon, con Python 3.11 o posterior y Homebrew:

```sh
./configurar.sh
```

Instala unixODBC, crea el entorno `.venv` con `pyodbc`, descarga Oracle Instant
Client (Basic + ODBC + SQL*Plus) comprobando sus SHA256 y lo deja en `.local`.
No modifica nada fuera de la carpeta del proyecto.

Después, cada persona guarda **su** usuario de Oracle (doble clic en
`Configurar_cuenta.command`, o editando `config.ini`). Según el anexo I del
enunciado, el usuario es el DNI sin la letra y con el primer dígito cambiado por
una `x` minúscula, y la contraseña inicial es ese mismo usuario. La contraseña
no se guarda en ningún sitio: se pide al arrancar. Hay que estar en Eduroam o
con la VPN de la UGR.

En Windows, Linux o Mac Intel: instalar Python, el Driver Manager ODBC
(unixODBC en Linux/Mac), Oracle Instant Client Basic + ODBC y registrar el
driver según las instrucciones de Oracle; después `python -m venv .venv`,
`pip install -r requirements.txt`, copiar `config.example.ini` a `config.ini`
y poner en `driver` el nombre que muestre `pyodbc.drivers()`. La aplicación se
arranca con `python -m seminario`.

## Uso

| Qué | Doble clic | Terminal |
| --- | --- | --- |
| Aplicación | `Iniciar.command` | `./ejecutar.sh` |
| Cliente de consulta (otra sesión) | `Consultar.command` | `./ejecutar.sh --consulta` |
| Probar la conexión | — | `./ejecutar.sh --comprobar` |
| Validación automática en Oracle | `Validar_Oracle.command` | `./ejecutar.sh --probar-oracle` |

La opción 1 del menú (y la validación automática) **borra y vuelve a crear**
`STOCK`, `PEDIDO` y `DETALLE_PEDIDO` en tu cuenta. Pide escribir `BORRAR` porque
en Oracle el DDL no se puede deshacer.

Como cliente de consulta también sirven SQL Developer o SQL*Plus
(`.local/instantclient/sqlplus /nolog`, luego
`CONNECT tu_usuario@//oracle0.ugr.es:1521/practbd` y `@sql/consultas.sql`).
El servidor admite 3 o 4 sesiones por usuario: cierra los clientes al acabar
(anexo II del enunciado; los comandos están al final de `sql/consultas.sql`).

## Pruebas

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Usan SQLite solo como banco de pruebas de la lógica; no sustituyen a la
validación en Oracle (`./ejecutar.sh --probar-oracle`).

## Decisiones

- Añadir dos veces el mismo producto suma la cantidad en una única línea (la
  clave primaria de Detalle-Pedido es pedido + producto).
- Se puede finalizar un pedido sin detalles: el enunciado no lo prohíbe.
- Códigos y cantidades son enteros positivos de hasta 9 cifras; el stock puede
  quedar a cero pero nunca negativo.
- Los datos van siempre como parámetros `?`, nunca concatenados en el SQL.

## Entrega

1. Rellenar el reparto real de trabajo en `docs/equipo.json`.
2. Generar memoria y ZIP:

   ```sh
   .venv/bin/python -m pip install -r requirements-docs.txt
   .venv/bin/python scripts/preparar_entrega.py
   ```

3. Subir a Prado `entrega/Seminario1_DDSI_D2.zip` (contiene la memoria PDF y el
   código, sin configuración personal ni contraseñas).

## Fuentes

Código escrito para este enunciado con asistencia de herramientas de IA (Codex
y Claude Code); no se ha reutilizado código de otros
cursos. Bibliotecas: pyodbc (MIT), unixODBC, Oracle Instant Client y ReportLab
(solo para generar la memoria). Documentación consultada:

- Enunciado `Seminario1_DDSI_2026_2027.pdf` y sus anexos.
- [pyodbc: conexiones y transacciones](https://github.com/mkleehammer/pyodbc/wiki/Connection)
- [Oracle ODBC: cadena de conexión](https://docs.oracle.com/en/database/oracle/oracle-database/19/adfns/odbc-driver.html)
- [Oracle: SAVEPOINT](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/SAVEPOINT.html)
- [Oracle: ROLLBACK](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/ROLLBACK.html)
- [Oracle: transacciones y COMMIT implícito del DDL](https://docs.oracle.com/en/database/oracle/oracle-database/21/cncpt/transactions.html)
- [Oracle Instant Client para macOS ARM64](https://www.oracle.com/database/technologies/instant-client/macos-arm64-downloads.html)
