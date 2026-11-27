=====================
Cambio de divisas TPV
=====================

Una ventanilla de cambio dentro del Punto de Venta de Odoo 20: el cliente
trae billetes en una moneda y se lleva billetes en otra, menos una
comisión. Construido sobre POS Multi-Currency Cash, que controla el cajón
de cada divisa, sus tipos de caja y sus monedas y billetes.

Presentación
============

Los comercios de zonas turísticas, hoteles, campings o ciudades
fronterizas reciben a menudo peticiones de cambio de dinero. Con POS
Multi-Currency Cash la caja ya acepta billetes extranjeros y devuelve el
cambio en una moneda extranjera; este módulo añade la operación sin venta:

* el cajero abre la entrada **Cambio de divisas** del menú de la caja,
  elige la moneda recibida y la moneda entregada, e introduce el importe
  recibido, o el importe que el cliente quiere recibir;
* la caja calcula la operación: billetes recibidos al tipo de caja del
  punto de venta (el tipo de compra), billetes entregados al tipo de venta
  de la ventanilla, la comisión de la moneda, el redondeo a las monedas y
  billetes, y lo que contiene el cajón;
* la operación se registra con el cajero y, cuando se requiere, el cliente
  y su documento de identidad, y se imprime un recibo de cambio;
* los dos cajones se mueven: los billetes recibidos entran en el cajón de
  su moneda y los billetes entregados salen del otro, en el diario de
  efectivo de la sesión, con la comisión registrada en una cuenta de
  ingresos dedicada;
* un administrador del Punto de venta puede cancelar una operación errónea
  mientras la sesión está abierta y el cajón aún contiene los billetes
  recibidos;
* las operaciones aparecen en el control de cierre, en el informe
  *Posición de divisas* y en el informe *Detalles de ventas*, en una lista
  con una tabla dinámica de las comisiones y márgenes de tipo, y en un
  registro de cambios que se puede exportar o imprimir para un periodo;
* la tabla de tipos de la ventanilla se puede mostrar e imprimir en la
  caja, o imprimir en PDF;
* varias ventanillas de un mismo establecimiento con licencia pueden
  formar una **casa de cambio**: comparten su licencia, sus reglas de
  identificación y los mismos tipos, y la casa de cambio muestra los
  cajones de cada ventanilla;
* por encima de los umbrales que usted define, el cliente declara el
  origen de los fondos, y la operación se marca *Por revisar* para el
  responsable de cumplimiento;
* cada operación se encadena en un registro inalterable (cadena de hash),
  que se puede comprobar y cerrar por periodo;
* la tabla de tipos se puede mostrar a pantalla completa en una pantalla
  orientada a los clientes, o en la pantalla del cliente de Odoo, y
  recarga los tipos por sí sola;
* las monedas y billetes extranjeros recibidos y entregados se pueden
  contar por denominación, con las existencias de cada cajón, y se pueden
  enviar billetes de una ventanilla de una casa de cambio a otra.

Todo esto es opcional: una ventanilla sola, sin casa de cambio, funciona
como antes.

Requisitos
==========

* La aplicación **Punto de venta** (``point_of_sale``), Odoo 20.
* **POS Multi-Currency Cash** (``pos_nm_multicurrencies``) **20.0.2.1.0 o
  posterior**, incluido en el precio mostrado en la Odoo Apps Store: 178 EUR
  en total, 59 EUR por este módulo más 119 EUR por POS Multi-Currency Cash
  (¿ya lo ha comprado? Contáctenos en odoo@natimai.solutions antes de comprar
  este módulo), con al menos una moneda extranjera en
  el método de pago en efectivo del punto de venta (consulte su guía:
  *Aceptar una divisa en efectivo*). Una versión anterior de POS
  Multi-Currency Cash no funciona con este módulo: actualícela primero.
  Con la 20.0.2.1.1 o posterior, la apertura del bloque Efectivo de la
  moneda principal en la ventana de cierre se muestra correctamente
  cuando la sesión tiene operaciones de cambio (antes, solo era un error
  de visualización: los importes contados y contabilizados eran
  correctos).
* Una **cuenta de ingresos para las comisiones** (tipo *Ingreso* u *Otros
  ingresos*).
* Para traspasar billetes entre las ventanillas de una casa de cambio:
  una **cuenta de fondos en tránsito** (tipo *Activos corrientes*).

Configuración
=============

Activar la ventanilla
---------------------

Vaya a *Punto de venta → Configuración → Ajustes*, seleccione su punto
de venta y consulte la sección **Cambio de divisas**:

* **Cambio de divisas** (activado por defecto): muestra las entradas de la
  ventanilla en el menú de la caja.
* **Cuenta de comisión**: cuenta de ingresos que recibe las comisiones.
  Solo se pueden elegir cuentas de ingresos. Es obligatoria para registrar
  una operación.
* **Número de licencia de cambio**: número de licencia o de registro de su
  actividad de cambio, impreso en los recibos y la tabla de tipos cuando
  se indica.
* **Casa de cambio**: la casa de cambio de esta ventanilla (consulte *Casa
  de cambio y ventanillas*). Con una casa de cambio, la licencia y los
  umbrales de identificación siguientes se ocultan: se aplican los de la
  casa de cambio.
* **Cliente obligatorio a partir de**: valor de una operación, en la
  moneda del punto de venta, a partir del cual debe identificarse al
  cliente.
* **Cliente obligatorio para cada operación**: cada operación indica su
  cliente.
* **Documento de identidad obligatorio a partir de**: valor a partir del
  cual se registra el documento de identidad del cliente en la operación.
* **Periodo de operaciones vinculadas (días)**: cuando es mayor que 0, el
  valor comparado con los umbrales es la operación más las operaciones
  del mismo cliente durante esos días (consulte *Identificación del
  cliente*).
* **Origen de los fondos obligatorio a partir de**: valor a partir del
  cual el cliente declara el origen de los fondos (consulte *Umbrales de
  cumplimiento*).
* **Revisión a partir de**: valor a partir del cual la operación se marca
  *Por revisar* para el responsable de cumplimiento. Nunca se rechaza.
* **Seguir los billetes por denominación**: los billetes extranjeros
  recibidos y entregados se cuentan por moneda y billete (consulte
  *Billetes por denominación*).
* **Tabla de tipos en la pantalla del cliente**: la pantalla del cliente de
  Odoo muestra la tabla de tipos mientras no hay ningún pedido en curso.
* **Dirección de la tabla de tipos**: dirección de la tabla de tipos a
  pantalla completa de esta ventanilla, para una pantalla orientada a los
  clientes (consulte *Tabla de tipos en una pantalla*).
* **Imprimir los tipos de cambio**: imprime la tabla de tipos del punto de
  venta en PDF.

Los umbrales en 0 nunca se aplican.

Comisiones y margen de venta por moneda
---------------------------------------

Vaya a *Punto de venta → Configuración → Monedas en efectivo* y abra la
línea de la moneda. El grupo *Cambio de divisas* contiene cuatro valores,
los importes en la moneda del punto de venta:

* **Margen de venta de cambio (%)**: margen de la ventanilla sobre los
  billetes de esta moneda que entrega (consulte *Tipos* más abajo). Oculto
  con un tipo de caja fijo, donde no se usa. Una moneda nueva parte de su
  Margen del tipo de caja (uno negativo se convierte en el margen de venta
  que mantiene el mismo tipo de venta, como en la actualización);
* **Comisión de cambio (%)**: porcentaje del valor de los billetes
  recibidos;
* **Comisión de cambio fija**: parte fija que se suma al porcentaje;
* **Comisión de cambio mínima**: la comisión es como mínimo este importe.

La comisión de una operación es la de la moneda extranjera implicada (la
moneda entregada cuando ambas son extranjeras). Cada cambio de estos
valores se registra en el chatter de la línea, como los tipos.

Tipos
-----

La ventanilla compra a un tipo y vende a otro, siempre a favor del
comercio. Los tipos se expresan en unidades de la moneda extranjera por
una unidad de la moneda del punto de venta, como en POS Multi-Currency
Cash:

* **Billetes recibidos** (tipo de compra): el tipo de caja de POS
  Multi-Currency Cash, es decir el tipo de Odoo con el **Margen del tipo
  de caja (%)** de la moneda, o su **Tipo fijo**.
* **Billetes entregados** (tipo de venta): el tipo de Odoo dividido entre
  1 + el **Margen de venta de cambio**. Con un tipo de caja fijo, el menor
  del **Tipo fijo** y del **Tipo fijo del cambio** (un Tipo fijo del cambio
  en 0 equivale al Tipo fijo): el tipo menor entrega menos billetes.

Ejemplo, punto de venta en USD, tipo de Odoo de 2 EUR por 1 USD, Margen
del tipo de caja y Margen de venta de cambio del 10 %: la ventanilla
compra euros a 2 × 1,10 = 2,20 EUR por 1 USD (100 EUR recibidos valen
45,45 $) y los vende a 2 / 1,10 = 1,8182 EUR por 1 USD (100 EUR entregados
valen 55,00 $), antes de la comisión.

La diferencia con los tipos de Odoo es el **Margen de tipo** de la
operación (consulte *Notas contables*). Al actualizar desde 20.0.1.x, el
Margen de venta de cambio de cada moneda toma el
valor de su Margen del tipo de caja: compruébelo.

Monedas y billetes
------------------

Los billetes entregados se redondean una vez, *a la baja*, a la moneda o
al billete más pequeño de su divisa, para que el cajero nunca tenga que
entregar monedas que no existen en el cajón; el resto queda en la
comisión, que nunca es inferior a la configurada:

* una moneda extranjera: su **Redondeo del cambio**, si no el redondeo de
  la moneda;
* la moneda del punto de venta: el método de redondeo del **Redondeo
  total** en los ajustes del punto de venta, cuando está activado, si no
  el redondeo de la moneda.

Recibo
------

El recibo de cambio imprime el logotipo, el **encabezado** y el **pie**
del punto de venta (*Ajustes*, sección *Facturas y recibos*, *Encabezado
y pie de página personalizado*), el número de licencia de cambio y los
datos de la compañía. Indique ahí las menciones legales que su actividad
debe mostrar al cliente. Con los billetes contados por denominación, el
recibo lista los billetes debajo de los importes.

Casa de cambio y ventanillas
----------------------------

Una casa de cambio es un establecimiento con licencia que tiene una o
varias ventanillas (puntos de venta). Es opcional: una ventanilla fuera de
cualquier casa de cambio conserva sus propios ajustes.

Vaya a *Punto de venta → Configuración → Casas de cambio* y pulse
**Nuevo**. Dé un nombre a la casa de cambio y complete:

* grupo *Casa de cambio*: la **Dirección** (impresa en el registro de
  cambios y la tabla de tipos), el **Número de licencia de cambio**, el
  **Responsable de cumplimiento** (recibe una actividad por cada operación
  marcada *Por revisar*) y la **Cuenta de fondos en tránsito** (consulte
  *Cuenta de fondos en tránsito*);
* grupo *Identificación*: **Cliente obligatorio para cada operación**,
  **Cliente obligatorio a partir de**, **Documento de identidad
  obligatorio a partir de**, **Origen de los fondos obligatorio a partir
  de**, **Revisión a partir de** y **Periodo de operaciones vinculadas**
  (días). Funcionan como los ajustes del mismo nombre de un punto de
  venta, en la moneda de la compañía.

La licencia y las reglas de la casa de cambio sustituyen a las de sus
ventanillas. Para añadir una ventanilla, defina su **Casa de cambio** en
la sección *Cambio de divisas* de los ajustes del punto de venta, o
añádala en la pestaña **Ventanillas** de la casa de cambio. Las
ventanillas de una casa de cambio deben usar la moneda de su compañía.

Los botones inteligentes de la casa de cambio abren sus **Ventanillas**,
sus **Operaciones** y sus **Traspasos** de billetes.

Los mismos tipos en cada ventanilla
-----------------------------------

En la pestaña **Ventanillas** de la casa de cambio, elija la **Ventanilla
de referencia**: la ventanilla cuyos tipos copian las demás, y cuyos tipos
muestra la tabla de tipos de la casa de cambio. Después, con dos
ventanillas o más:

* **Aplicar los tipos a las ventanillas** copia a las demás ventanillas,
  para cada moneda de la ventanilla de referencia, el tipo de caja (modo
  de tipo, margen, tipos fijos), los redondeos de las monedas y billetes,
  el **Margen de venta de cambio (%)** y las comisiones. Los cambios del
  tipo de caja, del margen de venta y de las comisiones se registran en el
  chatter de la moneda (no los de los redondeos). Una ventanilla que no acepta la
  moneda en efectivo se omite y se indica en un aviso;
* **Diferencias de tipos** lista lo que todavía difiere de la ventanilla
  de referencia.

Vuelva a aplicar los tipos después de cada cambio de la ventanilla de
referencia.

Umbrales de cumplimiento
------------------------

Dos umbrales le ayudan a seguir las normas contra el blanqueo de capitales
de su país. Se definen en la casa de cambio, o en los ajustes de un punto
de venta fuera de cualquier casa de cambio, en la moneda del punto de
venta; en 0 nunca se aplican. Las operaciones vinculadas del cliente
cuentan, como para los demás umbrales.

* **Origen de los fondos obligatorio a partir de**: la operación requiere
  un cliente, y el cliente declara el origen de los fondos. *Otro* requiere
  detalles.
* **Revisión a partir de**: la operación se marca *Por revisar*. Nunca se
  rechaza en la ventanilla. Se envía una actividad al **Responsable de
  cumplimiento** de la casa de cambio.

Una operación cuyo cliente declara ser una persona expuesta políticamente
también se marca *Por revisar*. Elija a un administrador del Punto de
venta como responsable de cumplimiento: solo los administradores del
Punto de venta pueden revisar las operaciones.

Tabla de tipos en una pantalla
------------------------------

Cada ventanilla tiene una página pública de tabla de tipos para un
televisor, una tableta o cualquier pantalla orientada a los clientes. Su
dirección es la **Dirección de la tabla de tipos** de la sección *Cambio
de divisas* de los ajustes del punto de venta. Contiene el token de acceso
del punto de venta, el de su pantalla del cliente: compártala solo con las
pantallas de la ventanilla.

Una casa de cambio tiene su propia página, en la pestaña **Tabla de
tipos** de la casa de cambio (administradores del Punto de venta): la
**Dirección de la tabla de tipos** muestra los tipos de la ventanilla de
referencia con el nombre, la dirección y la licencia de la casa de cambio.
**Actualización de la tabla de tipos (segundos)** define cada cuánto la
página recarga los tipos (60 por defecto, 10 como mínimo), también para
las páginas de sus ventanillas. **Nueva dirección** da a la página de la
casa de cambio una nueva dirección: las pantallas que muestran la antigua
dejan de recibir los tipos (conservan los últimos tipos con «Conexión
perdida: se muestran los últimos tipos» y no muestran nada una vez recargada la página).

Para mostrar la tabla en la pantalla del cliente de Odoo, marque **Tabla
de tipos en la pantalla del cliente** en los ajustes del punto de venta.

Billetes por denominación
-------------------------

POS Multi-Currency Cash ya cuenta las monedas y billetes de cada moneda
extranjera en la apertura y en el cierre. Este módulo también puede
seguirlos durante la sesión:

1. Vaya a *Punto de venta → Configuración → Monedas/billetes* y compruebe
   que las monedas y billetes de cada moneda extranjera existen, con su
   **Moneda** definida (consulte la guía de POS Multi-Currency Cash).
2. En los ajustes del punto de venta, marque **Seguir los billetes por
   denominación**.

La opción se aplica a las monedas extranjeras en efectivo que tienen
monedas y billetes en este punto de venta. La moneda del punto de venta no
se sigue: no tiene recuento por denominación. Cuente la apertura por
monedas y billetes, para que las existencias del cajón partan bien.

Cuenta de fondos en tránsito
----------------------------

Los billetes enviados de una ventanilla de una casa de cambio a otra pasan
por la **Cuenta de fondos en tránsito** de la casa de cambio: una cuenta
de activo corriente (tipo *Activos corrientes*). Cree una en su plan
contable si es necesario, por ejemplo «Billetes en tránsito», y defínala
en la casa de cambio. Su saldo es el valor de los billetes enviados y aún
no recibidos. Sin ella, no se pueden traspasar billetes.

Quién puede hacer qué
---------------------

* Los **usuarios del Punto de venta** (cajeros) registran operaciones en
  la caja, reimprimen sus recibos y muestran la tabla de tipos. Pueden
  leer las operaciones pero no modificarlas.
* Los **administradores del Punto de venta** (acceso *Punto de venta*:
  *Administrador*) ven además los menús *Punto de venta → Pedidos →
  Cambios de divisas* y *Punto de venta → Informes → Registro de
  cambios* y los documentos de identidad de los clientes, pueden
  modificar la nota de una operación y cancelar una operación.
* En una casa de cambio con otra ventanilla activada, los usuarios del
  Punto de venta también envían y reciben billetes en la caja (*Enviar
  billetes*, *Recibir billetes*), y ven las *Existencias de billetes* de
  su cajón cuando los billetes se siguen.
* Los administradores del Punto de venta gestionan además las casas de
  cambio (*Punto de venta → Configuración → Casas de cambio*, con las
  pestañas **Cajones** y **Tabla de tipos**), los traspasos de billetes
  (*Punto de venta → Pedidos → Traspasos de billetes*), y ven *Punto de
  venta → Informes → Existencias de billetes*, *Movimientos de billetes* y
  *Cierres del registro de cambios*.
* Solo los administradores del Punto de venta ven las declaraciones del
  cliente y revisan las operaciones (**Cumplimiento**, **Nota de
  cumplimiento**), comprueban la integridad del registro y lo cierran.
* Nadie puede eliminar una operación ni una de sus líneas de extracto, un
  movimiento de billetes, un cierre del registro ni un traspaso de billetes
  una vez enviado.
* Con varias compañías, cada usuario ve las operaciones de las compañías
  a las que tiene acceso.
* Con el módulo Empleados (``pos_hr``), el cajero de una operación es el
  empleado conectado a la caja, que debe estar autorizado en el punto de
  venta; si no, es el usuario.

Trabajo diario
==============

Cambiar divisas
---------------

Desde cualquier pantalla de la caja, abra el menú (arriba a la derecha) y
pulse **Cambio de divisas**:

1. elija la moneda **recibida del cliente** e introduzca el importe;
2. elija la moneda **entregada al cliente**. El importe entregado, el
   tipo, el valor de los billetes recibidos, la comisión y el saldo del
   cajón (**En el cajón**) se calculan mientras escribe. El botón de
   flecha intercambia las dos monedas;
3. cuando el cliente pide un importe exacto, introdúzcalo en el campo
   **Entregado al cliente**: se calcula el importe a recibir, redondeado
   al alza a las monedas de la divisa recibida, y aparece la indicación
   «Importe a recibir calculado a partir del importe entregado.». Al salir
   del campo, muestra el importe realmente entregado, que puede ser algo
   mayor cuando los billetes no permiten el importe exacto. Volver a
   escribir en **Recibido del cliente** vuelve al cálculo normal;
4. cuando el cliente debe identificarse, el botón **Cliente** se pone rojo
   con el motivo: púlselo y elija el cliente (créelo si es necesario).
   Cuando se requiere el documento de identidad, aparecen sus campos:
   tipo, país de expedición y fecha de caducidad se rellenan desde el
   contacto, y el campo del número solo muestra, como indicación, los 4
   últimos caracteres del número registrado. Tipo, número y fecha de
   caducidad son obligatorios; para un documento sin fecha de caducidad
   (un documento de identidad antiguo), marque **Sin fecha de caducidad**
   en su lugar. **Nacionalidad** y **Fecha de nacimiento**
   aparecen vacíos: si se dejan vacíos, conservan los valores del
   contacto. Para el mismo documento (mismo tipo, número dejado vacío), el
   número y los demás campos dejados vacíos también conservan los valores
   del contacto; para otro documento, introduzca su número;
5. añada una nota si es útil y pulse **Confirmar**. El cajón portamonedas
   se abre, se imprime el recibo de cambio y una notificación resume la
   operación.

**Confirmar** permanece desactivado mientras se calcula una cotización, y
cuando el cajón de la moneda entregada no contiene el importe (la línea
*En el cajón* aparece entonces en rojo, con el rechazo).

Si la conexión se pierde al confirmar, la ventana indica que la operación
puede haberse registrado: confirme de nuevo cuando vuelva la conexión.
Mientras tanto, importes, monedas, cliente, documento y nota no pueden
modificarse. Una operación ya registrada no se registra dos veces, y se
imprime su recibo. Si la conexión se pierde mientras se calcula la
cotización, la ventana lo indica y vuelve a pedir la cotización unos
segundos después.

Cuando la ventanilla no puede funcionar en este punto de venta, la entrada
**Cambio de divisas** muestra el motivo en lugar de la ventana: ninguna
moneda extranjera en el método de pago en efectivo, o ninguna cuenta de
comisión.

Declaraciones del cliente
-------------------------

Por encima del umbral **Origen de los fondos obligatorio a partir de** o
del umbral **Revisión a partir de**, una vez elegido el cliente, la
ventana muestra **Declaraciones del cliente**:

* **Origen de los fondos**: Salario o pensión, Ahorros, Ingresos
  profesionales, Venta de un bien, Herencia o donación, Otro. Obligatorio
  por encima del umbral de origen de los fondos; para *Otro*, escriba los
  **Detalles del origen de los fondos**;
* **Finalidad de la operación**: Viaje, Actividad profesional, Estudios,
  Ayuda familiar, Otro;
* **Persona expuesta políticamente (o un familiar o allegado cercano)**:
  márquelo cuando el cliente lo declare. La operación se marca entonces
  *Por revisar*.

Solo por encima del umbral de revisión, las declaraciones se piden pero no
son obligatorias. Se fijan en la operación con la dirección del cliente.
El cajero nunca queda bloqueado por una revisión: el responsable de
cumplimiento comprueba la operación más tarde (consulte *Por revisar*).

Contar los billetes
-------------------

Con **Seguir los billetes por denominación**, la ventana se ensancha y
muestra una cuadrícula para cada moneda extranjera seguida de la
operación:

* **Billetes recibidos**: introduzca la **Cantidad** de cada moneda y
  billete que entrega el cliente. El **Total** debe ser igual al importe
  recibido;
* **Billetes entregados**: las cantidades se proponen a partir de las
  existencias del cajón, los billetes más grandes primero. **En el cajón**
  da las existencias de cada moneda y billete. Cambie las cantidades si
  entrega otros billetes: el **Total** debe ser igual al importe
  entregado.

Aparece un mensaje rojo cuando un total no coincide, y **Confirmar**
permanece desactivado. Cuando al cajón le faltan algunos billetes, un
mensaje naranja los indica: «Al cajón le faltan ...: compruebe los
billetes antes de entregarlos.». Es solo un aviso, porque las ventas en
efectivo en una moneda extranjera mueven el cajón sin denominaciones: las
existencias pueden ir por detrás del cajón real. Cuando el importe
entregado no se puede componer con las monedas y billetes de la divisa, la
ventana lo muestra como un error.

Existencias de billetes
-----------------------

La entrada **Existencias de billetes** del menú de la caja (visible
cuando los billetes se siguen) da, para cada moneda seguida y cada moneda
y billete, el recuento de **Apertura**, los billetes movidos por los
**Cambios** y los traspasos, y las existencias **En el cajón**. Cuando la
apertura no se contó por monedas y billetes, la ventana lo indica: las
existencias solo cuentan entonces los cambios.

En el cierre, la ventana de recuento de cada moneda seguida muestra la
cantidad esperada (*esperado*) de cada moneda y billete junto al
recuento, cuando la apertura se contó por monedas y billetes (o el cajón
estaba vacío en la apertura).

Enviar y recibir billetes
-------------------------

Una ventanilla de una casa de cambio con otra ventanilla activada tiene
dos entradas más en el menú de la caja.

**Enviar billetes**:

1. elija la ventanilla en **Enviar a**. Cuando no hay ninguna caja abierta
   allí, la ventana avisa de que los billetes permanecen en tránsito hasta
   que se reciban;
2. elija la moneda e introduzca el **Importe enviado**. Con los billetes
   seguidos, la cuadrícula **Billetes enviados** propone los billetes a
   partir de las existencias del cajón; su **Total** debe ser igual al
   importe;
3. añada una nota si es útil y pulse **Confirmar**. El cajón portamonedas
   se abre y se imprime un comprobante de traspaso: póngalo con los
   billetes.

El cajón debe contener el importe. El traspaso recibe su referencia
(``TRF/AAAA/NNNNN``) y los billetes salen del cajón: una salida de
efectivo en la sesión, en la cuenta de fondos en tránsito de la casa de
cambio.

**Recibir billetes** lista los billetes en tránsito hacia esta ventanilla:
referencia, fecha de envío, ventanilla emisora, importe y billetes. Cuente
los billetes y pulse **Recibir**: los billetes entran en el cajón (una
entrada de efectivo del mismo valor) y se imprime un comprobante. Cuando la
ventanilla emisora no contó los billetes por denominación y esta
ventanilla los sigue, **Recibir** abre la cuadrícula **Billetes
recibidos**, prerrellenada con los billetes más grandes primero:
corríjala con los billetes realmente recibidos y pulse **Confirmar la
recepción**. **Actualizar** recarga la lista.

El importe recibido es el importe enviado. Una diferencia aparece en el
recuento de cierre del cajón receptor.

La tabla de tipos en una pantalla
---------------------------------

Abra la **Dirección de la tabla de tipos** de la ventanilla, o la
**Dirección de la tabla de tipos** de la casa de cambio (botón **Abrir la
tabla de tipos** de la casa de cambio), en el navegador de la pantalla y
póngala a pantalla completa. La página muestra las monedas con **Compramos**,
**Vendemos**, **Usted recibe por** y **Usted paga por** el importe típico, la comisión de
cada moneda, la licencia, la fecha y la hora. Recarga los tipos por sí
sola. Cuando se pierde la conexión, mantiene los últimos tipos en pantalla
con el mensaje «Conexión perdida: se muestran los últimos tipos».

La tabla se muestra en el idioma de la empresa (el de su contacto). Para
otro idioma instalado en la base de datos, añádalo a la dirección:
``&lang=es_ES`` para el español, ``&lang=en_US`` para el inglés, etc.

Con **Tabla de tipos en la pantalla del cliente**, la pantalla del cliente
de Odoo muestra la tabla de la ventanilla mientras no hay ningún pedido en
curso.

El aviso de monedas
-------------------

Aparece un aviso naranja cuando el importe recibido en una moneda
extranjera no se puede componer con sus monedas y billetes, por ejemplo
1.106 XPF con monedas de 5 XPF. El paso comprobado es el **Redondeo de los
pagos** de la moneda, si no su **Redondeo del cambio** cuando su **Resto
del cambio** está en *Conservado como redondeo*. El aviso no bloquea la
operación: compruebe los billetes realmente recibidos y corrija el
importe si es necesario.

Rechazos
--------

La caja rechaza una operación, con un mensaje, cuando:

* el cajón de la moneda entregada no contiene el importe, incluida la
  moneda del punto de venta (el saldo es el del control de cierre:
  apertura, ventas en efectivo y cambio entregado, movimientos de efectivo
  y operaciones de cambio de la sesión);
* el importe es demasiado pequeño: una vez deducida la comisión, no se
  puede entregar ningún billete;
* se elige la misma moneda en ambos lados;
* se requiere el cliente, o un documento de identidad válido, y falta, o
  el documento ha caducado;
* se requiere el origen de los fondos y no se ha declarado;
* con los billetes seguidos, los billetes recibidos o entregados no suman
  los importes;
* la cotización cambió entre la ventana y el servidor (tipo, margen o
  comisión modificados entretanto): no se registra nada, la ventana
  muestra de inmediato la nueva cotización con un aviso; compruébela con
  el cliente y confirme de nuevo;
* la sesión no está abierta, o la ventanilla está desactivada.

Reimprimir un recibo
--------------------

La entrada **Operaciones de cambio** del menú de la caja lista las
operaciones de la sesión (referencia, fecha, operación, recibido,
entregado, cliente). **Reimprimir** imprime de nuevo el recibo, marcado
*COPIA*; una operación cancelada desde entonces aparece marcada
*CANCELADO* con la fecha y la hora.

Mostrar los tipos
-----------------

La entrada **Tipos de cambio** del menú de la caja muestra la tabla de
tipos de la ventanilla, una línea por moneda extranjera en efectivo:

* **Compramos**: valor de 1 unidad de los billetes recibidos (tipo de
  caja, antes de la comisión), y **Usted recibe**: lo que el cliente
  recibe por un importe típico, comisión deducida y redondeado a los
  billetes;
* **Vendemos**: precio de 1 unidad de los billetes entregados (tipo de
  venta, antes de la comisión), y **Usted paga**: lo que el cliente paga
  por un importe típico, comisión incluida;
* **Comisión**: porcentaje, parte fija y mínimo.

El importe típico es la potencia de 10 más cercana a 100 unidades de la
moneda del punto de venta (100 EUR, 10.000 XPF, 1.000.000 VND), redondeada
a las monedas que la ventanilla acepta y entrega en esa moneda (su
Redondeo de los pagos y su Redondeo del cambio: 99 CHF con monedas de 3 CHF). Los
importes se calculan con la cotización de la ventanilla, por lo que
coinciden con las operaciones. **Imprimir** imprime la tabla en la
impresora de recibos.

Cancelar una operación
----------------------

Una operación errónea se cancela, no se corrige con otra operación: una
operación inversa cobraría de nuevo la comisión y redondearía de nuevo
los billetes, y un movimiento de efectivo dejaría la comisión en la cuenta
de comisión.

Un administrador del Punto de venta abre la operación (*Punto de venta →
Pedidos → Cambios de divisas*), pulsa **Cancelar la operación** y
confirma. Es posible mientras la sesión de la operación está abierta y el
cajón todavía contiene los billetes recibidos (el cliente los recupera).
Se registran en la sesión dos líneas de extracto exactamente opuestas a
las originales: mismos importes en ambas monedas, misma cuenta de
contrapartida. Ambos cajones y la cuenta de comisión vuelven a su estado
anterior a la operación.

La operación pasa a **Cancelada**, con la fecha y el usuario, se publica
un mensaje en la sesión y en la operación, y ya no cuenta en las
comisiones, el resumen de cierre ni los informes. Su recibo, reimpreso,
aparece marcado *CANCELADO*. Con los billetes seguidos, se restablecen
las existencias del cajón: los billetes recibidos salen de ellas y los
billetes devueltos vuelven a ellas (movimientos de billetes
*Cancelación*). La cancelación recibe su
propio hash en el registro (**Hash de la cancelación**), y una operación
de un periodo cerrado del registro no se puede cancelar.

Una vez cerrada la sesión, una operación ya no se puede cancelar.
Corríjala entonces con una operación inversa (la comisión y el redondeo
se aplican de nuevo; ponga la comisión de la moneda en 0 durante la
operación si la reembolsa) o con movimientos de efectivo de cada moneda,
y pida a su contable que retire la comisión de la cuenta de comisión.

Cerrar la sesión
----------------

La ventana de cierre muestra un bloque **Cambio de divisas** cuando la
sesión tiene operaciones: el número de operaciones, cada operación
(recibido, entregado, cajero), el total de las comisiones, el **Margen de
tipo** y el número de operaciones canceladas. Los billetes recibidos y
entregados ya están en los importes esperados de sus monedas: un cambio
es una entrada de efectivo en un cajón y una salida en el otro, ambas
listadas en los movimientos de la moneda.

Identificación del cliente
==========================

Los umbrales le ayudan a aplicar las normas de identificación de su país;
el módulo registra lo que introduce el cajero, no comprueba los
documentos de identidad en ningún registro.

* El valor comparado con los umbrales es el valor de los billetes
  recibidos, en la moneda del punto de venta.
* Con un **Periodo de operaciones vinculadas**, se suman las operaciones
  hechas (no canceladas) por el mismo cliente en los últimos días, en
  todos los puntos de venta de la compañía, convertidas a la moneda del
  punto de venta. Cuando este total supera un umbral, la ventana muestra
  «Con las operaciones vinculadas del cliente» y el total; si no, las
  demás operaciones del cliente no se muestran. Sin cliente, solo cuenta la
  operación: active **Cliente obligatorio para cada operación** para que
  la regla se aplique siempre.
* Por encima de **Cliente obligatorio a partir de**, la operación requiere
  un cliente.
* Por encima de **Documento de identidad obligatorio a partir de**,
  requiere un cliente y un documento de identidad válido: tipo
  (Pasaporte, Documento nacional de identidad, Permiso de conducir,
  Permiso de residencia, Otro), número, país de expedición, fecha de
  caducidad (o **Sin fecha de caducidad** para un documento que no la
  tiene), nacionalidad y fecha de nacimiento. Un documento caducado se
  rechaza.

El servidor vuelve a comprobar estas reglas al registrar la operación. El
documento introducido en la caja, cuando difiere del registrado, se
guarda en el contacto (pestaña **Documento de identidad** del formulario
del contacto) y se conserva una
copia en la operación con el nombre del cliente: modificar o renombrar el
contacto después no cambia las operaciones registradas. El recibo imprime
el nombre del cliente y el tipo de documento con solo los 4 últimos
caracteres de su número (por ejemplo «Pasaporte \*\*\*\*4567»).

Los documentos de identidad solo son visibles para los administradores
del Punto de venta; en la ventana, el cajero ve el tipo, el país de
expedición, la fecha de caducidad y los 4 últimos caracteres del número
del cliente seleccionado. Un documento modificado en la caja queda
registrado en el contacto. El contacto de un usuario interno, incluso
archivado, solo lo modifica un administrador del Punto de venta (el
documento queda entonces en la operación); un cliente con una cuenta de
portal es un cliente como cualquier otro.

Consultar las operaciones
=========================

Cambios de divisas
------------------

*Punto de venta → Pedidos → Cambios de divisas* (administradores del
Punto de venta) lista las operaciones con su referencia, fecha, punto de
venta, cajero, cliente, los billetes recibidos y entregados, la comisión,
el margen de tipo y el estado. Se abre con el filtro **Hecha**; el filtro
**Cancelada** muestra las canceladas. Otros filtros: *Hoy*, *Con
cliente*, *Compra de divisas*, *Venta de divisas*, *Cambio cruzado*;
agrupación por punto de venta, sesión, cajero, tipo de operación, estado,
moneda o fecha. La tabla dinámica da las comisiones, los márgenes de tipo
y los valores recibidos por día, estado y moneda recibida; reagrúpela por
punto de venta, sesión o cajero si lo necesita.

El tipo de operación se ve desde el comercio: *Compra de divisas* cuando
recibe billetes extranjeros, *Venta de divisas* cuando entrega billetes
extranjeros, *Cambio cruzado* entre dos monedas extranjeras.

El formulario de una operación muestra sus importes, el **Tipo aplicado**
(«1 USD = 119,33 XPF»), la comisión, el margen de tipo, el documento de
identidad y el chatter. Sus botones:

* **Enviar por correo electrónico** (cuando la operación tiene un
  cliente): envía el recibo en PDF con la plantilla *Cambio de divisas:
  enviar el recibo*;
* **Imprimir**: el recibo en PDF (*Recibo de cambio*);
* **Cancelar la operación** (véase más arriba);
* **Líneas de extracto**: las dos líneas de la operación, y las dos
  líneas de su cancelación.

Solo la **Nota**, el **Cumplimiento** y la **Nota de cumplimiento** se
pueden modificar, por un administrador del Punto de venta (véase *Por
revisar*); los cambios de la **Nota** y del **Cumplimiento** se registran
en el chatter.

El formulario de la sesión tiene un botón con el total de las comisiones
y «Operaciones: N», el número de operaciones hechas; las abre.

En una casa de cambio, la operación muestra también su **Casa de cambio**
y su **Licencia**, y la lista se puede agrupar por **Casa de cambio**. Con
los billetes seguidos, el botón **Movimientos de billetes** abre las
monedas y billetes de la operación.

Por revisar
-----------

El filtro **Por revisar** de *Cambios de divisas* da las operaciones
marcadas para el responsable de cumplimiento: por encima del umbral de
revisión, o con una persona expuesta políticamente declarada. El
responsable de cumplimiento de la casa de cambio recibe además una
actividad «Revisar la operación de cambio ...».

El grupo **Declaraciones y cumplimiento** de la operación (administradores
del Punto de venta) muestra el **Origen de los fondos**, los **Detalles
del origen de los fondos**, la **Finalidad**, **Persona expuesta
políticamente**, el **Motivo de la revisión**, y los dos campos de la
revisión:

* **Cumplimiento**: Ninguno, Por revisar, Revisada o Notificada. Elija
  *Revisada* una vez comprobada, o *Notificada* cuando haya comunicado la
  operación a las autoridades;
* **Nota de cumplimiento**: lo que ha comprobado o decidido.

Estos dos campos y la **Nota** son los únicos que un administrador del
Punto de venta puede modificar; los cambios de **Cumplimiento** y de la
**Nota** se registran en el chatter. El grupo **Documento de identidad**
muestra ahora también la **Dirección del cliente** de la operación.

Detalles de ventas
------------------

El informe *Detalles de ventas* termina con una tabla *Cambio de
divisas*: cada operación con su sesión, sus importes, su comisión y su
margen de tipo, luego los totales, una línea por moneda de los puntos de
venta, y la lista de las operaciones canceladas, que no se cuentan.
Impreso desde una sesión, cubre las operaciones de la sesión; lanzado
desde *Punto de venta → Informes → Detalles de ventas* para un periodo,
cubre las operaciones fechadas en ese periodo en los puntos de venta
seleccionados (todos cuando no se selecciona ninguno), sesiones abiertas
incluidas. El informe *Posición de divisas* de POS Multi-Currency Cash
refleja los billetes movidos.

Registro de cambios
-------------------

*Punto de venta → Informes → Registro de cambios* (administradores del
Punto de venta) lista cada operación en el orden de su referencia,
incluidas las canceladas (en gris, con su estado), con el cajero, el tipo
de operación, los importes, el tipo, la comisión, el margen de tipo, el
nombre del cliente y el documento de identidad. Las referencias se siguen
sin huecos. Expórtelo a Excel con la acción estándar *Exportar*.

**Imprimir el registro** pide un periodo (**Desde**, **Hasta**, por
defecto desde el inicio del mes hasta ahora) y los **Puntos de venta**
(todos cuando está vacío), e imprime el registro en PDF (A4 apaisado) con
los totales por moneda: número de operaciones, recibido, entregado,
saldo, comisiones y márgenes de tipo. Las operaciones canceladas
aparecen pero no se cuentan en los totales.

La lista muestra también el **Origen de los fondos** y el
**Cumplimiento** de cada operación; la **Casa de cambio**, la
**Licencia**, la **Dirección del cliente**, la **Finalidad**, **Persona
expuesta políticamente** y el **Hash del registro** se pueden añadir desde
las columnas opcionales. En el asistente, elija una **Casa de cambio**
para imprimir solo el registro de sus ventanillas. El PDF muestra entonces
la casa de cambio, su dirección y su licencia; también da, para cada
operación, la dirección, la nacionalidad y la fecha de nacimiento del
cliente, las declaraciones, el estado de cumplimiento y el hash.

Integridad del registro
-----------------------

Cada operación recibe un hash (SHA-256) al registrarse, con el hash de la
operación anterior de la compañía: las operaciones forman una cadena. Una
cancelación recibe su propio hash, encadenado al hash de la operación. El
formulario de la operación los muestra en el grupo **Registro**: **Hash
del registro**, **Hash anterior** y **Hash de la cancelación**. Odoo
rechaza cualquier cambio de los campos del registro de una operación con
hash (importes, tipo, cliente, documento de identidad, origen de los
fondos), incluso por parte del administrador: solo la **Nota** y la
revisión de cumplimiento se pueden seguir modificando.

Para comprobar la cadena, pulse **Imprimir el registro** y después
**Comprobar la integridad**. La comprobación recalcula los hashes de todas
las operaciones de la compañía, en orden:

* «N operaciones comprobadas: el registro está intacto (última: ...).»
  cuando todos los hashes coinciden. Las operaciones sin hash, registradas
  antes del inicio de la cadena, se cuentan aparte;
* si no, «La comprobación de integridad falló en ...», con la primera
  operación que no coincide y el motivo: falta el hash, cadena rota, la
  operación fue alterada o la cancelación fue alterada.

La cadena de hash muestra que una operación se modificó o se eliminó
directamente en la base de datos. No impide ese cambio, y no puede mostrar
que se eliminaron las últimas operaciones: compare con el **Hash de la
última operación** del último cierre del registro, o con un registro
impreso.

Cierres del registro
--------------------

Cierre el registro de un periodo una vez terminado, por ejemplo cada mes:

1. *Punto de venta → Informes → Registro de cambios*, **Imprimir el
   registro**;
2. defina **Desde** y **Hasta**, y la **Casa de cambio** para cerrar el
   registro de una casa de cambio (déjela vacía, sin punto de venta, para
   toda la compañía);
3. pulse **Cerrar el periodo** y confirme. El cierre no se puede deshacer.

El registro solo se cierra cuando el periodo ha terminado, las sesiones de
sus operaciones están cerradas, no se solapa con otro cierre de la misma
casa de cambio o de toda la compañía (para un cierre de toda la compañía:
tampoco con ningún cierre de una de sus casas de cambio), y la comprobación de integridad es
correcta. El cierre recibe una referencia sin huecos (``EXR/AAAA/NNNN``) y
fija el número de **Operaciones** y de canceladas (**Cancelada**), la
**Primera referencia** y la **Última referencia**, las **Comisiones**, los
**Márgenes de tipo**, el resultado de la comprobación de **Integridad** y
el **Hash de la última operación**. Se adjunta el registro en PDF del
periodo: **Descargar el registro**.

Los cierres se listan en *Punto de venta → Informes → Cierres del registro
de cambios*. No se pueden modificar ni eliminar, y una operación de un
periodo cerrado ya no se puede cancelar.

Existencias y movimientos de billetes
-------------------------------------

*Punto de venta → Informes → Existencias de billetes* (administradores del
Punto de venta) da, por sesión, moneda y **Denominación**, el recuento de
**Apertura**, las monedas y billetes puestos (**Entradas**) y retirados
(**Salidas**) por las operaciones y los traspasos, las **Existencias**, el
recuento de **Cierre** y la **Diferencia** (cierre menos existencias,
cuando ambos recuentos se hicieron por monedas y billetes). Una diferencia
negativa aparece en rojo, una positiva en naranja. El filtro
**Diferencias** conserva las líneas que no coinciden; una vista de tabla
dinámica da las existencias por moneda y denominación.

*Punto de venta → Informes → Movimientos de billetes* lista cada moneda y
billete movido: por un cambio, una cancelación o un traspaso, con su
sesión, operación o traspaso, **Denominación** y **Cantidad**. Los
movimientos nunca se modifican ni se eliminan.

Traspasos de billetes
---------------------

*Punto de venta → Pedidos → Traspasos de billetes* (administradores del
Punto de venta) lista los traspasos con su referencia, casa de cambio,
**Ventanilla emisora**, **Ventanilla receptora**, importe, valor, fechas y
estado: Borrador, En tránsito, Recibido o Traspaso cancelado. El filtro
**En tránsito** da los billetes enviados y aún no recibidos.

Un administrador del Punto de venta también puede hacer un traspaso desde
el backend de Odoo: **Nuevo**, elija la casa de cambio, las ventanillas, la moneda
y el importe, y después **Enviar**. La ventanilla emisora necesita una
sesión abierta. Cuando sigue los billetes, se envían los billetes
propuestos a partir de sus existencias; si sus existencias no permiten
componer exactamente el importe, el envío se rechaza («Introduzca los
billetes enviados por denominación»): envíe entonces desde la caja para
elegir los billetes. **Recibir** pone los billetes en el cajón de la ventanilla
receptora, en su sesión abierta.

**Cancelar** un traspaso en tránsito es posible mientras la sesión que lo
envió está abierta: los billetes vuelven al cajón emisor (una entrada de
efectivo en esa sesión). Un traspaso recibido no se puede cancelar:
traspase los billetes de vuelta. Una vez enviado, solo se puede modificar
la **Nota** de un traspaso. Los botones **Movimientos de efectivo** y
**Movimientos de billetes** abren sus líneas de extracto y sus monedas y
billetes.

Los cajones de una casa de cambio
---------------------------------

La pestaña **Cajones** de la casa de cambio (administradores del Punto de
venta) muestra, para cada ventanilla con una sesión abierta, el
**Efectivo esperado** de cada moneda (apertura, ventas, movimientos de
efectivo, cambios y traspasos), las **Operaciones de hoy** y las
**Comisiones de hoy**, con los totales. Debajo, **Fondos en tránsito** da,
por moneda, los traspasos enviados y aún no recibidos, su importe y su
valor, y el **Total en tránsito**.

Tabla de tipos en PDF
---------------------

La tabla de tipos descrita más arriba también se imprime en PDF (*Tipos
de cambio*) con **Imprimir los tipos de cambio** en los ajustes, o desde
el menú *Imprimir* de los puntos de venta (vista de lista de *Punto de
venta → Tablero*).

Notas contables
===============

* Una operación son dos líneas de extracto del diario de efectivo de la
  sesión: los billetes recibidos (positivos, en su moneda, a su valor
  recibido) y los billetes entregados (negativos, en su moneda, a su valor
  entregado). Una línea en la moneda del punto de venta no lleva moneda
  extranjera. Las líneas llevan al cajero como contacto.
* Ambas líneas usan la **cuenta de comisión** como contrapartida: la
  diferencia entre los dos valores, la comisión, es lo que queda en esa
  cuenta. No se registra ningún asiento separado para la comisión.
* El **Margen de tipo** de una operación es lo que sus tipos ganan frente
  a los tipos de Odoo del día: valor de los billetes recibidos al tipo de
  Odoo menos su valor recibido, más el valor entregado menos el valor de
  los billetes entregados al tipo de Odoo. Se realiza como en cualquier
  venta en moneda extranjera: con la revalorización del cajón de POS
  Multi-Currency Cash, o al depositar los billetes (consulte su guía). La
  comisión más el margen de tipo es el ingreso de la operación. Con tipos
  fijos por encima de los tipos de Odoo, el margen de tipo puede ser
  negativo: muestra la pérdida.
* Una cancelación registra dos líneas opuestas a las originales, en la
  misma cuenta de contrapartida: la comisión se revierte.
* Las operaciones y sus líneas de extracto no se pueden eliminar; las
  referencias (``EXC/AAAA/NNNNN``) no tienen huecos.
* Un traspaso de billetes también son dos líneas de extracto: una salida
  de efectivo en la sesión de la ventanilla emisora cuando se envían los
  billetes, y una entrada de efectivo del mismo valor en la sesión de la
  ventanilla receptora cuando se reciben, ambas con la **Cuenta de fondos
  en tránsito** de la casa de cambio como contrapartida. El valor es el
  importe al tipo de Odoo del día, en la moneda de la compañía. El saldo
  de la cuenta es el valor de los billetes en tránsito; vuelve a cero una
  vez recibido o cancelado cada traspaso.

Actualizar a 20.0.4.0.0
=======================

* Sigue siendo necesario POS Multi-Currency Cash 20.0.2.1.0 o posterior.
* La actualización copia el número de licencia de cambio de cada punto de
  venta en sus operaciones existentes, y después encadena las operaciones
  existentes en el hash del registro, en el orden de su creación,
  compañía por compañía. Ejecute **Comprobar la integridad** una vez
  después de la actualización.
* Nada cambia para una ventanilla fuera de cualquier casa de cambio: sus
  ajustes se mantienen. Los nuevos umbrales (**Origen de los fondos
  obligatorio a partir de**, **Revisión a partir de**) parten de 0, sin
  aplicarse, y **Seguir los billetes por denominación** no está marcado.
* Para usar las casas de cambio, créelas, añada sus ventanillas y defina
  después la **Cuenta de fondos en tránsito** de cada casa de cambio antes
  de enviar billetes entre sus ventanillas.
* Cierre las sesiones, o recargue cada caja, después de la actualización,
  para que las cajas carguen las nuevas entradas del menú.

Actualizar desde 20.0.1.x
=========================

* Actualice primero POS Multi-Currency Cash a 20.0.2.1.0 o posterior: de
  lo contrario, la instalación y la actualización se rechazan.
* El **Margen de venta de cambio** de cada moneda toma el valor de su
  Margen del tipo de caja (un margen negativo se convierte en el margen de
  venta que mantiene el mismo tipo de venta, 2,04 % para -2 %): los
  billetes entregados se
  valoran ahora al tipo de venta, a favor del comercio. Compruebe los
  márgenes y la tabla de tipos antes de abrir las cajas.
* Las operaciones ya registradas reciben su usuario, estado, tipo, margen
  de tipo y nombre del cliente. Su margen de tipo se calcula al tipo de
  Odoo de su día: las operaciones anteriores muestran la pérdida de la
  antigua valoración de los billetes entregados.
* La secuencia de las referencias pasa a ser sin huecos. Las operaciones
  ya no se pueden eliminar: use **Cancelar la operación**.
* El cajón de la moneda del punto de venta ahora se comprueba: cuente su
  importe de apertura.
* Cierre las sesiones, o recargue cada caja, después de la actualización:
  una caja que sigue con la versión anterior no puede registrar
  operaciones.
* Una operación cuya línea de extracto se eliminó con 20.0.1.x se indica
  en el registro del servidor y con un mensaje en la operación: corrija el
  cajón con un movimiento de efectivo.

Limitaciones conocidas
======================

* La ventanilla funciona en línea: la cotización y el registro son
  llamadas al servidor.
* Una operación implica dos monedas; un cliente que cambia varias monedas
  a la vez genera varias operaciones.
* Una operación solo se puede cancelar mientras su sesión está abierta, y
  no en un periodo cerrado del registro.
* Los billetes se siguen por denominación solo para las monedas
  extranjeras: la moneda del punto de venta no tiene recuento por monedas
  y billetes.
* Las existencias de billetes solo siguen las operaciones de cambio y los
  traspasos: las ventas en efectivo y los movimientos de efectivo en una
  moneda extranjera cambian el cajón sin denominaciones. El siguiente
  recuento lo corrige.
* Un traspaso de billetes recibido no se puede cancelar: traspase los
  billetes de vuelta.
* La comprobación de integridad cubre el registro de toda la compañía.

Solución de problemas
=====================

La entrada Cambio de divisas no aparece en el menú
--------------------------------------------------

Compruebe que **Cambio de divisas** está activado en el punto de venta y
después cierre y vuelva a abrir la caja: el ajuste se lee al cargar sus
datos.

Aparece un mensaje en lugar de la ventana
-----------------------------------------

Añada una moneda extranjera al método de pago en efectivo del punto de
venta, o defina la **Cuenta de comisión** en la sección *Cambio de
divisas* de los ajustes, y recargue la caja.

La cuenta de comisión se rechaza
--------------------------------

Solo una cuenta de tipo *Ingreso* u *Otros ingresos* puede recibir las
comisiones.

El importe entregado es inferior al esperado
--------------------------------------------

Los billetes entregados se valoran al tipo de venta y se redondean a la
baja al **Redondeo del cambio** de su moneda (el Redondeo total del punto
de venta para su propia moneda), y la comisión incluye el resto.
Compruebe el Margen de venta de cambio, el redondeo y la comisión de la
moneda.

El cajón no contiene el importe
-------------------------------

El cajón de la moneda entregada debe contener el importe, tal como lo
cuenta el control de cierre. Haga el cambio en el otro sentido, o
registre primero una entrada de efectivo en esa moneda. Para la moneda
del punto de venta, compruebe que se contó el importe de apertura.

Un aviso naranja sobre monedas y billetes
-----------------------------------------

El importe recibido no se puede componer con las monedas de la divisa
(consulte *El aviso de monedas*). No bloquea la operación.

«La cotización cambió»
----------------------

Un tipo, un margen o una comisión cambió después de la cotización: no
se registró nada. La ventana pide de inmediato la nueva cotización y la
muestra con un aviso; compruebe el nuevo importe con el cliente y pulse de
nuevo **Confirmar**. La operación nunca se confirma sola.

La conexión se perdió al confirmar
----------------------------------

Confirme de nuevo cuando vuelva la conexión: una operación ya registrada
no se registra dos veces.

Una operación no se puede cancelar
----------------------------------

Solo un administrador del Punto de venta puede cancelar, mientras la
sesión de la operación está abierta y el cajón todavía contiene los
billetes recibidos. Después del cierre, consulte *Cancelar una
operación*.

El documento de identidad se rechaza
------------------------------------

Tipo, número y fecha de caducidad son obligatorios (o **Sin fecha de
caducidad** marcado para un documento que no la tiene), y el documento no
debe estar caducado. El umbral puede alcanzarse con las operaciones
vinculadas del cliente: la ventana muestra su total.

Falta Eliminar en las operaciones
---------------------------------

Las operaciones no se pueden eliminar, para que el registro siga
completo: cancele la operación en su lugar.

Faltan Enviar billetes y Recibir billetes
-----------------------------------------

La ventanilla debe pertenecer a una casa de cambio con al menos otra
ventanilla donde **Cambio de divisas** está activado. Después, recargue la
caja.

«Defina la cuenta de fondos en tránsito»
----------------------------------------

Defina la **Cuenta de fondos en tránsito** de la casa de cambio (una
cuenta de activo corriente) antes de traspasar billetes.

Los billetes no cuadran
-----------------------

Con los billetes seguidos, el **Total** de cada cuadrícula debe ser igual
al importe de la operación o del traspaso. Corrija las cantidades.

«Al cajón le faltan ...»
------------------------

Las existencias del cajón, tal como se contaron en la apertura y las
movieron las operaciones, contienen menos de esos billetes. Compruebe los
billetes realmente entregados o enviados. No bloquea la operación.

El registro no se puede cerrar
------------------------------

El periodo debe haber terminado, las sesiones de sus operaciones deben
estar cerradas y la comprobación de integridad debe ser correcta. No debe
solaparse con un cierre de la misma casa de cambio o de toda la
compañía; un cierre de toda la compañía no debe solaparse con ningún
cierre de una casa de cambio. Para
cerrar toda la compañía, deje vacíos **Casa de cambio** y **Puntos de
venta**.

El cajero no encuentra Cambios de divisas ni Registro de cambios
----------------------------------------------------------------

Estos menús están reservados a los administradores del Punto de venta.
Los cajeros usan la entrada **Operaciones de cambio** del menú de la
caja.

Aviso legal
===========

Este módulo lo proporciona Natimai Solutions bajo la Odoo Proprietary
License v1.0. Las operaciones de cambio pueden estar reguladas en su país
(licencias, identificación del cliente, registros, declaraciones): el
módulo le ayuda a conservar las operaciones, su cliente y su documento de
identidad y el registro de cambios, pero no hace por sí solo que su
actividad cumpla la normativa; el cumplimiento de la normativa local
sigue siendo responsabilidad de la empresa.

Soporte
=======

* Correo electrónico: odoo@natimai.solutions
* Sitio web: https://www.natimai.solutions

Licencia
========

OPL-1 (Odoo Proprietary License), consulte el archivo ``LICENSE`` del
módulo.
