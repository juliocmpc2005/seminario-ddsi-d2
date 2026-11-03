# Demostración y explicación — D2

Todo el grupo debe poder explicar todos los módulos. Estos pasos permiten mostrar
las operaciones exigidas desde la aplicación y desde un cliente independiente.

## Demostración

1. Ejecuta la aplicación y usa opción 1; escribe `BORRAR`. Comprueba las 10 filas
   de Stock y las otras dos tablas vacías. Abre `Consultar.command` o SQL*Plus
   en una segunda sesión con la misma cuenta.
2. Inicia pedido 1001, cliente 20, fecha del día. Añade producto 1, cantidad 7.
   La aplicación ve stock 93 y el pedido; el observador sigue viendo stock 100
   y ningún pedido. Todavía no ha habido `COMMIT`.
3. Intenta añadir 94 unidades del producto 1. Se rechaza y se conserva el detalle
   previo de 7 unidades. Prueba también un producto inexistente.
4. Elimina todos los detalles con opción 2. El stock vuelve a 100, desaparecen
   los detalles y se mantiene la cabecera del pedido 1001.
5. Añade 5 unidades del producto 1 y otras 3 del mismo. Hay un detalle de 8 unidades
   y stock 92. Finaliza con opción 4. Actualiza el observador: ahora ve los datos.
6. Inicia pedido 1002, añade 2 unidades del producto 1 y cancela con opción 3.
   Stock vuelve a 92 y no queda el pedido 1002 ni sus detalles. Se muestran las tablas.
7. Intenta reutilizar el código 1001: el sistema rechaza la clave duplicada y
   conserva el pedido que ya estaba confirmado.
8. Inicia otro pedido, añade un detalle y pulsa Ctrl+C. Comprueba en el observador
   que el pedido pendiente no se ha confirmado. Cierra ambos clientes al terminar.

## Qué sucede en cada transacción

La conexión se abre con `autocommit=False`. El primer `INSERT` en Pedido inicia
la transacción de Oracle. Inmediatamente después se establece
`SAVEPOINT pedido_sin_detalles`. Ese punto deja la cabecera dentro de la
transacción pero aún no persistida.

Cada añadido establece `SAVEPOINT antes_detalle`. Un `UPDATE` condicional descuenta
stock solo si hay cantidad suficiente. Después se inserta el detalle, o se acumula
si ese producto ya figura en el pedido. Si ocurre un fallo, `ROLLBACK TO antes_detalle`
deshace tanto el descuento como cualquier cambio de esa línea; los detalles previos
siguen pendientes. No hay commit dentro de `add` ni al mostrar las tablas.

Eliminar todos los detalles ejecuta `ROLLBACK TO pedido_sin_detalles`: repone todo
el stock de ese pedido y conserva la cabecera. La transacción continúa activa y el
mismo savepoint puede volver a utilizarse. No basta con borrar filas de detalles,
porque eso no repondría los descuentos de stock.

Cancelar usa `connection.rollback()`: elimina la cabecera y todos sus detalles y
repone el stock. Finalizar usa `connection.commit()`: confirma todos los cambios
de forma conjunta. Una vez confirmado, un rollback posterior no los deshace.

## Preguntas habituales

- **¿Por qué no activar autocommit?** Confirmaría cada sentencia y rompería la
  atomicidad entre cabecera, detalles y stock.
- **¿Por qué usar la misma conexión?** La transacción pertenece a la sesión;
  otra conexión tendría otra transacción.
- **¿Qué evita vender stock negativo?** La condición `CANTIDAD >= ?` en el mismo
  UPDATE que descuenta las unidades y la restricción `CHECK (CANTIDAD >= 0)`.
  Oracle coordina el acceso concurrente a las filas modificadas. La lectura
  inicial y un descuento incondicional separado permitirían carreras.
- **¿Se bloquea toda la base de datos?** Oracle bloquea las filas modificadas
  para coordinar escrituras; otras sesiones pueden consultar los datos confirmados.
  También existen bloqueos de tabla relacionados con operaciones de esquema.
- **¿Puede un error SQL dejar stock descontado?** Sí si el programa solo captura
  la excepción. Aquí se vuelve explícitamente al savepoint para mantener la línea
  atómica. No se supone que todo error SQL cancele toda la transacción.
- **¿Por qué el reinicio está fuera del alta?** El DDL de Oracle hace commits
  implícitos. Ejecutarlo en mitad de un pedido podría confirmar datos pendientes.
- **¿Cómo se cierra?** Se solicita un rollback explícito de lo pendiente y se
  cierra la conexión incluso ante EOF o Ctrl+C. Los cursores se cierran sin usar
  un contexto de conexión que pueda confirmar cambios automáticamente.
- **¿Qué es ODBC aquí?** Python llama a pyodbc; pyodbc usa unixODBC, que carga
  el controlador Oracle. Este se conecta al listener y al servicio `practbd`.
- **¿Por qué los valores usan `?`?** El driver enlaza los datos separados del
  texto SQL. No se concatenan códigos o cantidades introducidos por el usuario.

## Antes de entregar

Completa el reparto real en `docs/equipo.json`. Si necesitas repetir la validación,
ejecuta `Validar_Oracle.command`. Regenera el PDF y el ZIP con
`.venv/bin/python scripts/preparar_entrega.py`. Practicad la demostración entre
todos y subid el ZIP a Prado. La memoria debe reflejar el trabajo real de cada
persona, incluida la revisión y comprensión del código asistido.
