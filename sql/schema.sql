-- Tablas del enunciado. La aplicación lee este fichero en la opción 1 del menú
-- y ejecuta las sentencias una a una (ver Orders.reset en seminario/orders.py).
-- Todos los dominios son numéricos, salvo la fecha del pedido.

-- Stock (Cproducto, Cantidad). El CHECK impide que el stock sea negativo.
CREATE TABLE STOCK (
    CPRODUCTO NUMBER(9,0) PRIMARY KEY CHECK (CPRODUCTO > 0),
    CANTIDAD NUMBER(9,0) NOT NULL CHECK (CANTIDAD >= 0)
);

-- Pedido (Cpedido, Ccliente, Fecha-pedido)
CREATE TABLE PEDIDO (
    CPEDIDO NUMBER(9,0) PRIMARY KEY CHECK (CPEDIDO > 0),
    CCLIENTE NUMBER(9,0) NOT NULL CHECK (CCLIENTE > 0),
    FECHA_PEDIDO DATE NOT NULL
);

-- Detalle-Pedido (Cpedido, Cproducto, Cantidad): clave primaria compuesta y
-- dos claves externas, una a PEDIDO y otra a STOCK.
CREATE TABLE DETALLE_PEDIDO (
    CPEDIDO NUMBER(9,0),
    CPRODUCTO NUMBER(9,0),
    CANTIDAD NUMBER(9,0) NOT NULL CHECK (CANTIDAD > 0),
    PRIMARY KEY (CPEDIDO, CPRODUCTO),
    FOREIGN KEY (CPEDIDO) REFERENCES PEDIDO(CPEDIDO),
    FOREIGN KEY (CPRODUCTO) REFERENCES STOCK(CPRODUCTO)
);
