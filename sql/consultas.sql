-- Consultas para la defensa. Ejecutar en SQL Developer o SQL*Plus, en una
-- sesión DISTINTA a la de la aplicación: solo se verá lo confirmado con COMMIT.
SELECT * FROM STOCK ORDER BY CPRODUCTO;
SELECT * FROM PEDIDO ORDER BY CPEDIDO;
SELECT * FROM DETALLE_PEDIDO ORDER BY CPEDIDO, CPRODUCTO;

-- Anexo II del enunciado: si se quedan sesiones colgadas (hay un máximo de 3 o 4
-- por usuario), se listan y se matan las que tengan STATUS INACTIVE:
--   SET SERVEROUTPUT ON
--   SELECT * FROM mis_sesiones;
--   EXECUTE mata_sesion(<SID>, <SERIAL#>);
