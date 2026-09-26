===============
POS Geldwechsel
===============

Ein Wechselschalter im Odoo 20 Kassensystem: Der Kunde bringt Scheine in
einer Währung mit und geht mit Scheinen einer anderen, abzüglich einer
Provision. Aufgebaut auf POS Multi-Currency Cash, das die Schublade jeder
Währung, ihre Bargeldkurse sowie ihre Münzen und Scheine kontrolliert.

Überblick
=========

Geschäfte in Touristengebieten, Hotels, Campingplätzen oder Grenzstädten
werden regelmäßig gebeten, Geld zu wechseln. Mit POS Multi-Currency Cash
akzeptiert die Kasse bereits fremde Scheine und gibt Wechselgeld in einer
Fremdwährung zurück; dieses Modul fügt den Vorgang ohne Verkauf hinzu:

* der Kassierer öffnet den Eintrag **Geldwechsel** im Menü der Kasse, wählt
  die erhaltene und die ausgezahlte Währung und gibt den erhaltenen Betrag
  ein;
* die Kasse berechnet den auszuzahlenden Betrag zu den Bargeldkursen der
  Kasse, mit der Provision der Währung und der Rundung auf ihre Münzen und
  Scheine;
* der Vorgang wird mit dem Kassierer und, falls erforderlich, dem Kunden
  erfasst, und ein Wechselbeleg wird gedruckt;
* beide Schubladen bewegen sich: Die erhaltenen Scheine gehen in die
  Schublade ihrer Währung ein, und die ausgezahlten Scheine verlassen die
  andere, auf dem Kassenjournal der Sitzung, mit der Provision gebucht auf
  ein eigenes Ertragskonto;
* die Vorgänge erscheinen in der Abschlusskontrolle, im Bericht
  *Währungsposition* und im Bericht *Verkaufsdetails* und werden je Kasse,
  Sitzung und Kassierer aufgelistet, mit einer Pivot-Ansicht der
  Provisionen.

Voraussetzungen
===============

* Die Anwendung **Kassensystem** (``point_of_sale``), Odoo 20.
* **POS Multi-Currency Cash** (``pos_nm_multicurrencies``) 20.0, mit
  mindestens einer Fremdwährung auf der Bargeld-Zahlungsmethode der Kasse
  (siehe dessen Anleitung: *Eine Währung in bar akzeptieren*).
* Ein **Ertragskonto für die Provisionen**.

Konfiguration
=============

Den Wechselschalter aktivieren
------------------------------

Gehen Sie zu *Kassensystem -> Konfiguration -> Einstellungen*, wählen Sie
Ihre Kasse und sehen Sie sich den Abschnitt **Geldwechsel** an:

* **Geldwechsel** (standardmäßig aktiv): zeigt den Eintrag im Menü der
  Kasse.
* **Konto für Wechselprovisionen**: Ertragskonto, auf dem die Provisionen
  gebucht werden. Es ist erforderlich, um einen Vorgang zu erfassen.
* **Kunde erforderlich ab**: Wert eines Vorgangs, in der Währung der Kasse,
  ab dem der Kunde erfasst werden muss. 0: nie.

Provisionen je Währung
----------------------

Gehen Sie zu *Kassensystem -> Konfiguration -> Bargeldwährungen* und öffnen
Sie die Zeile der Währung. Die Gruppe *Geldwechsel* enthält drei Werte, alle
in der Währung der Kasse außer dem Prozentsatz:

* **Wechselprovision (%)**: Prozentsatz des Wertes der erhaltenen Scheine;
* **Feste Wechselprovision**: fester Teil, der zum Prozentsatz addiert
  wird;
* **Mindestwechselprovision**: die Provision beträgt mindestens diesen
  Betrag.

Die Provision eines Vorgangs ist die der beteiligten Fremdwährung (die
ausgezahlte Währung, wenn beide fremd sind). Jede Änderung der Provisionen
wird im Chatter der Zeile protokolliert, wie die Kurse.

Kurse sowie Münzen und Scheine
------------------------------

Der Schalter verwendet die Bargeldkurse von POS Multi-Currency Cash: Die
erhaltenen Scheine werden zu dem Kurs bewertet, der für das gilt, was ein
Kunde zahlt (Kurs von Odoo mit Marge, oder der feste Kurs), die ausgezahlten
Scheine zu dem Kurs, der für das Wechselgeld gilt (der feste
Wechselgeldkurs, falls gesetzt). Die ausgezahlten Scheine werden *abgerundet*
auf die **Wechselgeldrundung** ihrer Währung, sodass der Kassierer nie
Münzen auszahlen muss, die in der Schublade nicht existieren; der Rest
bleibt in der Provision.

Täglicher Ablauf
================

Währungen wechseln
------------------

Öffnen Sie von jedem Bildschirm der Kasse aus das Menü (oben rechts) und
drücken Sie **Geldwechsel**:

1. wählen Sie die vom Kunden **erhaltene** Währung und geben Sie den Betrag
   ein;
2. wählen Sie die **ausgezahlte** Währung; der Betrag, der angewendete Kurs
   (Provision inbegriffen) und die Provision werden während der Eingabe
   berechnet. Die Pfeilschaltfläche tauscht die beiden Währungen;
3. überschreitet der Wert der erhaltenen Scheine den Schwellenwert der
   Kasse, drücken Sie **Kunde** und wählen Sie den Kunden (legen Sie ihn
   bei Bedarf an); die Schaltfläche bleibt rot, bis dies erledigt ist;
4. fügen Sie bei Bedarf eine Notiz hinzu und drücken Sie dann
   **Bestätigen**. Die Kassenschublade öffnet sich, der Wechselbeleg wird
   gedruckt (erhalten, ausgezahlt, Kurs, Provision), und eine
   Benachrichtigung fasst den Vorgang zusammen.

Die Kasse lehnt einen Vorgang ab, wenn die Schublade der ausgezahlten
Währung nicht genug Scheine enthält, wenn der Betrag für einen einzelnen
Schein zu gering ist, oder wenn auf beiden Seiten dieselbe Währung gewählt
wird.

Sitzung schließen
-----------------

Das Schließfenster zeigt einen Block **Geldwechsel** mit der Anzahl der
Vorgänge, jedem Vorgang (erhalten, ausgezahlt, Kassierer) und der Summe der
Provisionen. Die erhaltenen und ausgezahlten Scheine sind bereits in den
erwarteten Beträgen ihrer Währungen enthalten: Ein Wechselvorgang ist eine
Einzahlung in einer Schublade und eine Auszahlung aus der anderen, beide in
den Bewegungen der Währung aufgelistet.

Die Vorgänge prüfen
-------------------

*Kassensystem -> Aufträge -> Geldwechsel* listet jeden Vorgang mit
Referenz, Datum, Kasse, Sitzung, Kassierer, Kunde, den erhaltenen und
ausgezahlten Scheinen, dem Kurs und der Provision auf; gruppieren Sie nach
Kasse, Sitzung, Kassierer oder Währung, und wechseln Sie zur Pivot-Ansicht
für die Provisionen je Tag und Währung. Das Sitzungsformular hat eine
Schaltfläche **Wechselvorgänge** mit der Summe der Provisionen.

Der Bericht *Verkaufsdetails* einer Sitzung endet mit einer Tabelle
*Geldwechsel* (Vorgänge und Provisionen), und der Bericht
*Währungsposition* von POS Multi-Currency Cash spiegelt die bewegten
Scheine wider.

Buchhalterische Hinweise
========================

* Ein Vorgang besteht aus zwei Kontoauszugszeilen des Kassenjournals der
  Sitzung: den erhaltenen Scheinen (positiv, in ihrer Währung, bewertet zum
  Bargeldkurs) und den ausgezahlten Scheinen (negativ, in ihrer Währung,
  bewertet zum Wechselgeldkurs). Eine Zeile in der Währung der Kasse trägt
  keine Fremdwährung.
* Beide Zeilen verwenden das **Konto für Wechselprovisionen** als
  Gegenbuchung: Die Differenz zwischen den beiden Werten, die Provision,
  ist das, was auf diesem Konto verbleibt. Für die Provision wird keine
  eigene Buchung erzeugt.
* Die Marge zwischen den Bargeldkursen und den Kursen von Odoo wird
  realisiert wie bei jedem Verkauf in einer Fremdwährung: bei der
  Einzahlung der Scheine oder bei der Neubewertung der Schublade (siehe die
  Anleitung von POS Multi-Currency Cash).
* Die Vorgänge können über ihr Formular geöffnet werden (Schaltfläche
  *Kontoauszugszeilen*) und können nicht bearbeitet werden; ein
  fehlerhafter Vorgang wird durch einen entgegengesetzten Vorgang oder eine
  Kassenbewegung korrigiert.

Bekannte Einschränkungen
========================

* Der Schalter arbeitet online: Das Angebot und die Erfassung sind
  Serveraufrufe.
* Ein Vorgang betrifft zwei Währungen; ein Kunde, der mehrere Währungen auf
  einmal wechselt, erzeugt mehrere Vorgänge.
* Der Beleg wird über den Bondrucker der Kasse oder den Browser gedruckt;
  es gibt keinen Versand des Wechselbelegs per E-Mail.

Fehlerbehebung
==============

Der Eintrag Geldwechsel fehlt im Menü
-------------------------------------

Prüfen Sie, ob **Geldwechsel** an der Kasse aktiviert ist, und schließen und
öffnen Sie die Kasse dann erneut: Die Einstellung wird beim Laden ihrer
Daten gelesen.

Der Vorgang wird wegen des Kontos für Wechselprovisionen abgelehnt
------------------------------------------------------------------

Setzen Sie das **Konto für Wechselprovisionen** im Abschnitt *Geldwechsel*
der Einstellungen der Kasse.

Der ausgezahlte Betrag ist niedriger als erwartet
-------------------------------------------------

Die ausgezahlten Scheine werden auf die **Wechselgeldrundung** ihrer
Währung abgerundet, und die Provision enthält den Rest. Verringern Sie die
Rundung der Währung, oder prüfen Sie ihre Provision.

Haftungsausschluss
==================

Dieses Modul wird von Natimai Solutions unter der Odoo Proprietary License
v1.0 bereitgestellt. Wechselvorgänge können in Ihrem Land reguliert sein
(Zulassung, Identifizierung des Kunden, Register): Das Modul erfasst die
Vorgänge und ihren Kunden, aber die Einhaltung der örtlichen Vorschriften
bleibt in der Verantwortung des Unternehmens.

Support
=======

* E-Mail: odoo@natimai.solutions
* Website: https://www.natimai.solutions

Lizenz
======

OPL-1 (Odoo Proprietary License), siehe die Datei ``LICENSE`` des Moduls.
