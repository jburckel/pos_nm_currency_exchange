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
* ein Kassenadministrator kann einen fehlerhaften Vorgang stornieren,
  solange die Sitzung geöffnet ist und die Schublade die erhaltenen Scheine
  noch enthält;
* die Vorgänge erscheinen in der Abschlusskontrolle, im Bericht
  *Währungsposition* und im Bericht *Verkaufsdetails*, in einer Liste mit
  einer Pivot-Ansicht der Provisionen und Kursmargen und in einem
  Wechselregister, das für einen Zeitraum exportiert oder gedruckt werden
  kann;
* die Kurstafel des Schalters kann an der Kasse angezeigt und gedruckt
  oder als PDF gedruckt werden;
* mehrere Schalter eines lizenzierten Geschäftssitzes können eine
  **Wechselstube** bilden: Sie teilen ihre Lizenz, ihre
  Identifikationsregeln und dieselben Kurse, und die Wechselstube zeigt
  die Schubladen jedes Schalters;
* über von Ihnen festgelegten Schwellen erklärt der Kunde die Herkunft der
  Mittel, und der Vorgang wird für den Compliance-Beauftragten als *Zu
  prüfen* markiert;
* jeder Vorgang wird in ein unveränderbares Register verkettet
  (Hash-Kette), das je Zeitraum geprüft und abgeschlossen werden kann;
* die Kurstafel kann im Vollbild auf einem den Kunden zugewandten
  Bildschirm oder auf dem Kundendisplay von Odoo angezeigt werden und lädt
  die Kurse von selbst neu;
* die erhaltenen und ausgezahlten fremden Münzen und Scheine können nach
  Stückelung gezählt werden, mit dem Bestand jeder Schublade, und Scheine
  können von einem Schalter einer Wechselstube an einen anderen gesendet
  werden.

All dies ist optional: Ein einzelner Schalter ohne Wechselstube arbeitet
wie bisher.

Voraussetzungen
===============

* Die Anwendung **Kassensystem** (``point_of_sale``), Odoo 20.
* **POS Multi-Currency Cash** (``pos_nm_multicurrencies``) **20.0.2.1.0
  oder neuer**, im auf dem Odoo Apps Store angezeigten Preis enthalten:
  insgesamt 178 EUR, 59 EUR für dieses Modul plus 119 EUR für POS
  Multi-Currency Cash (bereits gekauft? Kontaktieren Sie uns vor dem Kauf dieses Moduls unter
  odoo@natimai.solutions), mit
  mindestens einer Fremdwährung auf der Bargeld-Zahlungsmethode der Kasse
  (siehe dessen Anleitung: *Eine Währung in bar akzeptieren*). Eine
  ältere Version von POS Multi-Currency
  Cash funktioniert mit diesem Modul nicht: Aktualisieren Sie sie zuerst.
  Ab 20.0.2.1.1 wird der Anfangsbestand des Bargeld-Blocks der
  Hauptwährung im Abschlussfenster korrekt angezeigt, wenn die Sitzung
  Geldwechsel-Vorgänge hat (vorher war es nur ein Anzeigefehler: Die
  gezählten und gebuchten Beträge waren richtig).
* Ein **Ertragskonto für die Provisionen** (Typ *Einkommen* oder
  *Sonstige betriebliche Erträge*).
* Um Scheine zwischen den Schaltern einer Wechselstube zu übertragen: ein
  **Konto für Geld im Transit** (Typ *Umlaufvermögen*).

Konfiguration
=============

Den Wechselschalter aktivieren
------------------------------

Gehen Sie zu *Kassensystem → Konfiguration → Einstellungen*, wählen Sie
Ihre Kasse und suchen Sie den Abschnitt **Geldwechsel**:

* **Geldwechsel** (standardmäßig aktiviert): zeigt die Einträge des
  Schalters im Menü der Kasse.
* **Provisionskonto**: Ertragskonto, auf dem die Provisionen gebucht
  werden. Nur Ertragskonten können gewählt werden. Es ist erforderlich, um
  einen Vorgang zu erfassen.
* **Wechsellizenznummer**: Lizenz- oder Registrierungsnummer Ihrer
  Geldwechseltätigkeit, auf den Belegen und der Kurstafel gedruckt, wenn
  angegeben.
* **Wechselstube**: die Wechselstube dieses Schalters (siehe
  *Wechselstube und Schalter*). Mit einer Wechselstube sind die Lizenz und
  die folgenden Identifikationsschwellen ausgeblendet: Es gelten die der
  Wechselstube.
* **Kunde erforderlich ab**: Wert eines Vorgangs in der Währung der Kasse,
  ab dem der Kunde erfasst werden muss.
* **Kunde für jeden Vorgang erforderlich**: Jeder Vorgang nennt seinen
  Kunden.
* **Ausweisdokument erforderlich ab**: Wert, ab dem das Ausweisdokument
  des Kunden auf dem Vorgang erfasst wird.
* **Zeitraum der verbundenen Vorgänge (Tage)**: Wenn größer als 0, ist der
  mit den Schwellen verglichene Wert der Vorgang plus die Vorgänge
  desselben Kunden in so vielen Tagen (siehe *Kundenidentifikation*).
* **Herkunft der Mittel erforderlich ab**: Wert, ab dem der Kunde die
  Herkunft der Mittel erklärt (siehe *Compliance-Schwellen*).
* **Prüfung ab**: Wert, ab dem der Vorgang für den
  Compliance-Beauftragten als *Zu prüfen* markiert wird. Er wird nie
  abgelehnt.
* **Scheine nach Stückelung verfolgen**: Die erhaltenen und ausgezahlten
  fremden Scheine werden nach Münze und Schein gezählt (siehe *Scheine
  nach Stückelung*).
* **Kurstafel auf dem Kundendisplay**: Das Kundendisplay von Odoo zeigt
  die Kurstafel, solange kein Auftrag läuft.
* **Adresse der Kurstafel**: Adresse der Vollbild-Kurstafel dieses
  Schalters für einen den Kunden zugewandten Bildschirm (siehe *Kurstafel
  auf einem Bildschirm*).
* **Wechselkurse drucken**: druckt die Kurstafel der Kasse als PDF.

Schwellen auf 0 werden nie angewendet.

Provisionen und Verkaufsmarge je Währung
----------------------------------------

Gehen Sie zu *Kassensystem → Konfiguration → Bargeldwährungen* und
öffnen Sie die Zeile der Währung. Die Gruppe *Geldwechsel* enthält vier
Werte, wobei die Beträge in der Währung der Kasse sind:

* **Wechsel-Verkaufsmarge (%)**: Marge des Schalters auf die Scheine
  dieser Währung, die er auszahlt (siehe *Kurse* unten). Bei einem festen
  Kassenkurs ausgeblendet, da dort nicht verwendet. Eine neue Währung
  beginnt mit ihrer Kassenkurs-Marge (eine negative wird zur
  Verkaufsmarge, die denselben Verkaufskurs behält, wie beim Update);
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
Wechsel-Verkaufsmarge von 10 %: Der Schalter kauft Euro zu
2 × 1,10 = 2,20 EUR für 1 USD (100 erhaltene EUR sind 45,45 $ wert) und
verkauft sie zu 2 / 1,10 = 1,8182 EUR für 1 USD (100 ausgezahlte EUR sind
55,00 $ wert), vor der Provision.

Der Unterschied zu den Odoo-Kursen ist die **Kursmarge** des Vorgangs
(siehe *Buchhalterische Hinweise*). Bei einer Aktualisierung von 20.0.1.x
wird die Wechsel-Verkaufsmarge jeder Währung auf
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
die Ihre Tätigkeit dem Kunden zeigen muss. Werden die Scheine nach
Stückelung gezählt, listet der Beleg die Scheine unter den Beträgen auf.

Wechselstube und Schalter
-------------------------

Eine Wechselstube ist ein lizenzierter Geschäftssitz mit einem oder
mehreren Schaltern (Kassen). Sie ist optional: Ein Schalter außerhalb
jeder Wechselstube behält seine eigenen Einstellungen.

Gehen Sie zu *Kassensystem → Konfiguration → Wechselstuben* und drücken
Sie **Neu**. Geben Sie der Wechselstube einen Namen und füllen Sie dann
aus:

* Gruppe *Wechselstube*: die **Adresse** (auf dem Wechselregister und der
  Kurstafel gedruckt), die **Wechsellizenznummer**, den
  **Compliance-Beauftragten** (er erhält eine Aktivität für jeden als *Zu
  prüfen* markierten Vorgang) und das **Konto für Geld im Transit**
  (siehe *Konto für Geld im Transit*);
* Gruppe *Identifikation*: **Kunde für jeden Vorgang erforderlich**,
  **Kunde erforderlich ab**, **Ausweisdokument erforderlich ab**,
  **Herkunft der Mittel erforderlich ab**, **Prüfung ab** und **Zeitraum
  der verbundenen Vorgänge** (Tage). Sie wirken wie die gleichnamigen
  Einstellungen einer Kasse, in der Währung des Unternehmens.

Die Lizenz und die Regeln der Wechselstube ersetzen die ihrer Schalter.
Um einen Schalter hinzuzufügen, legen Sie seine **Wechselstube** im
Abschnitt *Geldwechsel* der Einstellungen der Kasse fest oder fügen Sie
ihn im Reiter **Schalter** der Wechselstube hinzu. Die Schalter einer
Wechselstube müssen die Währung ihres Unternehmens verwenden.

Die intelligenten Schaltflächen der Wechselstube öffnen ihre
**Schalter**, ihre **Vorgänge** und ihre Scheine-**Transfers**.

Dieselben Kurse an jedem Schalter
---------------------------------

Wählen Sie im Reiter **Schalter** der Wechselstube den
**Referenzschalter**: den Schalter, dessen Kurse die anderen übernehmen
und dessen Kurse die Kurstafel der Wechselstube zeigt. Dann, ab zwei
Schaltern:

* **Kurse auf die Schalter anwenden** kopiert für jede Währung des
  Referenzschalters den Kassenkurs (Kursmodus, Marge, feste Kurse), die
  Rundungen der Münzen und Scheine, die **Wechsel-Verkaufsmarge (%)** und
  die Provisionen auf die anderen Schalter. Die Änderungen der Kurse, der
  Margen und der Provisionen werden im Chatter der Währung protokolliert
  (nicht die der Rundungen). Ein Schalter, der die Währung nicht in bar
  annimmt, wird übersprungen und in einem Hinweis genannt;
* **Kursabweichungen** listet, was noch vom Referenzschalter abweicht.

Wenden Sie die Kurse nach jeder Änderung am Referenzschalter erneut an.

Compliance-Schwellen
--------------------

Zwei Schwellen helfen Ihnen, die Geldwäschevorschriften Ihres Landes zu
befolgen. Sie werden in der Wechselstube festgelegt oder, für eine Kasse
außerhalb jeder Wechselstube, in den Einstellungen der Kasse, in der
Währung der Kasse; auf 0 werden sie nie angewendet. Die verbundenen
Vorgänge des Kunden zählen wie bei den anderen Schwellen.

* **Herkunft der Mittel erforderlich ab**: Der Vorgang erfordert einen
  Kunden, und der Kunde erklärt die Herkunft der Mittel. *Andere*
  erfordert Einzelheiten.
* **Prüfung ab**: Der Vorgang wird als *Zu prüfen* markiert. Er wird am
  Schalter nie abgelehnt. Eine Aktivität geht an den
  **Compliance-Beauftragten** der Wechselstube.

Ein Vorgang, dessen Kunde erklärt, eine politisch exponierte Person zu
sein, wird ebenfalls als *Zu prüfen* markiert. Wählen Sie einen
Kassenadministrator als Compliance-Beauftragten: Nur
Kassenadministratoren können die Vorgänge prüfen.

Kurstafel auf einem Bildschirm
------------------------------

Jeder Schalter hat eine öffentliche Kurstafel-Seite für einen Fernseher,
ein Tablet oder einen beliebigen den Kunden zugewandten Bildschirm. Ihre
Adresse ist die **Adresse der Kurstafel** im Abschnitt *Geldwechsel* der
Einstellungen der Kasse. Sie enthält das Zugriffstoken der Kasse, das
ihres Kundendisplays: Teilen Sie sie nur mit den Bildschirmen des
Schalters.

Eine Wechselstube hat ihre eigene Seite, im Reiter **Kurstafel** der
Wechselstube (Kassenadministratoren): Die **Adresse der Kurstafel** zeigt
die Kurse des Referenzschalters unter dem Namen, der Adresse und der
Lizenz der Wechselstube. **Aktualisierung der Tafel (Sekunden)** legt
fest, wie oft die Seite die Kurse neu lädt (standardmäßig 60, mindestens
10), auch für die Seiten ihrer Schalter. **Neue Adresse** gibt der Seite
der Wechselstube eine neue Adresse: Die Bildschirme mit der alten Adresse
erhalten die Kurse nicht mehr (sie behalten die letzten Kurse mit
„Verbindung unterbrochen: letzte Kurse angezeigt“ und zeigen nach dem Neuladen der Seite
nichts mehr an).

Um die Tafel auf dem Kundendisplay von Odoo anzuzeigen, aktivieren Sie
**Kurstafel auf dem Kundendisplay** in den Einstellungen der Kasse.

Scheine nach Stückelung
-----------------------

POS Multi-Currency Cash zählt die Münzen und Scheine jeder Fremdwährung
bereits beim Öffnen und Schließen. Dieses Modul kann sie auch während der
Sitzung verfolgen:

1. Gehen Sie zu *Kassensystem → Konfiguration → Münzen/Scheine* und
   prüfen Sie, ob die Münzen und Scheine jeder Fremdwährung vorhanden
   sind, mit gesetzter **Währung** (siehe die Anleitung von POS
   Multi-Currency Cash).
2. Aktivieren Sie in den Einstellungen der Kasse **Scheine nach
   Stückelung verfolgen**.

Die Option gilt für die fremden Bargeldwährungen, die an dieser Kasse
Münzen und Scheine haben. Die Währung der Kasse wird nicht verfolgt: Sie
hat keine Zählung nach Stückelung. Zählen Sie den Anfangsbestand nach
Münzen und Scheinen, damit der Bestand der Schublade richtig beginnt.

Konto für Geld im Transit
-------------------------

Scheine, die von einem Schalter einer Wechselstube an einen anderen
gesendet werden, laufen über das **Konto für Geld im Transit** der
Wechselstube: ein Konto des Umlaufvermögens (Typ *Umlaufvermögen*).
Legen Sie bei Bedarf eines in Ihrem Kontenplan an, zum Beispiel „Geld im
Transit“, und setzen Sie es in der Wechselstube. Sein Saldo ist der Wert
der gesendeten und noch nicht empfangenen Scheine. Ohne dieses Konto
können keine Scheine übertragen werden.

Wer darf was
------------

* **Kassenbenutzer** (Kassierer) erfassen Vorgänge an der Kasse, drucken
  ihre Belege nach und zeigen die Kurstafel. Sie können die Vorgänge lesen,
  aber nicht ändern.
* **Kassenadministratoren** (Zugriff *Kassensystem*: *Administrator*)
  sehen zusätzlich die Menüs *Kassensystem → Aufträge → Geldwechsel* und
  *Kassensystem → Berichtswesen → Wechselregister* und die
  Ausweisdokumente der Kunden, können die Notiz eines Vorgangs bearbeiten
  und einen Vorgang stornieren.
* An einer Wechselstube mit einem weiteren aktivierten Schalter senden
  und empfangen Kassenbenutzer außerdem Scheine an der Kasse (*Scheine
  senden*, *Scheine empfangen*), und sie sehen den *Notenbestand* ihrer
  Schublade, wenn die Scheine verfolgt werden.
* Kassenadministratoren verwalten außerdem die Wechselstuben
  (*Kassensystem → Konfiguration → Wechselstuben*, mit den Reitern
  **Schubladen** und **Kurstafel**) und die Notentransfers (*Kassensystem
  → Aufträge → Notentransfers*) und sehen *Kassensystem → Berichtswesen →
  Notenbestand*, *Notenbewegungen* und *Abschlüsse des
  Wechselregisters*.
* Nur Kassenadministratoren sehen die Erklärungen des Kunden und prüfen
  die Vorgänge (**Compliance**, **Compliance-Notiz**), prüfen die
  Integrität des Registers und schließen es ab.
* Niemand kann einen Vorgang oder eine seiner Kontoauszugszeilen, eine
  Notenbewegung, einen Registerabschluss oder einen gesendeten
  Notentransfer löschen.
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
   erscheinen seine Felder: Art, Ausstellungsland und Ablaufdatum sind
   aus dem Kontakt vorausgefüllt, und das Feld der Nummer zeigt nur als
   Hinweis die letzten 4 Zeichen der gespeicherten Nummer. Art, Nummer
   und Ablaufdatum sind Pflichtfelder; bei einem Dokument ohne
   Ablaufdatum (ein älterer Personalausweis) wird stattdessen **Kein
   Ablaufdatum** angekreuzt. **Staatsangehörigkeit** und
   **Geburtsdatum** erscheinen leer: Leer gelassen, behalten sie die Werte
   des Kontakts. Beim selben Dokument (gleiche Art, Nummer leer gelassen)
   behalten auch die Nummer und die anderen leer gelassenen Felder die
   Werte des Kontakts; geben Sie für ein anderes Dokument seine Nummer
   ein;
5. fügen Sie bei Bedarf eine Notiz hinzu und tippen Sie auf
   **Bestätigen**. Die Kassenschublade öffnet sich, der Wechselbeleg wird
   gedruckt und eine Benachrichtigung fasst den Vorgang zusammen.

**Bestätigen** bleibt deaktiviert, solange eine Berechnung läuft und wenn
die Schublade der ausgezahlten Währung den Betrag nicht enthält (die Zeile
*In der Schublade* ist dann rot, mit der Ablehnung).

Bricht die Verbindung beim Bestätigen ab, meldet das Fenster, dass der
Vorgang möglicherweise erfasst wurde: Bestätigen Sie erneut, sobald die
Verbindung wiederhergestellt ist. Bis dahin können Beträge, Währungen,
Kunde, Dokument und Notiz nicht geändert werden. Ein bereits erfasster
Vorgang wird nicht doppelt erfasst, und sein Beleg wird gedruckt. Bricht
die Verbindung ab, während das Angebot berechnet wird, meldet das Fenster
dies und fordert das Angebot einige Sekunden später erneut an.

Wenn der Schalter an dieser Kasse nicht arbeiten kann, zeigt der Eintrag
**Geldwechsel** den Grund statt des Fensters: keine Fremdwährung auf der
Bargeld-Zahlungsmethode oder kein Provisionskonto.

Erklärungen des Kunden
----------------------

Über der Schwelle **Herkunft der Mittel erforderlich ab** oder **Prüfung
ab** zeigt das Fenster, sobald der Kunde gewählt ist, **Erklärungen des
Kunden**:

* **Herkunft der Mittel**: Gehalt oder Rente, Ersparnisse,
  Geschäftseinkünfte, Verkauf eines Vermögenswerts, Erbschaft oder
  Schenkung, Andere. Erforderlich über der Schwelle der Herkunft der
  Mittel; bei *Andere* geben Sie die **Einzelheiten zur Herkunft der
  Mittel** ein;
* **Zweck des Vorgangs**: Reise, Geschäftstätigkeit, Studium,
  Familienunterstützung, Andere;
* **Politisch exponierte Person (oder ein Familienmitglied oder eine ihr
  nahestehende Person)**: Kreuzen Sie es an, wenn der Kunde dies erklärt.
  Der Vorgang wird dann als *Zu prüfen* markiert.

Nur über der Prüfungsschwelle werden die Erklärungen abgefragt, sind aber
nicht erforderlich. Sie werden mit der Adresse des Kunden im Vorgang
festgeschrieben. Der Kassierer wird nie durch eine Prüfung blockiert: Der
Compliance-Beauftragte prüft den Vorgang später (siehe *Zu prüfen*).

Die Scheine zählen
------------------

Mit **Scheine nach Stückelung verfolgen** wird das Fenster breiter und
zeigt ein Raster für jede verfolgte Fremdwährung des Vorgangs:

* **Erhaltene Scheine**: Geben Sie die **Menge** jeder Münze und jedes
  Scheins ein, die der Kunde übergibt. Die **Summe** muss dem erhaltenen
  Betrag entsprechen;
* **Ausgezahlte Scheine**: Die Mengen werden aus dem Bestand der
  Schublade vorgeschlagen, die größten Scheine zuerst. **In der
  Schublade** gibt den Bestand jeder Münze und jedes Scheins an. Ändern
  Sie die Mengen, wenn Sie andere Scheine auszahlen: Die **Summe** muss
  dem ausgezahlten Betrag entsprechen.

Eine rote Meldung erscheint, wenn eine Summe nicht übereinstimmt, und
**Bestätigen** bleibt deaktiviert. Fehlen der Schublade einige Scheine,
nennt eine orangefarbene Meldung sie: „In der Schublade fehlen ...:
Prüfen Sie die Scheine, bevor Sie sie auszahlen.“ Es ist nur ein Hinweis,
da die Barverkäufe in einer Fremdwährung die Schublade ohne Stückelung
bewegen: Der Bestand kann hinter der tatsächlichen Schublade
zurückliegen. Kann der ausgezahlte Betrag nicht mit den Münzen und
Scheinen der Währung zusammengesetzt werden, zeigt das Fenster dies als
Fehler.

Notenbestand
------------

Der Eintrag **Notenbestand** im Menü der Kasse (angezeigt, wenn die
Scheine verfolgt werden) gibt für jede verfolgte Währung und jede Münze
und jeden Schein die Zählung bei **Eröffnung**, die durch die
**Wechselvorgänge** und die Transfers bewegten Scheine und den Bestand
**In der Schublade** an. Wurde die Eröffnung nicht nach Münzen und
Scheinen gezählt, meldet das Fenster dies: Der Bestand zählt dann nur
die Wechsel.

Beim Schließen zeigt das Zählfenster jeder verfolgten Währung neben der
Zählung die erwartete Menge jeder Münze und jedes Scheins (*erwartet*),
wenn die Eröffnung nach Münzen und Scheinen gezählt wurde (oder die
Schublade bei der Eröffnung leer war).

Scheine senden und empfangen
----------------------------

Ein Schalter einer Wechselstube mit einem weiteren aktivierten Schalter
hat zwei weitere Einträge im Menü der Kasse.

**Scheine senden**:

1. wählen Sie den Schalter in **Senden an**. Ist dort keine Kasse
   geöffnet, warnt das Fenster, dass die Scheine im Transit bleiben, bis
   sie empfangen werden;
2. wählen Sie die Währung und geben Sie den Betrag in **Gesendeter Betrag**
   ein. Bei
   verfolgten Scheinen schlägt das Raster **Gesendete Scheine** die
   Scheine aus dem Bestand der Schublade vor; ihre **Summe** muss dem
   Betrag entsprechen;
3. fügen Sie bei Bedarf eine Notiz hinzu und tippen Sie auf
   **Bestätigen**. Die Kassenschublade öffnet sich und ein Transferbeleg
   wird gedruckt: Legen Sie ihn zu den Scheinen.

Die Schublade muss den Betrag enthalten. Der Transfer erhält seine
Referenz (``TRF/JJJJ/NNNNN``), und die Scheine verlassen die Schublade:
eine Auszahlung in der Sitzung, auf dem Konto für Geld im Transit der
Wechselstube.

**Scheine empfangen** listet die Scheine im Transit zu diesem Schalter:
Referenz, Sendedatum, sendender Schalter, Betrag und Scheine. Zählen Sie
die Scheine und tippen Sie dann auf **Empfangen**: Die Scheine gehen in
die Schublade ein (eine Einzahlung desselben Werts), und ein Beleg wird
gedruckt. Hat der sendende Schalter die Scheine nicht nach Stückelung
gezählt und verfolgt dieser Schalter sie, öffnet **Empfangen** das Raster
**Erhaltene Scheine**, vorausgefüllt mit den größten Scheinen zuerst:
Korrigieren Sie es auf die tatsächlich erhaltenen Scheine und tippen Sie
dann auf **Empfang bestätigen**. **Aktualisieren** lädt die Liste neu.

Der empfangene Betrag ist der gesendete Betrag. Eine Differenz zeigt sich
in der Abschlusszählung der empfangenden Schublade.

Die Kurstafel auf einem Bildschirm
----------------------------------

Öffnen Sie die **Adresse der Kurstafel** des Schalters oder die
**Adresse der Kurstafel** der Wechselstube (Schaltfläche **Kurstafel
öffnen** in der Wechselstube) im Browser des Bildschirms und schalten Sie
auf Vollbild. Die Seite zeigt die Währungen mit **Wir kaufen**,
**Wir verkaufen**, **Sie erhalten für** und **Sie zahlen für** den
typischen Betrag, die Provision jeder Währung, die Lizenz, das Datum und
die Uhrzeit. Sie lädt die Kurse von selbst neu. Bricht die
Verbindung ab, behält sie die letzten Kurse auf dem Bildschirm mit der
Meldung „Verbindung unterbrochen: letzte Kurse angezeigt“.

Die Tafel erscheint in der Sprache des Unternehmens (der Sprache seines
Kontakts). Für eine andere in der Datenbank installierte Sprache ergänzen
Sie die Adresse: ``&lang=de_DE`` für Deutsch, ``&lang=en_US`` für
Englisch usw.

Mit **Kurstafel auf dem Kundendisplay** zeigt das Kundendisplay von Odoo
die Tafel des Schalters, solange kein Auftrag läuft.

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
* die Herkunft der Mittel erforderlich ist und nicht erklärt wurde;
* bei verfolgten Scheinen die erhaltenen oder ausgezahlten Scheine nicht
  die Beträge ergeben;
* sich das Angebot zwischen Fenster und Server geändert hat (Kurs, Marge
  oder Provision inzwischen geändert): Es wird nichts gebucht, das Fenster
  zeigt sofort das neue Angebot mit einem Hinweis; prüfen Sie es mit dem
  Kunden und bestätigen Sie dann erneut;
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
der Kasse am nächsten liegt (100 EUR, 10.000 XPF, 1.000.000 VND), gerundet
auf die Münzen, die der Schalter in dieser Währung annimmt und auszahlt
(Zahlungsrundung und Wechselgeldrundung: 99 CHF bei 3-CHF-Münzen). Die
Beträge werden mit dem Angebot des Schalters berechnet und stimmen daher
mit den Vorgängen überein. **Drucken** druckt die Tafel auf dem
Bondrucker.

Einen Vorgang stornieren
------------------------

Ein fehlerhafter Vorgang wird storniert, nicht durch einen anderen
Vorgang korrigiert: Ein Gegenvorgang würde die Provision erneut berechnen
und die Scheine erneut runden, und eine Bargeldbewegung würde die
Provision auf dem Provisionskonto lassen.

Ein Kassenadministrator öffnet den Vorgang (*Kassensystem → Aufträge →
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
nachgedruckter Beleg ist mit *STORNIERT* gekennzeichnet. Bei verfolgten
Scheinen wird der Bestand der Schublade wiederhergestellt: Die erhaltenen
Scheine verlassen ihn und die ausgezahlten Scheine kehren zurück
(Scheinbewegungen *Stornierung*).
Die Stornierung erhält ihren eigenen Hash im Register (**Hash der
Stornierung**), und ein Vorgang eines abgeschlossenen Registerzeitraums
kann nicht storniert werden.

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
  Kasse. Überschreitet diese Summe eine Schwelle, zeigt das Fenster „Mit
  den verbundenen Vorgängen des Kunden“ und die Summe; sonst werden die
  anderen Vorgänge des Kunden nicht gezeigt. Ohne Kunden zählt nur der Vorgang: Aktivieren Sie **Kunde
  für jeden Vorgang erforderlich**, damit die Regel immer gilt.
* Über **Kunde erforderlich ab** erfordert der Vorgang einen Kunden.
* Über **Ausweisdokument erforderlich ab** erfordert er einen Kunden und
  ein gültiges Ausweisdokument: Art (Reisepass, Personalausweis,
  Führerschein, Aufenthaltstitel, Andere), Nummer, Ausstellungsland,
  Ablaufdatum (oder **Kein Ablaufdatum** bei einem Dokument ohne
  Ablaufdatum), Staatsangehörigkeit und Geburtsdatum. Ein abgelaufenes
  Dokument wird abgelehnt.

Der Server prüft diese Regeln beim Erfassen erneut. Das an der Kasse
eingegebene Dokument wird, wenn es vom gespeicherten abweicht, im Kontakt
gespeichert (Reiter **Ausweisdokument** des Kontaktformulars), und eine Kopie wird mit dem
Namen des Kunden im Vorgang aufbewahrt: Spätere Änderungen oder
Umbenennungen des Kontakts ändern die erfassten Vorgänge nicht. Der Beleg
druckt den Namen des Kunden und die Dokumentart mit nur den letzten
4 Zeichen der Nummer (zum Beispiel „Reisepass \*\*\*\*4567“).

Die Ausweisdokumente sind nur für Kassenadministratoren sichtbar; der
Kassierer sieht im Fenster Art, Ausstellungsland, Ablaufdatum und die
letzten 4 Zeichen der Nummer des gewählten Kunden. Ein an der Kasse
geändertes Dokument wird im Kontakt protokolliert. Den Kontakt eines
internen Benutzers, auch eines archivierten, ändert nur ein
Kassenadministrator (das Dokument bleibt dann im Vorgang); ein Kunde mit
einem Portalkonto ist ein Kunde wie jeder andere.

Die Vorgänge prüfen
===================

Geldwechsel
-----------

*Kassensystem → Aufträge → Geldwechsel* (Kassenadministratoren) listet
die Vorgänge mit Referenz, Datum, Kasse, Kassierer, Kunde, den erhaltenen
und ausgezahlten Scheinen, der Provision, der Kursmarge und dem Status.
Die Liste öffnet sich mit dem Filter **Erledigt**; der Filter
**Storniert** zeigt die stornierten. Weitere Filter: *Heute*, *Mit Kunde*,
*Ankauf von Fremdwährung*, *Verkauf von Fremdwährung*, *Kreuzwechsel*;
Gruppierung nach Kasse, Sitzung, Kassierer, Vorgangsart, Status, Währung
oder Datum. Die Pivot-Ansicht liefert Provisionen, Kursmargen und
erhaltene Werte je Tag, Status und erhaltener Währung; gruppieren Sie sie
bei Bedarf nach Kasse, Sitzung oder Kassierer.

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

Nur die **Notiz**, **Compliance** und die **Compliance-Notiz** können
bearbeitet werden, von einem Kassenadministrator (siehe *Zu prüfen*); die
Änderungen der **Notiz** und von **Compliance** werden im Chatter
protokolliert.

Das Sitzungsformular hat eine Schaltfläche mit der Summe der Provisionen
und „Vorgänge: N“, der Anzahl der erledigten Vorgänge; sie öffnet diese.

An einer Wechselstube zeigt der Vorgang außerdem seine **Wechselstube**
und seine **Lizenz**, und die Liste kann nach **Wechselstube** gruppiert
werden. Bei verfolgten Scheinen öffnet die Schaltfläche
**Notenbewegungen** die Münzen und Scheine des Vorgangs.

Zu prüfen
---------

Der Filter **Zu prüfen** von *Geldwechsel* zeigt die für den
Compliance-Beauftragten markierten Vorgänge: über der Prüfungsschwelle
oder mit einer erklärten politisch exponierten Person. Der
Compliance-Beauftragte der Wechselstube erhält außerdem eine Aktivität
„Den Wechselvorgang ... prüfen“.

Die Gruppe **Erklärungen und Compliance** des Vorgangs
(Kassenadministratoren) zeigt die **Herkunft der Mittel**, die
**Einzelheiten zur Herkunft der Mittel**, den **Zweck**, **Politisch
exponierte Person**, den **Prüfungsgrund** und die zwei Felder der
Prüfung:

* **Compliance**: Keine, Zu prüfen, Geprüft oder Gemeldet. Setzen Sie
  *Geprüft*, sobald geprüft, oder *Gemeldet*, wenn Sie den Vorgang den
  Behörden gemeldet haben;
* **Compliance-Notiz**: was Sie geprüft oder entschieden haben.

Diese zwei Felder und die **Notiz** sind die einzigen, die ein
Kassenadministrator ändern kann; die Änderungen von **Compliance** und
der **Notiz** werden im Chatter protokolliert. Die Gruppe
**Ausweisdokument** zeigt nun auch die **Kundenadresse** des Vorgangs.

Verkaufsdetails
---------------

Der Bericht *Verkaufsdetails* endet mit einer Tabelle *Geldwechsel*:
jeder Vorgang mit seiner Sitzung, seinen Beträgen, seiner Provision und
seiner Kursmarge, dann die Summen, eine Zeile je Währung der Kassen, und
die Liste der stornierten Vorgänge, die nicht gezählt werden. Aus einer
Sitzung gedruckt, umfasst er die Vorgänge der Sitzung; über *Kassensystem
→ Berichtswesen → Verkaufsdetails* für einen Zeitraum erstellt, umfasst
er die Vorgänge dieses Zeitraums an den gewählten Kassen (allen, wenn
keine gewählt ist), geöffnete Sitzungen eingeschlossen. Der Bericht
*Währungsposition* von POS Multi-Currency Cash spiegelt die bewegten
Scheine wider.

Wechselregister
---------------

*Kassensystem → Berichtswesen → Wechselregister*
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

Die Liste zeigt außerdem die **Herkunft der Mittel** und die
**Compliance** jedes Vorgangs; die **Wechselstube**, die **Lizenz**, die
**Kundenadresse**, der **Zweck**, **Politisch exponierte Person** und der
**Register-Hash** können über die optionalen Spalten hinzugefügt werden.
Wählen Sie im Assistenten eine **Wechselstube**, um nur das Register
ihrer Schalter zu drucken. Das PDF zeigt dann die Wechselstube, ihre
Adresse und ihre Lizenz; außerdem gibt es für jeden Vorgang die Adresse,
die Staatsangehörigkeit und das Geburtsdatum des Kunden, die
Erklärungen, den Compliance-Status und den Hash an.

Integrität des Registers
------------------------

Jeder Vorgang wird beim Erfassen gehasht (SHA-256), mit dem Hash des
vorherigen Vorgangs des Unternehmens: Die Vorgänge bilden eine Kette.
Eine Stornierung erhält ihren eigenen Hash, verkettet mit dem Hash des
Vorgangs. Das Formular des Vorgangs zeigt sie in der Gruppe
**Register**: **Register-Hash**, **Vorheriger Hash** und **Hash der
Stornierung**. Odoo verweigert jede Änderung der gehashten Felder eines
Vorgangs (Beträge, Kurs, Kunde, Ausweisdokument, Herkunft der Mittel,
politisch exponierte Person), auch durch den Administrator; nur die
**Notiz**, **Compliance** und die **Compliance-Notiz** bleiben änderbar.

Um die Kette zu prüfen, drücken Sie **Register drucken** und dann
**Integrität prüfen**. Die Prüfung berechnet die Hashes aller Vorgänge
des Unternehmens der Reihe nach neu:

* „N Vorgänge geprüft: Das Register ist intakt (letzter: ...).“, wenn
  jeder Hash übereinstimmt. Vorgänge ohne Hash, die vor dem Beginn der
  Kette erfasst wurden, werden gesondert gezählt;
* sonst „Integritätsprüfung bei ... fehlgeschlagen“, mit dem ersten
  Vorgang, der nicht übereinstimmt, und dem Grund: Hash fehlt, Kette
  unterbrochen, der Vorgang wurde verändert oder die Stornierung wurde
  verändert.

Die Hash-Kette zeigt, dass ein Vorgang direkt in der Datenbank geändert
oder entfernt wurde. Sie verhindert eine solche Änderung nicht, und sie
kann nicht zeigen, dass die letzten Vorgänge entfernt wurden: Vergleichen
Sie mit dem **Hash des letzten Vorgangs** des letzten Registerabschlusses
oder mit einem gedruckten Register.

Registerabschlüsse
------------------

Schließen Sie das Register eines Zeitraums ab, sobald er vorbei ist, zum
Beispiel jeden Monat:

1. *Kassensystem → Berichtswesen → Wechselregister*, **Register
   drucken**;
2. legen Sie **Von** und **Bis** fest sowie die **Wechselstube**, um das
   Register einer Wechselstube abzuschließen (leer lassen, ohne Kasse,
   für das ganze Unternehmen);
3. drücken Sie **Zeitraum abschließen** und bestätigen Sie. Der Abschluss
   kann nicht rückgängig gemacht werden.

Das Register wird nur abgeschlossen, wenn der Zeitraum vorbei ist, die
Sitzungen seiner Vorgänge geschlossen sind, er sich nicht mit einem
anderen Abschluss derselben Wechselstube oder des ganzen Unternehmens
überschneidet (bei einem Abschluss des ganzen Unternehmens auch mit keinem
Abschluss einer seiner Wechselstuben) und die Integritätsprüfung bestanden ist. Der Abschluss
erhält eine lückenlose Referenz (``EXR/JJJJ/NNNN``) und schreibt die
Anzahl der **Vorgänge** und der stornierten (**Storniert**), die **Erste
Referenz** und die **Letzte Referenz**, die **Provisionen**, die
**Kursmargen**, das Ergebnis der Prüfung (**Integrität**) und den **Hash
des letzten Vorgangs** fest. Das PDF-Register des Zeitraums wird
angehängt: **Register herunterladen**.

Die Abschlüsse sind unter *Kassensystem → Berichtswesen → Abschlüsse des
Wechselregisters* aufgeführt. Sie können nicht geändert oder gelöscht
werden, und ein Vorgang eines abgeschlossenen Zeitraums kann nicht mehr
storniert werden.

Notenbestand und Notenbewegungen
--------------------------------

*Kassensystem → Berichtswesen → Notenbestand* (Kassenadministratoren)
gibt je Sitzung, Währung und **Stückelung** die Zählung bei
**Eröffnung**, die durch die Vorgänge und die Transfers eingelegten
(**Eingänge**) und entnommenen (**Ausgänge**) Münzen und Scheine, den
**Bestand**, die Zählung beim **Abschluss** und die **Differenz** an
(Abschluss abzüglich Bestand, wenn beide Zählungen nach Münzen und
Scheinen erfolgten). Eine negative Differenz ist rot, eine positive
orange. Der Filter **Differenzen** behält die Zeilen, die nicht
übereinstimmen; eine Pivot-Ansicht gibt den Bestand je Währung und
Stückelung an.

*Kassensystem → Berichtswesen → Notenbewegungen* listet jede bewegte
Münze und jeden bewegten Schein: durch einen Geldwechsel, eine
Stornierung oder einen Transfer, mit Sitzung, Vorgang oder Transfer,
**Stückelung** und **Menge**. Die Bewegungen werden nie bearbeitet oder
gelöscht.

Notentransfers
--------------

*Kassensystem → Aufträge → Notentransfers* (Kassenadministratoren)
listet die Transfers mit Referenz, Wechselstube, **Sendender Schalter**,
**Empfangender Schalter**, Betrag, Wert, Daten und Status: Entwurf, Im
Transit, Erhalten oder Transfer storniert. Der Filter **Im Transit**
zeigt die gesendeten und noch nicht empfangenen Scheine.

Ein Kassenadministrator kann einen Transfer auch im Backend anlegen:
**Neu**, Wechselstube, Schalter, Währung und Betrag wählen, dann
**Senden**. Der sendende Schalter benötigt eine geöffnete Sitzung.
Verfolgt er die Scheine, werden die aus seinem Bestand vorgeschlagenen
Scheine gesendet; kann sein Bestand den Betrag nicht genau ergeben, wird
das Senden verweigert („Geben Sie die gesendeten Scheine nach Stückelung
ein“): Senden Sie dann von der Kasse aus, um die Scheine zu wählen.
**Empfangen** legt die Scheine in die Schublade des empfangenden
Schalters, in seiner geöffneten Sitzung.

**Stornieren** Sie einen Transfer im Transit, solange die Sitzung, die
ihn gesendet hat, geöffnet ist: Die Scheine gehen in die sendende
Schublade zurück (eine Einzahlung in dieser Sitzung). Ein empfangener
Transfer kann nicht storniert werden: Übertragen Sie die Scheine zurück.
Nach dem Senden kann nur die **Notiz** eines Transfers geändert werden.
Die Schaltflächen **Bargeldbewegungen** und **Notenbewegungen** öffnen
seine Kontoauszugszeilen und seine Münzen und Scheine.

Die Schubladen einer Wechselstube
---------------------------------

Der Reiter **Schubladen** der Wechselstube (Kassenadministratoren) zeigt
für jeden Schalter mit geöffneter Sitzung in der Spalte **Erwartetes
Bargeld** den erwarteten Bestand jeder Währung (Anfangsbestand, Verkäufe, Bargeldbewegungen, Geldwechsel und
Transfers), die **Vorgänge heute** und die **Provisionen heute**, mit den
Summen. Darunter gibt **Geld im Transit** je Währung die gesendeten und
noch nicht empfangenen Transfers, ihren Betrag und Wert sowie die
**Summe im Transit** an.

Kurstafel als PDF
-----------------

Die oben beschriebene Kurstafel wird auch als PDF (*Wechselkurse*)
gedruckt, mit **Wechselkurse drucken** in den Einstellungen oder über das
Menü *Drucken* der Kassen (Listenansicht von *Kassensystem →
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
* Ein Notentransfer besteht ebenfalls aus zwei Kontoauszugszeilen: eine
  Auszahlung in der Sitzung des sendenden Schalters beim Senden der
  Scheine und eine Einzahlung desselben Werts in der Sitzung des
  empfangenden Schalters bei ihrem Empfang, beide mit dem **Konto für
  Geld im Transit** der Wechselstube als Gegenkonto. Der Wert ist der
  Betrag zum Odoo-Tageskurs, in der Währung des Unternehmens. Der Saldo
  des Kontos ist der Wert der Scheine im Transit; er ist wieder null,
  sobald jeder Transfer empfangen oder storniert ist.

Aktualisierung auf 20.0.4.0.0
=============================

* POS Multi-Currency Cash 20.0.2.1.0 oder neuer ist weiterhin
  erforderlich.
* Die Aktualisierung kopiert die Wechsellizenznummer jeder Kasse auf ihre
  bestehenden Vorgänge und verkettet dann die bestehenden Vorgänge im
  Register-Hash, in der Reihenfolge ihrer Erstellung, Unternehmen für
  Unternehmen. Führen Sie nach der Aktualisierung einmal **Integrität
  prüfen** aus.
* Für einen Schalter außerhalb jeder Wechselstube ändert sich nichts:
  Seine Einstellungen bleiben, wie sie sind. Die neuen Schwellen
  (**Herkunft der Mittel erforderlich ab**, **Prüfung ab**) beginnen bei
  0, nie angewendet, und **Scheine nach Stückelung verfolgen** ist nicht
  aktiviert.
* Um die Wechselstuben zu nutzen, legen Sie sie an, fügen Sie ihre
  Schalter hinzu und setzen Sie dann das **Konto für Geld im Transit**
  jeder Wechselstube, bevor Sie Scheine zwischen ihren Schaltern senden.
* Schließen Sie nach der Aktualisierung die Sitzungen oder laden Sie jede
  Kasse neu, damit die Kassen die neuen Menüeinträge laden.

Aktualisierung von 20.0.1.x
===========================

* Aktualisieren Sie zuerst POS Multi-Currency Cash auf 20.0.2.1.0 oder
  neuer: Sonst werden Installation und Aktualisierung verweigert.
* Die **Wechsel-Verkaufsmarge** jeder Währung wird auf ihre
  Kassenkurs-Marge gesetzt (eine negative Marge wird zur Verkaufsmarge,
  die denselben Verkaufskurs ergibt, 2,04 % für -2 %): Die ausgezahlten
  Scheine
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
* Schließen Sie nach der Aktualisierung die Sitzungen oder laden Sie jede
  Kasse neu: Eine Kasse mit der vorherigen Version kann keine Vorgänge
  erfassen.
* Ein Vorgang, dessen Kontoauszugszeile mit 20.0.1.x gelöscht wurde, wird
  im Serverprotokoll und durch eine Nachricht im Vorgang gemeldet:
  Korrigieren Sie die Kassenlade mit einer Bargeldbewegung.

Bekannte Einschränkungen
========================

* Der Schalter arbeitet online: Berechnung und Erfassung sind
  Serveraufrufe.
* Ein Vorgang betrifft zwei Währungen; ein Kunde, der mehrere Währungen
  auf einmal wechselt, ergibt mehrere Vorgänge.
* Ein Vorgang kann nur storniert werden, solange seine Sitzung geöffnet
  ist, und nicht in einem abgeschlossenen Registerzeitraum.
* Die Scheine werden nur für die Fremdwährungen nach Stückelung
  verfolgt: Die Währung der Kasse hat keine Zählung nach Münzen und
  Scheinen.
* Der Notenbestand folgt nur den Wechselvorgängen und den Transfers: Die
  Barverkäufe und Bargeldbewegungen in einer Fremdwährung ändern die
  Schublade ohne Stückelung. Die nächste Zählung korrigiert ihn.
* Ein empfangener Notentransfer kann nicht storniert werden: Übertragen
  Sie die Scheine zurück.
* Die Integritätsprüfung umfasst das Register des ganzen Unternehmens.

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
geändert: Es wurde nichts gebucht. Das Fenster fordert sofort das neue
Angebot an und zeigt es mit einem Hinweis; prüfen Sie den neuen Betrag mit
dem Kunden und drücken Sie dann erneut **Bestätigen**. Der Vorgang wird nie
von selbst bestätigt.

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

Art, Nummer und Ablaufdatum sind Pflichtfelder (oder **Kein Ablaufdatum**
angekreuzt bei einem Dokument ohne Ablaufdatum), und das Dokument darf
nicht abgelaufen sein. Die Schwelle kann mit den verbundenen Vorgängen des
Kunden erreicht sein: Das Fenster zeigt ihre Summe.

Löschen fehlt bei den Vorgängen
-------------------------------

Die Vorgänge können nicht gelöscht werden, damit das Register vollständig
bleibt: Stornieren Sie den Vorgang stattdessen.

Scheine senden und Scheine empfangen fehlen
-------------------------------------------

Der Schalter muss zu einer Wechselstube mit mindestens einem weiteren
Schalter gehören, an dem **Geldwechsel** aktiviert ist. Laden Sie dann
die Kasse neu.

„Legen Sie das Konto für Geld im Transit der Wechselstube ... fest“
-------------------------------------------------------------------

Legen Sie das **Konto für Geld im Transit** der Wechselstube (ein Konto
des Umlaufvermögens) fest, bevor Sie Scheine übertragen.

Die Scheine ergeben den Betrag nicht
------------------------------------

Bei verfolgten Scheinen muss die **Summe** jedes Rasters dem Betrag des
Vorgangs oder des Transfers entsprechen. Korrigieren Sie die Mengen.

„In der Schublade fehlen ...“
-----------------------------

Der Bestand der Schublade, wie bei der Eröffnung gezählt und durch die
Vorgänge bewegt, enthält weniger dieser Scheine. Prüfen Sie die
tatsächlich ausgezahlten oder gesendeten Scheine. Der Vorgang wird nicht
blockiert.

Das Register kann nicht abgeschlossen werden
--------------------------------------------

Der Zeitraum muss vorbei sein, die Sitzungen seiner Vorgänge geschlossen
und die Integritätsprüfung bestanden. Er darf sich nicht mit einem
Abschluss derselben Wechselstube oder des ganzen Unternehmens
überschneiden; ein Abschluss des ganzen Unternehmens darf sich mit keinem
Abschluss einer Wechselstube überschneiden. Um
das ganze Unternehmen abzuschließen, lassen Sie **Wechselstube** und
**Kassen** leer.

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
