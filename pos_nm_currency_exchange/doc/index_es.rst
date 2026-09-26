=====================
Cambio de divisas TPV
=====================

Una ventanilla de cambio dentro del Punto de Venta de Odoo 20: el cliente
trae billetes en una moneda y se lleva billetes en otra, menos una
comisión. Construido sobre POS Multi-Currency Cash, que controla el cajón
de cada divisa, sus tipos de caja y sus monedas y billetes.

Presentación
============

Los comercios en zonas turísticas, hoteles, campings o localidades
fronterizas reciben con frecuencia solicitudes de cambio de moneda. Con
POS Multi-Currency Cash la caja ya acepta billetes extranjeros y devuelve
el cambio en una divisa extranjera; este módulo añade la operación sin
venta:

* el cajero abre la entrada **Cambio de divisas** del menú de la caja,
  elige la divisa recibida y la divisa entregada, e indica el importe
  recibido;
* la caja calcula el importe que hay que entregar a los tipos de caja del
  punto de venta, con la comisión de la divisa y el redondeo a sus
  monedas y billetes;
* la operación se registra con el cajero y, cuando es necesario, el
  cliente, y se imprime un recibo de cambio;
* ambos cajones se mueven: los billetes recibidos entran en el cajón de su
  divisa y los billetes entregados salen del otro, en el diario de caja de
  la sesión, con la comisión contabilizada en una cuenta de ingresos
  dedicada;
* las operaciones aparecen en el control de cierre, en el informe
  *Posición en divisas* y en el informe *Detalles de ventas*, y se listan
  por punto de venta, sesión y cajero con una tabla dinámica de las
  comisiones.

Requisitos
==========

* La aplicación **Punto de Venta** (``point_of_sale``), Odoo 20.
* **POS Multi-Currency Cash** (``pos_nm_multicurrencies``) 20.0, con al
  menos una divisa extranjera en el método de pago en efectivo del punto
  de venta (véase su guía: *Aceptar una divisa en efectivo*).
* Una **cuenta de ingresos para las comisiones**.

Configuración
=============

Activar la ventanilla
---------------------

Vaya a *Punto de Venta -> Configuración -> Ajustes*, seleccione su punto de
venta y consulte la sección **Cambio de divisas**:

* **Cambio de divisas** (activado por defecto): muestra la entrada en el
  menú de la caja.
* **Cuenta de comisión**: cuenta de ingresos que recibe las comisiones. Es
  obligatoria para registrar una operación.
* **Cliente obligatorio a partir de**: importe de una operación, en la
  divisa del punto de venta, a partir del cual debe identificarse el
  cliente. 0: nunca.

Comisiones por divisa
---------------------

Vaya a *Punto de Venta -> Configuración -> Monedas de efectivo* y abra la
línea de la divisa. El grupo *Cambio de divisas* contiene tres valores,
todos en la divisa del punto de venta salvo el porcentaje:

* **Comisión de cambio (%)**: porcentaje del valor de los billetes
  recibidos;
* **Comisión de cambio fija**: parte fija añadida al porcentaje;
* **Comisión de cambio mínima**: la comisión es como mínimo este importe.

La comisión de una operación es la de la divisa extranjera implicada (la
divisa entregada cuando ambas son extranjeras). Cada modificación de las
comisiones queda registrada en el chatter de la línea, como los tipos.

Tipos, monedas y billetes
-------------------------

La ventanilla utiliza los tipos de caja de POS Multi-Currency Cash: los
billetes recibidos se valoran al tipo aplicado a lo que paga un cliente
(tipo de Odoo con el margen, o el tipo fijo), los billetes entregados al
tipo aplicado al cambio (el tipo de cambio de vuelta fijo cuando está
establecido). Los billetes entregados se redondean *hacia abajo* al
**redondeo de vuelta** de su divisa, de modo que el cajero nunca tenga que
entregar monedas que no existen en el cajón; el resto queda en la
comisión.

Trabajo diario
==============

Cambiar divisas
---------------

Desde cualquier pantalla de la caja, abra el menú (arriba a la derecha) y
pulse **Cambio de divisas**:

1. elija la divisa **recibida del cliente** y escriba el importe;
2. elija la divisa **entregada**; el importe, el tipo aplicado (comisión
   incluida) y la comisión se calculan a medida que escribe. El botón de
   flecha intercambia las dos divisas;
3. cuando el valor de los billetes recibidos supera el umbral del punto de
   venta, pulse **Cliente** y elija el cliente (créelo si es necesario); el
   botón permanece en rojo hasta que se hace;
4. añada una nota si resulta útil y pulse **Confirmar**. El cajón se abre,
   se imprime el recibo de cambio (recibido, entregado, tipo, comisión) y
   una notificación resume la operación.

La caja rechaza una operación cuando el cajón de la divisa entregada no
contiene suficientes billetes, cuando el importe es demasiado pequeño para
un solo billete, o cuando se elige la misma divisa en ambos lados.

Cierre de la sesión
-------------------

La ventana de cierre muestra un bloque **Cambio de divisas** con el número
de operaciones, cada operación (recibido, entregado, cajero) y el total de
las comisiones. Los billetes recibidos y entregados ya están incluidos en
los importes esperados de sus divisas: un cambio es una entrada de
efectivo en un cajón y una salida en el otro, ambas listadas en los
movimientos de la divisa.

Revisar las operaciones
-----------------------

*Punto de Venta -> Pedidos -> Cambios de divisas* lista cada operación con
su referencia, fecha, punto de venta, sesión, cajero, cliente, los
billetes recibidos y entregados, el tipo y la comisión; agrupe por punto
de venta, sesión, cajero o divisa, y cambie a la tabla dinámica para las
comisiones por día y divisa. El formulario de sesión tiene un botón
**Comisiones de cambio** con el total de las comisiones.

El informe *Detalles de ventas* de una sesión termina con una tabla
*Cambio de divisas* (operaciones y comisiones), y el informe *Posición en
divisas* de POS Multi-Currency Cash refleja los billetes movidos.

Notas contables
===============

* Una operación consta de dos líneas de extracto del diario de caja de la
  sesión: los billetes recibidos (positiva, en su divisa, valorada al tipo
  de caja) y los billetes entregados (negativa, en su divisa, valorada al
  tipo de cambio de vuelta). Una línea en la divisa del punto de venta no
  lleva divisa extranjera.
* Ambas líneas utilizan la **cuenta de comisión** como contrapartida: la
  diferencia entre los dos valores, la comisión, es lo que queda en esa
  cuenta. No se contabiliza ningún asiento aparte para la comisión.
* El margen entre los tipos de caja y los tipos de Odoo se realiza como en
  cualquier venta en divisa extranjera: al depositar los billetes o al
  revalorizar el cajón (véase la guía de POS Multi-Currency Cash).
* Las operaciones pueden abrirse desde su formulario (botón *Líneas de
  extracto*) y no pueden editarse; una operación equivocada se corrige con
  una operación inversa o un movimiento de caja.

Limitaciones conocidas
======================

* La ventanilla funciona en línea: el cálculo y el registro son llamadas
  al servidor.
* Una operación implica dos divisas; un cliente que cambia varias divisas
  a la vez genera varias operaciones.
* El recibo se imprime a través de la impresora de tickets de la caja o
  del navegador; no existe el envío por correo electrónico del recibo de
  cambio.

Solución de problemas
=====================

La entrada Cambio de divisas no aparece en el menú
--------------------------------------------------

Compruebe que **Cambio de divisas** está activado en el punto de venta, y
cierre y vuelva a abrir la caja: el ajuste se lee al cargar sus datos.

La operación se rechaza por la cuenta de comisión
-------------------------------------------------

Indique la **Cuenta de comisión** en la sección *Cambio de divisas* de los
ajustes del punto de venta.

El importe entregado es inferior al esperado
--------------------------------------------

Los billetes entregados se redondean hacia abajo al **redondeo de vuelta**
de su divisa, y la comisión incluye el resto. Reduzca el redondeo de la
divisa, o compruebe su comisión.

Aviso legal
===========

Este módulo lo proporciona Natimai Solutions bajo la Odoo Proprietary
License v1.0. Las operaciones de cambio pueden estar reguladas en su país
(licencias, identificación del cliente, registros): el módulo registra las
operaciones y su cliente, pero el cumplimiento de la normativa local sigue
siendo responsabilidad de la empresa.

Soporte
=======

* Correo electrónico: odoo@natimai.solutions
* Sitio web: https://www.natimai.solutions

Licencia
========

OPL-1 (Odoo Proprietary License), véase el archivo ``LICENSE`` del módulo.
