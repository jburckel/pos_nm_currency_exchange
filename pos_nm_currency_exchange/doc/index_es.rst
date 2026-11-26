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
* un responsable puede cancelar una operación errónea mientras la sesión
  está abierta;
* las operaciones aparecen en el control de cierre, en el informe
  *Posición de divisas* y en el informe *Detalles de ventas*, en una lista
  con una tabla dinámica de las comisiones y márgenes de tipo, y en un
  registro de cambios que se puede exportar o imprimir para un periodo;
* la tabla de tipos de la ventanilla se puede mostrar e imprimir en la
  caja, o imprimir en PDF.

Requisitos
==========

* La aplicación **Punto de venta** (``point_of_sale``), Odoo 20.
* **POS Multi-Currency Cash** (``pos_nm_multicurrencies``) **20.0.2.1.0 o
  posterior**, incluido en el precio mostrado en la Odoo Apps Store (no se
  le cobra de nuevo si ya lo tiene), con al menos una moneda extranjera en
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

Configuración
=============

Activar la ventanilla
---------------------

Vaya a *Punto de venta -> Configuración -> Ajustes*, seleccione su punto
de venta y consulte la sección **Cambio de divisas**:

* **Cambio de divisas** (activado por defecto): muestra las entradas de la
  ventanilla en el menú de la caja.
* **Cuenta de comisión**: cuenta de ingresos que recibe las comisiones.
  Solo se pueden elegir cuentas de ingresos. Es obligatoria para registrar
  una operación.
* **Número de licencia de cambio**: número de licencia o de registro de su
  actividad de cambio, impreso en los recibos y la tabla de tipos cuando
  se indica.
* **Cliente obligatorio a partir de**: valor de una operación, en la
  moneda del punto de venta, a partir del cual debe identificarse al
  cliente.
* **Cliente obligatorio para cada operación**: cada operación indica su
  cliente.
* **Documento de identidad obligatorio a partir de**: valor a partir del
  cual se registra el documento de identidad del cliente en la operación.
* **Periodo de operaciones vinculadas (días)**: cuando es mayor que 0, el
  valor comparado con los dos umbrales es la operación más las operaciones
  del mismo cliente durante esos días (consulte *Identificación del
  cliente*).
* **Imprimir los tipos de cambio**: imprime la tabla de tipos del punto de
  venta en PDF.

Los umbrales en 0 nunca se aplican.

Comisiones y margen de venta por moneda
---------------------------------------

Vaya a *Punto de venta -> Configuración -> Monedas en efectivo* y abra la
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
compra euros a 2,20 EUR por 1 USD (100 EUR recibidos valen 45,45 $) y los
vende a 1,82 EUR por 1 USD (100 EUR entregados valen 55,00 $), antes de la
comisión.

La diferencia con los tipos de Odoo es el **Margen de tipo** de la
operación (consulte *Notas contables*). Al actualizar desde una versión
anterior a 20.0.2.0.0, el Margen de venta de cambio de cada moneda toma el
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
debe mostrar al cliente.

Quién puede hacer qué
---------------------

* Los **usuarios del Punto de venta** (cajeros) registran operaciones en
  la caja, reimprimen sus recibos y muestran la tabla de tipos. Pueden
  leer las operaciones pero no modificarlas.
* Los **administradores del Punto de venta** (acceso *Punto de venta*:
  *Administrador*) ven además los menús *Punto de venta -> Pedidos ->
  Cambios de divisas* y *Punto de venta -> Informes -> Registro de
  cambios* y los documentos de identidad de los clientes, pueden
  modificar la nota de una operación y cancelar una operación.
* Nadie puede eliminar una operación ni una de sus líneas de extracto.
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

Un administrador del Punto de venta abre la operación (*Punto de venta ->
Pedidos -> Cambios de divisas*), pulsa **Cancelar la operación** y
confirma. Es posible mientras la sesión de la operación está abierta y el
cajón todavía contiene los billetes recibidos (el cliente los recupera).
Se registran en la sesión dos líneas de extracto exactamente opuestas a
las originales: mismos importes en ambas monedas, misma cuenta de
contrapartida. Ambos cajones y la cuenta de comisión vuelven a su estado
anterior a la operación.

La operación pasa a **Cancelada**, con la fecha y el usuario, se publica
un mensaje en la sesión y en la operación, y ya no cuenta en las
comisiones, el resumen de cierre ni los informes. Su recibo, reimpreso,
aparece marcado *CANCELADO*.

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

*Punto de venta -> Pedidos -> Cambios de divisas* (administradores del
Punto de venta) lista las operaciones con su referencia, fecha, punto de
venta, cajero, cliente, los billetes recibidos y entregados, la comisión,
el margen de tipo y el estado. Se abre con el filtro **Hecha**; el filtro
**Cancelada** muestra las canceladas. Otros filtros: *Hoy*, *Con
cliente*, *Compra de divisas*, *Venta de divisas*, *Cambio cruzado*;
agrupación por punto de venta, sesión, cajero, tipo de operación, estado,
moneda o fecha. La tabla dinámica da las comisiones, los márgenes de tipo
y los valores recibidos por día, estado y moneda.

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

Solo la **Nota** se puede modificar, por un administrador del Punto de
venta; sus cambios se registran en el chatter.

El formulario de la sesión tiene un botón con el total de las comisiones
y «Operaciones: N», el número de operaciones hechas; las abre.

Detalles de ventas
------------------

El informe *Detalles de ventas* termina con una tabla *Cambio de
divisas*: cada operación con su sesión, sus importes, su comisión y su
margen de tipo, luego los totales, una línea por moneda de los puntos de
venta, y la lista de las operaciones canceladas, que no se cuentan.
Impreso desde una sesión, cubre las operaciones de la sesión; lanzado
desde *Punto de venta -> Informes -> Detalles de ventas* para un periodo,
cubre las operaciones fechadas en ese periodo en los puntos de venta
seleccionados (todos cuando no se selecciona ninguno), sesiones abiertas
incluidas. El informe *Posición de divisas* de POS Multi-Currency Cash
refleja los billetes movidos.

Registro de cambios
-------------------

*Punto de venta -> Informes -> Registro de cambios* (administradores del
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

Tabla de tipos en PDF
---------------------

La tabla de tipos descrita más arriba también se imprime en PDF (*Tipos
de cambio*) con **Imprimir los tipos de cambio** en los ajustes, o desde
el menú *Imprimir* de los puntos de venta (vista de lista de *Punto de
venta -> Tablero*).

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
* Una operación solo se puede cancelar mientras su sesión está abierta.
* La tabla de tipos no se muestra en la pantalla del cliente.

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
