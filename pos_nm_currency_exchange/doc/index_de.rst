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
  ein, oder den Betrag, den der Kunde ausgezahlt haben möchte;
* die Kasse berechnet den Vorgang: erhaltene Scheine zum Kassenkurs der
  Kasse (dem Ankaufskurs), ausgezahlte Scheine zum Verkaufskurs des
  Schalters, die Provision der Währung, die Rundung auf Münzen und Scheine
  und den Inhalt der Schublade;
* der Vorgang wird mit dem Kassierer und, falls erforderlich, dem Kunden
  und seinem Ausweisdokument erfasst, und ein Wechselbeleg wird gedruckt;
* beide Schubladen bewegen sich: Die erhaltenen Scheine gehen in die
  Schublade ihrer Währung ein, und die ausgezahlten Scheine verlassen die
  andere, auf dem Kassenjournal der Sitzung, mit der Provision gebucht auf
  ein eigenes Ertragskonto;
* ein Manager kann einen fehlerhaften Vorgang stornieren, solange die
  Sitzung geöffnet ist;
* die Vorgänge erscheinen in der Abschlusskontrolle, im Bericht
  *Währungsposition* und im Bericht *Verkaufsdetails*, in einer Liste mit
  einer Pivot-Ansicht der Provisionen und Kursmargen und in einem
  Wechselregister, das für einen Zeitraum exportiert oder gedruckt werden
  kann;
* die Kurstafel des Schalters kann an der Kasse angezeigt und gedruckt
  oder als PDF gedruckt werden.

Voraussetzungen
===============

* Die Anwendung **Kassensystem** (``point_of_sale``), Odoo 20.
* **POS Multi-Currency Cash** (``pos_nm_multicurrencies``) **20.0.2.1.0
  oder neuer**, separat erhältlich, mit mindestens einer Fremdwährung auf
  der Bargeld-Zahlungsmethode der Kasse (siehe dessen Anleitung: *Eine
  Währung in bar akzeptieren*). Eine ältere Version von POS Multi-Currency
  Cash funktioniert mit diesem Modul nicht: Aktualisieren Sie sie zuerst.
* Ein **Ertragskonto für die Provisionen** (Typ *Einkommen* oder
  *Sonstige betriebliche Erträge*).

Konfiguration
=============

Den Wechselschalter aktivieren
------------------------------

Gehen Sie zu *Kassensystem -> Konfiguration -> Einstellungen*, wählen Sie
Ihre Kasse und suchen Sie den Abschnitt **Geldwechsel**:

* **Geldwechsel** (standardmäßig aktiviert): zeigt die Einträge des
  Schalters im Menü der Kasse.
* **Provisionskonto**: Ertragskonto, auf dem die Provisionen gebucht
  werden. Nur Ertragskonten können gewählt werden. Es ist erforderlich, um
  einen Vorgang zu erfassen.
* **Wechsellizenznummer**: Lizenz- oder Registrierungsnummer Ihrer
  Geldwechseltätigkeit, auf den Belegen und der Kurstafel gedruckt, wenn
  angegeben.
* **Kunde erforderlich ab**: Wert eines Vorgangs in der Währung der Kasse,
  ab dem der Kunde erfasst werden muss.
* **Kunde für jeden Vorgang erforderlich**: Jeder Vorgang nennt seinen
  Kunden.
* **Ausweisdokument erforderlich ab**: Wert, ab dem das Ausweisdokument
  des Kunden auf dem Vorgang erfasst wird.
* **Zeitraum der verbundenen Vorgänge (Tage)**: Wenn größer als 0, ist der
  mit den beiden Schwellen verglichene Wert der Vorgang plus die Vorgänge
  desselben Kunden in so vielen Tagen (siehe *Kundenidentifikation*).
* **Wechselkurse drucken**: druckt die Kurstafel der Kasse als PDF.

Schwellen auf 0 werden nie angewendet.

Provisionen und Verkaufsmarge je Währung
----------------------------------------

Gehen Sie zu *Kassensystem -> Konfiguration -> Bargeldwährungen* und
öffnen Sie die Zeile der Währung. Die Gruppe *Geldwechsel* enthält vier
Werte, wobei die Beträge in der Währung der Kasse sind:

* **Wechsel-Verkaufsmarge (%)**: Marge des Schalters auf die Scheine
  dieser Währung, die er auszahlt (siehe *Kurse* unten). Bei einem festen
  Kassenkurs ausgeblendet, da dort nicht verwendet;
* **Wechselprovision (%)**: Prozentsatz des Wertes der erhaltenen
  Scheine;
* **Feste Wechselprovision**: fester Teil, der zum Prozentsatz hinzukommt;
* **Mindestwechselprovision**: Die Provision beträgt mindestens diesen
  Betrag.

Die Provision eines Vorgangs ist die der beteiligten Fremdwährung (die
ausgezahlte Währung, wenn beide fremd sind). Jede Änderung dieser Werte
wird im Chatter der Zeile protokolliert, wie die Kurse.

Kurse
-----

Der Schalter kauft zu einem Kurs und verkauft zu einem anderen, immer
zugunsten des Geschäfts. Die Kurse werden als Einheiten der Fremdwährung
für eine Einheit der Währung der Kasse angegeben, wie in POS
Multi-Currency Cash:

* **Erhaltene Scheine** (Ankaufskurs): der Kassenkurs von POS
  Multi-Currency Cash, also der Odoo-Kurs mit der **Kassenkurs-Marge (%)**
  der Währung, oder ihr **Fester Kurs**.
* **Ausgezahlte Scheine** (Verkaufskurs): der Odoo-Kurs geteilt durch 1 +
  die **Wechsel-Verkaufsmarge**. Bei einem festen Kassenkurs der
  niedrigere Wert aus **Fester Kurs** und **Fester Wechselgeldkurs** (ein
  Fester Wechselgeldkurs von 0 bedeutet den Festen Kurs): Der niedrigere
  Kurs zahlt weniger Scheine aus.

Beispiel: Kasse in USD, Odoo-Kurs 2 EUR für 1 USD, Kassenkurs-Marge und
Wechsel-Verkaufsmarge von 10 %: Der Schalter kauft Euro zu 2,20 EUR für
1 USD (100 erhaltene EUR sind 45,45 $ wert) und verkauft sie zu 1,82 EUR
für 1 USD (100 ausgezahlte EUR sind 55,00 $ wert), vor der Provision.

Der Unterschied zu den Odoo-Kursen ist die **Kursmarge** des Vorgangs
(siehe *Buchhalterische Hinweise*). Bei einer Aktualisierung von einer
Version vor 20.0.2.0.0 wird die Wechsel-Verkaufsmarge jeder Währung auf
ihre Kassenkurs-Marge gesetzt: Prüfen Sie sie.

Münzen und Scheine
------------------

Die ausgezahlten Scheine werden einmal *abgerundet*, auf die kleinste
Münze oder den kleinsten Schein ihrer Währung, damit der Kassierer nie
Münzen auszahlen muss, die es in der Schublade nicht gibt; der Rest
bleibt in der Provision, die nie unter der eingestellten liegt:

* eine Fremdwährung: ihre **Wechselgeldrundung**, sonst die Rundung der
  Währung;
* die Währung der Kasse: das Rundungsverfahren der **Gesamtrundung** in
  den Einstellungen der Kasse, wenn aktiviert, sonst die Rundung der
  Währung.

Beleg
-----

Der Wechselbeleg druckt das Logo, die **Kopfzeile** und die **Fußzeile**
der Kasse (*Einstellungen*, Abschnitt *Rechnungen & Quittungen*,
*Benutzerdefinierte Kopf- & Fußzeile*), die Wechsellizenznummer und die
Angaben des Unternehmens. Tragen Sie dort die rechtlichen Hinweise ein,
die Ihre Tätigkeit dem Kunden zeigen muss.

Wer darf was
------------

* **Kassenbenutzer** (Kassierer) erfassen Vorgänge an der Kasse, drucken
  ihre Belege nach und zeigen die Kurstafel. Sie können die Vorgänge lesen,
  aber nicht ändern.
* **Kassenadministratoren** (Zugriff *Kassensystem*: *Administrator*)
  sehen zusätzlich die Menüs *Kassensystem -> Aufträge -> Geldwechsel* und
  *Kassensystem -> Berichtswesen -> Wechselregister* und die
  Ausweisdokumente der Kunden, können die Notiz eines Vorgangs bearbeiten
  und einen Vorgang stornieren.
* Niemand kann einen Vorgang oder eine seiner Kontoauszugszeilen löschen.
* Bei mehreren Unternehmen sieht jeder Benutzer die Vorgänge der
  Unternehmen, auf die er Zugriff hat.
* Mit dem Modul Mitarbeiter (``pos_hr``) ist der Kassierer eines Vorgangs
  der an der Kasse angemeldete Mitarbeiter, der für die Kasse zugelassen
  sein muss; sonst ist es der Benutzer.

Täglicher Ablauf
================

Währungen wechseln
------------------

Öffnen Sie von einem beliebigen Bildschirm der Kasse das Menü (oben
rechts) und tippen Sie auf **Geldwechsel**:

1. wählen Sie die **vom Kunden erhaltene** Währung und geben Sie den
   Betrag ein;
2. wählen Sie die **an den Kunden ausgezahlte** Währung. Der ausgezahlte
   Betrag, der Kurs, der Wert der erhaltenen Scheine, die Provision und
   der Bestand der Schublade (**In der Schublade**) werden während der
   Eingabe berechnet. Die Pfeiltaste tauscht die beiden Währungen;
3. wenn der Kunde einen genauen Betrag wünscht, geben Sie ihn stattdessen
   im Feld **An den Kunden ausgezahlt** ein: Der zu erhaltende Betrag wird
   berechnet, auf die Münzen der erhaltenen Währung aufgerundet, und der
   Hinweis „Zu erhaltender Betrag aus dem ausgezahlten Betrag berechnet.“
   erscheint. Beim Verlassen des Feldes zeigt es den tatsächlich
   ausgezahlten Betrag, der etwas höher sein kann, wenn die Scheine den
   Betrag nicht genau ergeben. Eine erneute Eingabe in **Vom Kunden
   erhalten** kehrt zur normalen Berechnung zurück;
4. wenn der Kunde erfasst werden muss, wird die Schaltfläche **Kunde** rot
   mit dem Grund: Tippen Sie darauf und wählen Sie den Kunden (legen Sie
   ihn bei Bedarf an). Wenn das Ausweisdokument erforderlich ist,
   erscheinen seine Felder, vorausgefüllt aus dem Kontakt: Art, Nummer und
   Ablaufdatum sind Pflichtfelder;
5. fügen Sie bei Bedarf eine Notiz hinzu und tippen Sie auf
   **Bestätigen**. Die Kassenschublade öffnet sich, der Wechselbeleg wird
   gedruckt und eine Benachrichtigung fasst den Vorgang zusammen.

**Bestätigen** bleibt deaktiviert, solange eine Berechnung läuft und wenn
die Schublade der ausgezahlten Währung den Betrag nicht enthält (die Zeile
*In der Schublade* ist dann rot, mit der Ablehnung).

Bricht die Verbindung beim Bestätigen ab, meldet das Fenster, dass der
Vorgang möglicherweise erfasst wurde: Bestätigen Sie erneut, sobald die
Verbindung wiederhergestellt ist. Ein bereits erfasster Vorgang wird nicht
doppelt erfasst, und sein Beleg wird gedruckt.

Wenn der Schalter an dieser Kasse nicht arbeiten kann, zeigt der Eintrag
**Geldwechsel** den Grund statt des Fensters: keine Fremdwährung auf der
Bargeld-Zahlungsmethode oder kein Provisionskonto.

Der Münzhinweis
---------------

Ein orangefarbener Hinweis erscheint, wenn der in einer Fremdwährung
erhaltene Betrag nicht mit ihren Münzen und Scheinen zusammengesetzt
werden kann, zum Beispiel 1.106 XPF mit 5-XPF-Münzen. Geprüft wird die
**Zahlungsrundung** der Währung, sonst ihre **Wechselgeldrundung**, wenn
ihr **Rest des Wechselgelds** auf *Als Rundung behalten* steht. Der
Hinweis blockiert den Vorgang nicht: Prüfen Sie die tatsächlich erhaltenen
Scheine und korrigieren Sie den Betrag bei Bedarf.

Ablehnungen
-----------

Die Kasse lehnt einen Vorgang mit einer Meldung ab, wenn:

* die Schublade der ausgezahlten Währung den Betrag nicht enthält,
  einschließlich der Währung der Kasse (der Bestand ist der der
  Abschlusskontrolle: Anfangsbestand, Barverkäufe und Wechselgeld,
  Bargeldbewegungen und Geldwechsel der Sitzung);
* der Betrag zu gering ist: Nach Abzug der Provision kann kein Schein
  ausgezahlt werden;
* auf beiden Seiten dieselbe Währung gewählt ist;
* der Kunde oder ein gültiges Ausweisdokument erforderlich ist und fehlt,
  oder das Dokument abgelaufen ist;
* sich das Angebot zwischen Fenster und Server geändert hat (Kurs, Marge
  oder Provision inzwischen geändert): „Das Angebot hat sich geändert:
  ...“. Geben Sie den Betrag erneut ein, um das neue Angebot zu erhalten,
  und bestätigen Sie dann;
* die Sitzung nicht geöffnet oder der Schalter deaktiviert ist.

Einen Beleg nachdrucken
-----------------------

Der Eintrag **Wechselvorgänge** im Menü der Kasse listet die Vorgänge der
Sitzung (Referenz, Datum, Vorgang, erhalten, ausgezahlt, Kunde).
**Nachdrucken** druckt den Beleg erneut, mit *KOPIE* gekennzeichnet; ein
inzwischen stornierter Vorgang ist mit *STORNIERT* sowie Datum und Uhrzeit
gekennzeichnet.

Die Kurse anzeigen
------------------

Der Eintrag **Wechselkurse** im Menü der Kasse zeigt die Kurstafel des
Schalters, eine Zeile je Fremdwährung in bar:

* **Wir kaufen**: Wert von 1 Einheit der erhaltenen Scheine (Kassenkurs,
  vor der Provision), und **Sie erhalten**: was der Kunde für einen
  typischen Betrag erhält, Provision abgezogen und auf die Scheine
  gerundet;
* **Wir verkaufen**: Preis von 1 Einheit der ausgezahlten Scheine
  (Verkaufskurs, vor der Provision), und **Sie zahlen**: was der Kunde für
  einen typischen Betrag zahlt, Provision inbegriffen;
* **Provision**: Prozentsatz, fester Teil und Minimum.

Der typische Betrag ist die Zehnerpotenz, die 100 Einheiten der Währung
der Kasse am nächsten liegt (100 EUR, 10.000 XPF, 1.000.000 VND). Die
Beträge werden mit dem Angebot des Schalters berechnet und stimmen daher
mit den Vorgängen überein. **Drucken** druckt die Tafel auf dem
Bondrucker.

Einen Vorgang stornieren
------------------------

Ein fehlerhafter Vorgang wird storniert, nicht durch einen anderen
Vorgang korrigiert: Ein Gegenvorgang würde die Provision erneut berechnen
und die Scheine erneut runden, und eine Bargeldbewegung würde die
Provision auf dem Provisionskonto lassen.

Ein Kassenadministrator öffnet den Vorgang (*Kassensystem -> Aufträge ->
Geldwechsel*), tippt auf **Vorgang stornieren** und bestätigt. Das ist
möglich, solange die Sitzung des Vorgangs geöffnet ist und die Schublade
die erhaltenen Scheine noch enthält (der Kunde erhält sie zurück). Zwei
Kontoauszugszeilen, die den ursprünglichen genau entgegengesetzt sind,
werden in der Sitzung gebucht: gleiche Beträge in beiden Währungen,
gleiches Gegenkonto. Beide Schubladen und das Provisionskonto kehren in
ihren Zustand vor dem Vorgang zurück.

Der Vorgang wird **Storniert**, mit Datum und Benutzer, eine Nachricht
wird in der Sitzung und im Vorgang veröffentlicht, und er zählt nicht mehr
in den Provisionen, der Abschlusszusammenfassung und den Berichten. Sein
nachgedruckter Beleg ist mit *STORNIERT* gekennzeichnet.

Nach dem Schließen der Sitzung kann ein Vorgang nicht mehr storniert
werden. Korrigieren Sie ihn dann mit einem Gegenvorgang (Provision und
Rundung gelten erneut; setzen Sie die Provision der Währung so lange auf
0, wenn Sie sie erstatten) oder mit Bargeldbewegungen in jeder Währung,
und bitten Sie Ihren Buchhalter, die Provision vom Provisionskonto
zurückzubuchen.

Sitzung schließen
-----------------

Das Abschlussfenster zeigt einen Block **Geldwechsel**, sobald die Sitzung
Vorgänge hat: die Anzahl der Vorgänge, jeden Vorgang (erhalten,
ausgezahlt, Kassierer), die Summe der Provisionen, die **Kursmarge** und
die Anzahl der stornierten Vorgänge. Die erhaltenen und ausgezahlten
Scheine sind bereits in den erwarteten Beträgen ihrer Währungen
enthalten: Ein Geldwechsel ist eine Einzahlung in eine Schublade und eine
Auszahlung aus der anderen, beide in den Bewegungen der Währung
aufgeführt.

Kundenidentifikation
====================

Die Schwellen helfen Ihnen, die Identifikationsregeln Ihres Landes
anzuwenden; das Modul erfasst, was der Kassierer eingibt, es prüft
Ausweisdokumente nicht gegen ein Register.

* Der mit den Schwellen verglichene Wert ist der Wert der erhaltenen
  Scheine in der Währung der Kasse.
* Mit einem **Zeitraum der verbundenen Vorgänge** werden die erledigten
  (nicht stornierten) Vorgänge desselben Kunden der letzten Tage, an allen
  Kassen des Unternehmens, hinzugerechnet, umgerechnet in die Währung der
  Kasse. Das Fenster zeigt dann „Mit den verbundenen Vorgängen des Kunden“
  und die Summe. Ohne Kunden zählt nur der Vorgang: Aktivieren Sie **Kunde
  für jeden Vorgang erforderlich**, damit die Regel immer gilt.
* Über **Kunde erforderlich ab** erfordert der Vorgang einen Kunden.
* Über **Ausweisdokument erforderlich ab** erfordert er einen Kunden und
  ein gültiges Ausweisdokument: Art (Reisepass, Personalausweis,
  Führerschein, Aufenthaltstitel, Andere), Nummer, Ausstellungsland,
  Ablaufdatum, Staatsangehörigkeit und Geburtsdatum. Ein abgelaufenes
  Dokument wird abgelehnt.

Der Server prüft diese Regeln beim Erfassen erneut. Das an der Kasse
eingegebene Dokument wird im Kontakt gespeichert (Reiter
**Ausweisdokument** des Kontaktformulars), und eine Kopie wird mit dem
Namen des Kunden im Vorgang aufbewahrt: Spätere Änderungen oder
Umbenennungen des Kontakts ändern die erfassten Vorgänge nicht. Der Beleg
druckt den Namen des Kunden und die Dokumentart mit nur den letzten
4 Zeichen der Nummer (zum Beispiel „Reisepass \*\*\*\*4567“).

Die Ausweisdokumente sind nur für Kassenadministratoren sichtbar; der
Kassierer sieht das Dokument des gewählten Kunden im Fenster.

Die Vorgänge prüfen
===================

Geldwechsel
-----------

*Kassensystem -> Aufträge -> Geldwechsel* (Kassenadministratoren) listet
die Vorgänge mit Referenz, Datum, Kasse, Kassierer, Kunde, den erhaltenen
und ausgezahlten Scheinen, der Provision, der Kursmarge und dem Status.
Die Liste öffnet sich mit dem Filter **Erledigt**; der Filter
**Storniert** zeigt die stornierten. Weitere Filter: *Heute*, *Mit Kunde*,
*Ankauf von Fremdwährung*, *Verkauf von Fremdwährung*, *Kreuzwechsel*;
Gruppierung nach Kasse, Sitzung, Kassierer, Vorgangsart, Status, Währung
oder Datum. Die Pivot-Ansicht liefert Provisionen, Kursmargen und
erhaltene Werte je Tag, Status und Währung.

Die Vorgangsart ist aus Sicht des Geschäfts angegeben: *Ankauf von
Fremdwährung*, wenn es Fremdwährungsscheine erhält, *Verkauf von
Fremdwährung*, wenn es Fremdwährungsscheine auszahlt, *Kreuzwechsel*
zwischen zwei Fremdwährungen.

Das Formular eines Vorgangs zeigt seine Beträge, den Kurs (**Angewandter
Kurs**, „1 USD = 119,33 XPF“), die Provision, die Kursmarge, das
Ausweisdokument und den Chatter. Seine Schaltflächen:

* **Per E-Mail senden** (wenn der Vorgang einen Kunden hat): sendet den
  Beleg als PDF mit der Vorlage *Geldwechsel: Beleg senden*;
* **Drucken**: der Beleg als PDF (*Wechselbeleg*);
* **Vorgang stornieren** (siehe oben);
* **Kontoauszugszeilen**: die zwei Zeilen des Vorgangs und die zwei
  Zeilen seiner Stornierung.

Nur die **Notiz** kann bearbeitet werden, von einem Kassenadministrator;
ihre Änderungen werden im Chatter protokolliert.

Das Sitzungsformular hat eine Schaltfläche mit der Summe der Provisionen
und „Vorgänge: N“, der Anzahl der erledigten Vorgänge; sie öffnet diese.

Verkaufsdetails
---------------

Der Bericht *Verkaufsdetails* endet mit einer Tabelle *Geldwechsel*:
jeder Vorgang mit seiner Sitzung, seinen Beträgen, seiner Provision und
seiner Kursmarge, dann die Summen, eine Zeile je Währung der Kassen, und
die Liste der stornierten Vorgänge, die nicht gezählt werden. Aus einer
Sitzung gedruckt, umfasst er die Vorgänge der Sitzung; über *Kassensystem
-> Berichtswesen -> Verkaufsdetails* für einen Zeitraum erstellt, umfasst
er die Vorgänge dieses Zeitraums an den gewählten Kassen (allen, wenn
keine gewählt ist), geöffnete Sitzungen eingeschlossen. Der Bericht
*Währungsposition* von POS Multi-Currency Cash spiegelt die bewegten
Scheine wider.

Wechselregister
---------------

*Kassensystem -> Berichtswesen -> Wechselregister*
(Kassenadministratoren) listet jeden Vorgang in der Reihenfolge seiner
Referenz, einschließlich der stornierten (ausgegraut, mit ihrem Status),
mit Kassierer, Vorgangsart, Beträgen, Kurs, Provision, Kursmarge,
Kundenname und Ausweisdokument. Die Referenzen folgen lückenlos
aufeinander. Exportieren Sie es mit der Standardaktion *Exportieren* nach
Excel.

**Register drucken** fragt nach einem Zeitraum (**Von**, **Bis**,
standardmäßig vom Monatsanfang bis jetzt) und den **Kassen** (alle, wenn
leer) und druckt das Register als PDF (A4 quer) mit den Summen je Währung:
Anzahl der Vorgänge, erhalten, ausgezahlt, Saldo, Provisionen und
Kursmargen. Die stornierten Vorgänge sind aufgeführt, aber nicht in den
Summen gezählt.

Kurstafel als PDF
-----------------

Die oben beschriebene Kurstafel wird auch als PDF (*Wechselkurse*)
gedruckt, mit **Wechselkurse drucken** in den Einstellungen oder über das
Menü *Drucken* der Kassen (Listenansicht von *Kassensystem ->
Dashboard*).

Buchhalterische Hinweise
========================

* Ein Vorgang besteht aus zwei Kontoauszugszeilen des Kassenjournals der
  Sitzung: die erhaltenen Scheine (positiv, in ihrer Währung, zu ihrem
  erhaltenen Wert) und die ausgezahlten Scheine (negativ, in ihrer
  Währung, zu ihrem ausgezahlten Wert). Eine Zeile in der Währung der
  Kasse trägt keine Fremdwährung. Die Zeilen tragen den Kassierer als
  Partner.
* Beide Zeilen verwenden das **Provisionskonto** als Gegenkonto: Die
  Differenz der beiden Werte, die Provision, verbleibt auf diesem Konto.
  Für die Provision wird keine gesonderte Buchung erstellt.
* Die **Kursmarge** eines Vorgangs ist das, was seine Kurse gegenüber den
  Odoo-Tageskursen einbringen: Wert der erhaltenen Scheine zum Odoo-Kurs
  abzüglich ihres erhaltenen Werts, plus der ausgezahlte Wert abzüglich
  des Werts der ausgezahlten Scheine zum Odoo-Kurs. Sie wird wie bei jedem
  Verkauf in Fremdwährung realisiert: durch die Neubewertung der Schublade
  von POS Multi-Currency Cash oder bei der Einzahlung der Scheine (siehe
  dessen Anleitung). Provision plus Kursmarge ist der Ertrag des
  Vorgangs. Mit festen Kursen über den Odoo-Kursen kann die Kursmarge
  negativ sein: Sie zeigt den Verlust.
* Eine Stornierung bucht zwei Zeilen, die den ursprünglichen
  entgegengesetzt sind, auf demselben Gegenkonto: Die Provision wird
  storniert.
* Die Vorgänge und ihre Kontoauszugszeilen können nicht gelöscht werden;
  die Referenzen (``EXC/JJJJ/NNNNN``) sind lückenlos.

Aktualisierung von 20.0.1.x
===========================

* Aktualisieren Sie zuerst POS Multi-Currency Cash auf 20.0.2.1.0 oder
  neuer.
* Die **Wechsel-Verkaufsmarge** jeder Währung wird auf ihre
  Kassenkurs-Marge gesetzt (0, wenn negativ): Die ausgezahlten Scheine
  werden nun zum Verkaufskurs bewertet, zugunsten des Geschäfts. Prüfen
  Sie die Margen und die Kurstafel, bevor Sie die Kassen öffnen.
* Die bereits erfassten Vorgänge erhalten Benutzer, Status, Kurs,
  Kursmarge und Kundennamen. Ihre Kursmarge wird zum Odoo-Kurs ihres Tages
  berechnet: Die früheren Vorgänge zeigen den Verlust der alten Bewertung
  der ausgezahlten Scheine.
* Die Referenzsequenz wird lückenlos. Vorgänge können nicht mehr gelöscht
  werden: Verwenden Sie **Vorgang stornieren**.
* Die Schublade der Währung der Kasse wird nun geprüft: Zählen Sie ihren
  Anfangsbestand.

Bekannte Einschränkungen
========================

* Der Schalter arbeitet online: Berechnung und Erfassung sind
  Serveraufrufe.
* Ein Vorgang betrifft zwei Währungen; ein Kunde, der mehrere Währungen
  auf einmal wechselt, ergibt mehrere Vorgänge.
* Ein Vorgang kann nur storniert werden, solange seine Sitzung geöffnet
  ist.
* Die Kurstafel wird nicht auf dem Kundendisplay angezeigt.

Fehlerbehebung
==============

Der Eintrag Geldwechsel fehlt im Menü
-------------------------------------

Prüfen Sie, ob **Geldwechsel** an der Kasse aktiviert ist, und schließen
und öffnen Sie dann die Kasse erneut: Die Einstellung wird beim Laden
ihrer Daten gelesen.

Eine Meldung erscheint statt des Fensters
-----------------------------------------

Fügen Sie der Bargeld-Zahlungsmethode der Kasse eine Fremdwährung hinzu
oder legen Sie das **Provisionskonto** im Abschnitt *Geldwechsel* der
Einstellungen fest, und laden Sie dann die Kasse neu.

Das Provisionskonto wird abgelehnt
----------------------------------

Nur ein Konto vom Typ *Einkommen* oder *Sonstige betriebliche Erträge*
kann die Provisionen aufnehmen.

Der ausgezahlte Betrag ist niedriger als erwartet
-------------------------------------------------

Die ausgezahlten Scheine werden zum Verkaufskurs bewertet und auf die
**Wechselgeldrundung** ihrer Währung abgerundet (die Gesamtrundung der
Kasse für ihre eigene Währung), und die Provision enthält den Rest.
Prüfen Sie die Wechsel-Verkaufsmarge, die Rundung und die Provision der
Währung.

Die Schublade enthält den Betrag nicht
--------------------------------------

Die Schublade der ausgezahlten Währung muss den Betrag enthalten, wie ihn
die Abschlusskontrolle zählt. Wechseln Sie in die andere Richtung oder
erfassen Sie zuerst eine Einzahlung in dieser Währung. Für die Währung der
Kasse prüfen Sie, ob der Anfangsbestand gezählt wurde.

Ein orangefarbener Hinweis zu Münzen und Scheinen
-------------------------------------------------

Der erhaltene Betrag kann nicht mit den Münzen der Währung
zusammengesetzt werden (siehe *Der Münzhinweis*). Er blockiert den
Vorgang nicht.

„Das Angebot hat sich geändert“
-------------------------------

Ein Kurs, eine Marge oder eine Provision hat sich nach dem Angebot
geändert. Geben Sie den Betrag erneut ein: Das Fenster berechnet den neuen
Betrag; bestätigen Sie dann.

Die Verbindung brach beim Bestätigen ab
---------------------------------------

Bestätigen Sie erneut, sobald die Verbindung wiederhergestellt ist: Ein
bereits erfasster Vorgang wird nicht doppelt erfasst.

Ein Vorgang kann nicht storniert werden
---------------------------------------

Nur ein Kassenadministrator kann stornieren, solange die Sitzung des
Vorgangs geöffnet ist und die Schublade die erhaltenen Scheine noch
enthält. Nach dem Schließen siehe *Einen Vorgang stornieren*.

Das Ausweisdokument wird abgelehnt
----------------------------------

Art, Nummer und Ablaufdatum sind Pflichtfelder, und das Dokument darf
nicht abgelaufen sein. Die Schwelle kann mit den verbundenen Vorgängen des
Kunden erreicht sein: Das Fenster zeigt ihre Summe.

Löschen fehlt bei den Vorgängen
-------------------------------

Die Vorgänge können nicht gelöscht werden, damit das Register vollständig
bleibt: Stornieren Sie den Vorgang stattdessen.

Der Kassierer findet Geldwechsel oder Wechselregister nicht
-----------------------------------------------------------

Diese Menüs sind Kassenadministratoren vorbehalten. Kassierer verwenden
den Eintrag **Wechselvorgänge** im Menü der Kasse.

Haftungsausschluss
==================

Dieses Modul wird von Natimai Solutions unter der Odoo Proprietary License
v1.0 bereitgestellt. Wechselvorgänge können in Ihrem Land reguliert sein
(Zulassung, Identifizierung des Kunden, Register, Meldungen): Das Modul
hilft Ihnen, die Vorgänge, ihren Kunden und sein Ausweisdokument sowie das
Wechselregister aufzubewahren, macht Ihre Tätigkeit aber nicht von sich
aus konform; die Einhaltung der örtlichen Vorschriften bleibt in der
Verantwortung des Unternehmens.

Support
=======

* E-Mail: odoo@natimai.solutions
* Website: https://www.natimai.solutions

Lizenz
======

OPL-1 (Odoo Proprietary License), siehe die Datei ``LICENSE`` des Moduls.
