![logo](/images/logo.svg#gh-light-mode-only)
![logo](/images/dark_logo.svg#gh-dark-mode-only)

# Shadow Control

**Eine Home Assistant Integration zur vollständig automatischen Steuerung von Raffstoren und Jalousien.**

![Version](https://img.shields.io/github/v/release/starwarsfan/shadow-control?style=for-the-badge)
[![Tests][tests-badge]][tests]
[![Coverage][coverage-badge]][coverage]
[![hacs_badge][hacsbadge]][hacs]
[![github][ghsbadge]][ghs]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]
[![PayPal][paypalbadge]][paypal]
[![hainstall][hainstallbadge]][hainstall]

Go to the [English version](/README.md) version of the documentation.

## Inhaltsverzeichnis

* [Einführung](#einführung)
  * [TL;DR – Kurzform](#tldr--kurzform)
  * [Beschreibung – Langform](#beschreibung--langform)
  * [Entitäten-Vorrang](#entitäten-vorrang)
* [Installation](#installation)
* [Konfiguration](#konfiguration)
  * [Initiale Instanzkonfiguration](#initiale-instanzkonfiguration)
    * [Instanzname](#instanzname)
    * [Behangtyp](#behangtyp)
    * [Behang-Entitäten](#behang-entitäten)
    * [Azimut der Fassade](#azimut-der-fassade)
    * [Helligkeit](#helligkeit)
    * [Höhe der Sonne](#höhe-der-sonne)
    * [Azimut der Sonne](#azimut-der-sonne)
  * [Optionale Konfiguration](#optionale-konfiguration)
    * [Fassadenkonfiguration - Teil 1](#fassadenkonfiguration---teil-1)
      * [Behang-Entitäten](#behang-entitäten-1)
      * [Azimut der Fassade](#facade-azimuth)
      * [Beschattungsbeginn](#beschattungsbeginn)
      * [Beschattungsende](#beschattungsende)
      * [Minimale Sonnenhöhe](#minimale-sonnenhöhe)
      * [Maximale Sonnenhöhe](#maximale-sonnenhöhe)
      * [Debugmodus](#debugmodus)
    * [Fassadenkonfiguration - Teil 2](#fassadenkonfiguration---teil-2)
      * [Neutralhöhe](#neutralhöhe)
      * [Neutralwinkel](#neutralwinkel)
      * [Lamellenbreite](#lamellenbreite)
      * [Lamellenabstand](#lamellenabstand)
      * [Lamellenwinkeloffset](#lamellenwinkeloffset)
      * [Minimaler Lamellenwinkel](#minimaler-lamellenwinkel)
      * [Höhenschrittweite](#höhenschrittweite)
      * [Winkelschrittweite](#winkelschrittweite)
      * [Lichtstreifenbreite](#lichtstreifenbreite)
      * [Gesamthöhe](#gesamthöhe)
      * [Maximale Verfahrdauer](#maximale-verfahrdauer)
      * [Toleranz Höhenänderung](#toleranz-höhenänderung)
      * [Toleranz Lamellenwinkeländerung](#toleranz-lamellenwinkeländerung)
    * [Dynamische Eingänge](#dynamische-eingänge)
      * [Helligkeit](#brightness)
      * [Helligkeit Dawn](#brightness-Dawn)
      * [Höhe der Sonne](#sun-elevation)
      * [Azimut der Sonne](#sun-azimuth)
      * [Integration sperren](#integration-sperren)
      * [Integration sperren mit Zwangsposition](#integration-sperren-mit-zwangsposition)
      * [Zwangsposition Höhe](#zwangsposition-höhe)
      * [Zwangsposition Lamellenwinkel](#zwangsposition-lamellenwinkel)
      * [Höhenveränderung einschränken](#höhenveränderung-einschränken)
      * [Winkelveränderung einschränken](#winkelveränderung-einschränken)
      * [Zwangspositionierung auslösen](#zwangspositionierung-auslösen)
    * [Beschattungseinstellungen](#beschattungseinstellungen)
      * [B01 Steuerung aktiv](#b01-steuerung-aktiv)
      * [B02 Winter Helligkeitsschwellwert](#b02-winter-helligkeitsschwellwert)
      * [B05 Schliessen nach x Sekunden](#b05-schliessen-nach-x-sekunden)
      * [B06 Maximale Behanghöhe](#b06-maximale-behanghöhe)
      * [B07 Maximaler Lamellenwinkel](#b07-maximaler-lamellenwinkel)
      * [B08 Durchsicht nach x Sekunden](#b08-durchsicht-nach-x-sekunden)
      * [B09 Öffnen nach x Sekunden](#b09-öffnen-nach-x-sekunden)
      * [B10 Durchsichtwinkel](#b10-durchsichtwinkel)
      * [B11 Höhe nach Beschattung](#b11-höhe-nach-beschattung)
      * [B12 Winkel nach Beschattung](#b12-winkel-nach-beschattung)
    * [Dämmerungseinstellungen](#dämmerungseinstellungen)
      * [D01 Steuerung aktiv](#d01-steuerung-aktiv)
      * [D02 Dämmerungsschwellwert](#d02-dämmerungsschwellwert)
      * [D03 Schliessen nach x Sekunden](#d03-schliessen-nach-x-sekunden)
      * [D04 Maximale Behanghöhe](#d04-maximale-behanghöhe)
      * [D05 Maximaler Lamellenwinkel](#d05-maximaler-lamellenwinkel)
      * [D06 Durchsicht nach x Sekunden](#d06-durchsicht-nach-x-sekunden)
      * [D07 Öffnen nach x Sekunden](#d07-öffnen-nach-x-sekunden)
      * [D08 Durchsichtwinkel](#d08-durchsichtwinkel)
      * [D09 Höhe nach Dämmerung](#d09-höhe-nach-dämmerung)
      * [D10 Winkel nach Dämmerung](#d10-winkel-nach-dämmerung)
  * [Konfiguration via yaml](#konfiguration-via-yaml)
    * [yaml Beispielkonfiguration](#yaml-beispielkonfiguration)
* [Status, Rückgabewerte und direkte Optionen](#status-rückgabewerte-und-direkte-optionen)
  * [Status-Werte](#status-werte)
    * [Zielhöhe](#zielhöhe)
    * [Zielwinkel](#zielwinkel)
    * [Zielwinkel in Grad](#zielwinkel-in-grad)
    * [Kalkulatorische Zielhöhe](#kalkulatorische-zielhöhe)
    * [Kalkulatorischer Zielwinkel](#kalkulatorischer-zielwinkel)
    * [Aktueller Status](#aktueller-status)
    * [Sperr-Status](#sperr-status)
    * [Nächste Behangmodifikation](#nächste-behangmodifikation)
    * [In der Sonne](#in-der-sonne)
  * [Direkte Optionen](#direkte-optionen)
* [Konfiguration-Export](#konfiguration-export)
  * [Vorarbeiten](#vorarbeiten)
  * [Anwendung des Service](#anwendung-des-service)
  * [UI-Modus](#ui-modus)
  * [YAML-Modus](#yaml-modus)

# Einführung

**Shadow Control** ist die Portierung des Edomi-LBS "Beschattungssteuerung-NG" für Home Assistant. Da Edomi [zum Tode verurteilt wurde](https://knx-user-forum.de/forum/projektforen/edomi/1956975-quo-vadis-edomi) und ich mit den bestehenden Beschattungslösungen nicht wirklich zufrieden war, habe ich mich dazu entschlossen, meinen LBS (Edomi-Bezeichnung für **L**ogic**B**au**S**tein) in eine Home Assistant Integration zu portieren. Das war ein sehr interessanter "Tauchgang" in die Hintergründe von Homa Assistant, der Idee dahinter und wie das Ganze im Detail funktioniert. Viel Spass mit der Integration.

In den folgenden Abschnitten gilt Folgendes:

* Das Wort "Fassade" ist gleichbedeutend mit "Fenster" oder "Tür", da es hier lediglich den Bezug zum Azimut eines Objektes in Blickrichtung von innen nach aussen darstellt.
* Das Wort "Behang" bezieht sich auf Raffstoren. In der Home Assistant Terminologie ist das ein "cover", was aus Sicht dieser Integration das Gleiche ist.
* Die gesamte interne Logik wurde ursprünglich für die Interaktion mit KNX-Systemen entwickelt. Der Hauptunterschied ist daher die Handhabung von Prozentwerten. **Shadow Control** wird mit Home Assistant korrekt interagieren aber die Konfiguration sowie die Logausgaben verwenden 0 % als geöffnet und 100 % als geschlossen.
* Viele Einstellungen sind jeweils in zwei Ausprägungen vorhanden. Einmal als statischer Wert und einmal als Entität. Wird ein Wert fix konfiguriert und soll sich zur Laufzeit nicht ändern, wird das über die statische Konfiguration gemacht. Soll der Wert aber dynamisch angepasst werden können, muss er mit einer entsprechenden Entität verknüpft werden.
* Viele Einstellungen können via verknüpfter Entität modifiziert werden, stellen aber parallel dazu Instanz-spezifische Entitäten automatisch bereit. Damit können diese Einstellungen auch in Automationen verwendet werden, ohne durch eine Änderung einen Reload der Integration auszulösen. Konkret sind das die folgenden Settings, welche eigene Entitäten bereitstellen:
  * [Integration sperren](#integration-sperren)
  * [Integration sperren mit Zwangsposition](#integration-sperren-mit-zwangsposition)
  * [Zwangsposition Höhe](#zwangsposition-höhe)
  * [Zwangsposition Lamellenwinkel](#zwangsposition-lamellenwinkel)
  * [Höhenveränderung einschränken](#höhenveränderung-einschränken)
  * [Winkelveränderung einschränken](#winkelveränderung-einschränken)
  * [Alle Beschattungseinstellungen](#beschattungseinstellungen)
  * [Alle Dämmerungseinstellungen](#dämmerungseinstellungen)

## TL;DR – Kurzform

* Raffstoren- und Jalousie-Steuerung basierend auf Helligkeitsschwellwerten und verschiedenen Timern
* Höhe und Lamellenwinkel für Beschattung und Dämmerung separat konfigurierbar
  * Beschattungs- resp. Dämmerungsposition nach Helligkeitsschwellwert und Zeit X
  * Durchsicht-Position nach Helligkeitsschwellwert und Zeit Y
  * Offen-Position nach Zeit Z
* Besonnungsbereich einschränkbar
* Positionierung sperrbar
* Bewegungsrichtung des Behangs einschränkbar
* Unbeschatteter Bereich konfigurierbar
* Schrittweite konfigurierbar
* Separater Helligkeitseingang für Dämmerungssteuerung möglich
* Konfiguration via ConfigFlow und YAML möglich

## Beschreibung – Langform

Basierend auf verschiedenen Eingangswerten wird die Integration die Positionierung des Behangs übernehmen. Damit das funktioniert, muss die jeweilige Instanz mit dem Azimut der Fassade, dem Sonnenstand sowie der dortigen Helligkeit konfiguriert werden. Zusätzlich sind viele weitere Details konfigurierbar, um den Beschattungsvorgang resp. den entsprechenden Bereich unter direkter Sonneneinstrahlung zu definieren und somit direktes Sonnenlicht im Raum zu verhindern oder einzuschränken.

Die berechnete Behanghöhe sowie der Lamellenwinkel hängen von der momentanen Helligkeit, den konfigurierten Schwellwerten, der Abmessung der Lamellen, Timern und weiteren Einstellungen ab. Die verschiedenen Timer werden je nach momentanem Zustand der Integration gestartet.

Grundsätzlich gibt es zwei Betriebsarten: _Beschattung_ und _Dämmerung_, welche unabhängig voneinander eingerichtet werden.

Die Berechnung der Position wird durch die Aktualisierung der folgenden Eingänge ausgelöst:

* [Helligkeit](#helligkeit)
* [Helligkeit (Dämmerung)](#helligkeit-dämmerung)
* [Höhe der Sonne](#höhe-der-sonne)
* [Azimut der Sonne](#azimut-der-sonne)
* [Integration sperren](#integration-sperren)
* [Integration sperren mit Zwangsposition](#integration-sperren-mit-zwangsposition)
* [Beschattungssteuerung ein/aus](#b01-steuerung-aktiv)
* [Dämmerungssteuerung ein/aus](#d01-steuerung-aktiv)

Der konfigurierte Behang wird nur dann neu positioniert, wenn sich die berechneten Werte seit dem letzten Lauf der Integration geändert haben. Damit wird die unnötige Neupositionierung der Raffstorenlamellen verhindert.

## Entitäten-Vorrang
Achtung: Bei allen Optionen hat die Entity-Verknüpfung Vorrang! Das bedeutet, dass sobald eine Entität konfiguriert wird, wird deren Wert verwendet. Ausserdem werden die internen Entitäten aus dem System entfernt. Um die internen Entitäten wiederzuverwenden, muss die Entity-Verknüpfung gelöscht werden.


# Installation

**Shadow Control** ist eine Default-Integration in HACS. Zur Installation genügt es also, in HACS danach zu suchen, die Integration hinzuzufügen und Home-Assistant neu zu starten. Im Anschluss kann die Integration unter _Einstellungen > Geräte und Dienste_ hinzugefügt werden.

# Konfiguration

Die Konfiguration ist unterteilt in die minimalistische Initialkonfiguration sowie in eine separate Detailkonfiguration. Die Initialkonfiguration führt bereits zu einer vollständig funktionierenden Behangautomatisierung, welche über die Detailkonfiguration bei Bedarf jederzeit angepasst werden kann.



## Initiale Instanzkonfiguration

Die initiale Instanzkonfiguration ist sehr minimalistisch und benötigt nur die folgenden Konfigurationswerte. Alle anderen Einstellungen werden mit Standardwerten vorbelegt, welche im Nachhinein an die persönlichen Wünsche angepasst werden können. Siehe dazu den Abschnitt [Optionale Konfiguration](#optionale-konfiguration).

### Instanzname
(yaml: `name`)

Ein beschreibender und eindeutiger Name für diese **Shadow Control** Instanz. Eine bereinigte Version dieses Namens wird zur Kennzeichnung der Log-Einträge in der Home Assistant Logdatei sowie als Präfix für die von der Integration erstellten Status- und Options-Entitäten verwendet.

Beispiel: 
1. Die Instanz wird "Essbereich Tür" genannt
2. Der bereinigte Name ist daraufhin "essbereich_tr"
3. Log-Einträge beginnen mit `[essbereich_tr]`
4. Status-Entitäten heissen bspw. `sensor.essbereich_tr_target_height`

#### Behangtyp
(yaml: `facade_shutter_type_static`)

Der verwendete Behangtyp. Standardeinstellung ist der 90°-Behangtyp (yaml: `mode1`). Bei diesem Typ sind die Lamellen bei 0% waagerecht, also offen und bei 100% (i.d.R. nach aussen) vollständig geschlossen.

Weitere unterstützte Typen:

* Der zweite mögliche Behangtyp hat einen Schwenkbereich von ca. 180° (yaml: `mode2`), also bei 0% (i.d.R. nach aussen) geschlossen, bei 50% waagerecht offen und bei 100% (i.d.R. nach innen) wiederum geschlossen.
* Der dritte Behangtyp sind Jalousien bzw. Rollos (yaml: `mode3`). Bei diesem Typ werden sämtliche Winkeleinstellungen ausgeblendet.

Der Behangtyp kann im Nachhinein nicht geändert werden. Um ihn zu ändern, muss die jeweilige **Shutter Control** Instanz gelöscht und neu angelegt werden.

### Behang-Entitäten
(yaml: `target_cover_entity`)

Hier werden die zu steuernden Behang-Entitäten verbunden. Es können beliebig viele davon gleichzeitig gesteuert werden. Allerdings empfiehlt es sich, nur die Storen zu steuern, welche sich auf der gleichen Fassade befinden, also das gleiche Azimut haben. Für die weiteren internen Berechnungen wird der erste konfigurierte Behang herangezogen. Alle anderen Storen werden identisch positioniert.

Im yaml ist die Listen-Syntax zu verwenden:
```yaml
    target_cover_entity:
      - cover.fenster_buro_1
      - cover.fenster_buro_2
```

### Azimut der Fassade
(yaml: `facade_azimuth_static`)

Azimut der Fassade in Grad, also die Blickrichtung von innen nach aussen. Eine perfekt nach Norden ausgerichtete Fassade hat ein Azimut von 0°, eine nach Süden ausgerichtete Fassade demzufolge 180°. Der Sonnenbereich dieser Fassade ist der Bereich, in dem die Beschattungssteuerung via **Shadow Control** erfolgen soll. Das ist maximal ein Bereich von 180°, also [Azimut der Fassade](#azimut-der-fassade) + [Beschattungsbeginn](#beschattungsbeginn) bis [Azimut der Fassade](#azimut-der-fassade) + [Beschattungsende](#beschattungsende).

rdeckard hat damals für den Edomi-Baustein eine Zeichnung beigesteuert, welche unverändert auch hier gültig ist:

![Erklärung zum Azimut](/images/azimut.png)

### Helligkeit
(yaml: `brightness_entity`)

Aktuelle Helligkeit auf der Fassade. Im Regelfall kommt dieser Wert von einer Wetterstation und sollte der tatsächlichen Helligkeit auf dieser Fassade möglichst nah kommen.

### Höhe der Sonne
(yaml: `sun_elevation_entity`)

Hier wird die aktuelle Höhe (Elevation) der Sonne konfiguriert. Dieser Wert kommt ebenfalls von einer Wetterstation oder direkt von der Home Assistant Sonne-Entität. Gültig ist dabei der Bereich von 0° (horizontal) bis 90° (vertikal).

### Azimut der Sonne
(yaml: `sun_azimuth_entity`)

Hier wird der aktuelle Winkel (Azimut) der Sonne konfiguriert. Dieser Wert kommt ebenfalls von einer Wetterstation oder direkt von der Home Assistant Sonne-Entität. Gültig ist dabei der Bereich von 0° bis 359°.

sunrise_entity
sunset_entity



## Optionale Konfiguration

Die folgenden Optionen sind über den separaten ConfigFlow verfügbar, welcher mit einem Klick auf das Zahnrad-Symbol der jeweiligen Instanz unter Einstellungen > Geräte und Dienste > **Shadow Control** geöffnet wird..

### Fassadenkonfiguration - Teil 1

#### Behang-Entitäten

Siehe Beschreibung unter [Behang-Entitäten](#behang-entitäten).

#### Azimut der Fassade

Siehe Beschreibung unter [Azimut der Fassade](#azimut-der-fassade).

#### Beschattungsbeginn
(yaml: `facade_offset_sun_in_static`)

Negativoffset zum [Azimut der Fassade](#azimut-der-fassade), ab welchem die Beschattung erfolgen soll. Wenn das Azimut der Sonne kleiner ist als [Azimut der Fassade](#azimut-der-fassade) + [Beschattungsbeginn](#beschattungsbeginn), wird keine Beschattungsberechnung ausgelöst. Gültiger Wertebereich: -90–0, Standardwert: -90

#### Beschattungsende
(yaml: `facade_offset_sun_out_static`)

Positivoffset zum [Azimut der Fassade](#azimut-der-fassade), bis zu welchem die Beschattung erfolgen soll. Wenn das Azimut der Sonne grösser ist als [Azimut der Fassade](#azimut-der-fassade) + [Beschattungsende](#beschattungsende), wird keine Beschattungsberechnung ausgelöst. Gültiger Wertebereich: 0-90, Standardwert: 90

#### Minimale Sonnenhöhe
(yaml: `facade_elevation_sun_min_static`)

Minimale Höhe der Sonne in Grad. Ist die effektive Höhe kleiner als dieser Wert, wird keine Beschattungsberechnung ausgelöst. Ein Anwendungsfall dafür ist bspw. wenn sich vor der Fassade ein anderes Gebäude befindet, welches Schatten auf die Fassade wirft, während die Wetterstation auf dem Dach noch voll in der Sonne ist. Wertebereich: 0-90, Standardwert: 0

Hinweis bzgl. "effektiver Höhe": Um den korrekten Lamellenwinkel zu berechnen, muss die Höhe der Sonne im rechten Winkel zur Fassade errechnet werden. Das ist die sog. "effektive Höhe", welche so auch im Log zu finden ist. Wenn die Beschattungssteuerung insbesondere im Grenzbereich der beiden Beginn- und Ende-Offsets nicht wie erwartet arbeitet, muss dieser Wert genauer betrachtet werden.

#### Maximale Sonnenhöhe
(yaml: `facade_elevation_sun_max_static`)

Maximale Höhe der Sonne in Grad. Ist die effektive Höhe grösser als dieser Wert, wird keine Beschattungsberechnung ausgelöst. Ein Anwendungsfall dafür ist bspw. wenn sich über der Fassade resp. dem Fenster ein Balkon befindet, welcher Schatten auf die Fassade wirft, während die Wetterstation auf dem Dach noch voll in der Sonne ist. Wertebereich: 0-90, Standardwert: 90

#### Debugmodus
(yaml: `debug_enabled`)

Mit diesem Schalter kann der Debugmodus aktiviert werden. Damit werden erheblich mehr Informationen zum Verhalten und der Berechnung für diese Fassade ins Log geschrieben.



### Fassadenkonfiguration - Teil 2

#### Neutralhöhe
(yaml: `facade_neutral_pos_height_manual`)

Behanghöhe in % in Neutralposition. Die Integration wird in die Neutralposition fahren, wenn mindestens eine der folgenden Bedingungen erfüllt ist: 

* Die Sonne befindet sich im Beschattungsbereich und die Beschattungsregelung wird deaktiviert
* Die Dämmerungsregelung wird deaktiviert
* Die Sonne verlässt den Beschattungsbereich

Standardwert: 0

#### Neutralwinkel
(yaml: `facade_neutral_pos_angle_manual`)

Lamellenwinkel in % in Neutralposition. Alles andere identisch zu [Neutralhöhe](#neutralhöhe). Standardwert: 0

#### Lamellenbreite
(yaml: `facade_slat_width_static`)

Die Breite der Lamellen in mm. Breite und Abstand werden benötigt, um den Lamellenwinkel zu berechnen, der benötigt wird, die Lamellen gerade so schräg zu stellen, dass kein direktes Sonnenlicht in den Raum fällt. Die Lamellenbreite muss zwingend grösser als der Lamellenabstand sein, anderenfalls ist es nicht möglich, eine korrekte Beschattungsposition anzufahren. Standardwert: 95

#### Lamellenabstand
(yaml: `facade_slat_distance_static`)

Der Abstand der Lamellen in mm. Alles andere siehe [Lamellenbreite](#lamellenbreite). Standardwert: 67

#### Lamellenwinkeloffset
(yaml: `facade_slat_angle_offset_static`)

Lamellenwinkeloffset in %. Dieser Wert wird zum berechneten Lamellenwinkel addiert. Er kann somit verwendet werden, um allfällige Ungenauigkeiten im Grenzbereich der Beschattung zu korrigieren. Das ist bspw. der Fall, wenn der Behang in Beschattungsposition ist aber dennoch ein schmaler Lichtstrahl hindurchfällt. Standardwert: 0

#### Minimaler Lamellenwinkel
(yaml: `facade_slat_min_angle_static`)

Minimaler Lamellenwinkel in %. Die Lamellen werden im Bereich von diesem Wert bis 100% positioniert. Damit kann diese Option dazu verwendet werden, den Öffnungsbereich zu begrenzen. Standardwert: 0

#### Höhenschrittweite
(yaml: `facade_shutter_stepping_height_static`)

Schrittweite der Höhenpositionierung. Die meissten Rollläden sind nicht in der Lage, sehr kleine Positionierungsschritte anzufahren. Um dem zu begegnen, kann hier die Schrittweite eingestellt werden, in welcher der Behang positioniert werden soll. Dabei wird berücksichtigt, ob die Sonne steigt oder fällt. Standardwert: 5

#### Winkelschrittweite
(yaml: `facade_shutter_stepping_angle_static`)

Schrittweite der Lamellenwinkelpositionierung. Details siehe [Höhenschrittweite](#höhenschrittweite). Standardwert: 5

#### Lichtstreifenbreite
(yaml: `facade_light_strip_width_static`)

Breite eines nicht zu beschattenden Lichtstreifens am Boden. Mit dieser Einstellung wird festgelegt, wie tief oder weit die Sonne in den Raum hinein scheinen soll. Dementsprechend wird der Behang in der Höhe nicht 100% geschlossen, sondern auf die Höhe gefahren, welche in den hier definierten Lichtstreifen resultiert. Standardwert: 0

#### Gesamthöhe
(yaml: `facade_shutter_height_static`)

Um den Lichtstreifen aus [Lichtstreifenbreite](#lichtstreifenbreite) zu berechnen, wird die Gesamthöhe des Behangs resp. des Fensters benötigt. Damit muss die gleiche Einheit verwendet werden, also bspw. beide Werte in mm. Standardwert: 1000

#### Maximale Verfahrdauer
(yaml: `facade_max_movement_duration_static`)

Gibt die Dauer der Bewegung von vollständig geschlossen (unten) bis vollständig offen (oben) in Sekunden an. Dieser Wert wird benötigt, um die automatische Instanzsperre korrekt durchzuführen, wenn der Behang manuell bewegt wird.

#### Toleranz Höhenänderung
(yaml: `facade_modification_tolerance_height_static`)

Toleranzbereich für externe Höhenmodifikation. Weicht die kalkulierte Höhe von der tatsächlichen Höhe +/- der hier angegebenem Toleranz ab, sperrt sich die Integration nicht selbst. Standardwert: 8

#### Toleranz Lamellenwinkeländerung
(yaml: `facade_modification_tolerance_angle_static`)

Toleranzbereich für externe Lamellenwinkelmodifikation, alles Weitere siehe [Toleranz Höhenänderung](#toleranz-höhenänderung). Standardwert: 5





### Dynamische Eingänge

Dieser Abschnitt konfiguriert die dynamischen Eingänge. Damit werden die Werte eingerichtet, welche sich im täglichen Betrieb ändern können wie bspw. der Sonnenstand oder andere Verhaltenseinstellungen der Integration.

#### Helligkeit

Siehe Beschreibung unter [Helligkeit](#brightness).

#### Helligkeit (Dämmerung)
(yaml: `brightness_dawn_entity`)

Hier kann eine separate Helligkeit für die Dämmerungssteuerung eingestellt werden. Das ist insbesondere dann sinnvoll, wenn für die einzelnen **Shadow Control** Instanzen resp. Fassaden unterschiedliche Helligkeitssensoren verwendet werden, der Behang aber im gesamten Gebäude zur Dämmerung gleichzeitig geschlossen werden soll. 

In diesem Fall sollte über eine separate Automation bspw. der Mittelwert aus allen Helligkeiten berechnet und hier verknüpft werden. Damit werden alle Raffstoren gleichzeitig in die Dämmerungsposition gefahren.

Wenn nur eine Helligkeit für das gesamte Gebäude vorhanden ist, kann dieser Eingang leer bleiben.

#### Höhe der Sonne

Siehe Beschreibung unter [Höhe der Sonne](#sun-elevation).

#### Azimut der Sonne

Siehe Beschreibung unter [Azimut der Sonne](#sun-azimuth).

#### Aktuelle Behanghöhe

#### Aktueller Behangwinkel

#### Integration sperren
(yaml: `lock_integration_manual: true|false` u/o `lock_integration_entity: <entity>`)

Mit diesem Eingang kann die gesamte Integration gesperrt werden. Wird der Eingang aktiviert, also auf 'on' gesetzt, arbeitet die Integration intern normal weiter, aktualisiert aber den verbundenen Behang nicht. Damit wird erreicht, dass beim Entsperren direkt die nun gültige Position angefahren werden kann.

Wird der Eingang auf 'off' gesetzt, arbeitet die Integration normal weiter, solange nicht [Integration sperren mit Zwangsposition](#integration-sperren-mit-zwangsposition) aktiv ist.

Achtung, siehe Hinweis unter [Entitäten-Vorrang](#entitäten-vorrang).

#### Integration sperren mit Zwangsposition
(yaml: `lock_integration_with_position_manual: true|false` u/o `lock_integration_with_position_entity: <entity>`)

Mit diesem Eingang kann die gesamte Integration gesperrt und eine Zwangsposition angefahren werden. Wird der Eingang aktiviert, also auf 'on' gesetzt, arbeitet die Integration intern normal weiter, fährt aber den Behang auf die via [Zwangsposition Höhe](#zwangsposition-höhe)/[Zwangsposition Lamellenwinkel](#zwangsposition-lamellenwinkel) konfigurierte Position. Damit wird erreicht, dass beim Entsperren direkt die nun gültige Position angefahren werden kann.

Wird der Eingang auf 'off' gesetzt, arbeitet die Integration normal weiter, solange nicht [Integration sperren](#integration-sperren) aktiv ist.

Dieser Eingang hat Vorrang vor [Integration sperren](#integration-sperren). Werden beide Sperren auf 'on' gesetzt, wird die Zwangsposition angefahren.

Achtung, siehe Hinweis unter [Entitäten-Vorrang](#entitäten-vorrang).

#### Zwangsposition Höhe
(yaml: `lock_height_manual: true|false` u/o `lock_height_entity: <entity>`)

Anzufahrende Höhe in %, wenn die Integration via [Integration sperren mit Zwangsposition](#integration-sperren-mit-zwangsposition) gesperrt wird.

Achtung, siehe Hinweis unter [Entitäten-Vorrang](#entitäten-vorrang).

#### Zwangsposition Lamellenwinkel
(yaml: `lock_angle_manual: true|false` u/o `lock_angle_entity: <entity>`)

Anzufahrender Lamellenwinkel in %, wenn die Integration via [Integration sperren mit Zwangsposition](#integration-sperren-mit-zwangsposition) gesperrt wird.

Achtung, siehe Hinweis unter [Entitäten-Vorrang](#entitäten-vorrang).

#### Höhenveränderung einschränken
(yaml: `movement_restriction_height_manual: true|false` u/o `movement_restriction_height_entity: <entity>`)

Mit diesem Setting kann die Bewegungsrichtung der Höhenpositionierung wie folgt eingeschränkt werden

* "Keine Einschränkung" (Standardwert):
  Keine Einschränkung der Höhenpositionierung. Die Integration wird den Behang öffnen oder schliessen.
* "Nur schließen":
  Im Vergleich zur letzten (vorherigen) Positionierung werden nur weiter schließende Positionen angefahren.
* "Nur öffnen":
  Im Vergleich zur letzten (vorherigen) Positionierung werden nur weiter öffnende Positionen angefahren.

Das kann dafür verwendet werden, dass der Behang nach der Beschattung nicht zunächst geöffnet und kurze Zeit später durch schnell einsetzende Dämmerung wieder geschlossen wird. Durch eine separate, bspw. tageszeitabhängige Automation, kann dieser Eingang entsprechend modifiziert werden.

Achtung, siehe Hinweis unter [Entitäten-Vorrang](#entitäten-vorrang).

#### Winkelveränderung einschränken
(yaml: `movement_restriction_angle_manual: true|false` u/o `movement_restriction_angle_entity: <entity>`)

Siehe [Höhenveränderung einschränken](#höhenveränderung-einschränken), hier nur für den Lamellenwinkel.

Achtung, siehe Hinweis unter [Entitäten-Vorrang](#entitäten-vorrang).

#### Zwangspositionierung auslösen
(yaml: `enforce_positioning_entity: <entity>`)

Dieser Eingang kann mit einer Boolean-Entität verknüpft werden. Wird diese Entität auf 'on' gestellt, wird die unmittelbare positionierung erzwungen. Das ist hilfreich, wenn die tatsächliche Behangposition nicht mehr mit der von der Integration angenommenen Position übereinstimmt, sollte aber im Normalfall deaktiviert bleiben. Anderenfalls werden die Lamellen mglw. ständig nur geschlossen und wieder geöffnet, weil Raffstoren technisch immer erst die Höhe und danach den Lamellenwinkel anfahren.

Zusätzlich zur vorherigen Entitätskonfiguration kann diese Push-Button-Entität auf Detailseite der Instanz verwendet werden, um die Behangpositionierung einmalig zu erzwingen. Wenn dieser Knopf gedrückt wird, wird der Behang entsprechend der berechneten Werte positioniert.





### Beschattungseinstellungen

#### B01 Steuerung aktiv
(yaml: `shadow_control_enabled_manual: true|false` u/o `shadow_control_enabled_entity: <entity>`)

Mit dieser Option wird die Beschattungssteuerung ein- oder ausgeschaltet. Standardwert: ein

#### B02 Winter Helligkeitsschwellwert
(yaml: `shadow_brightness_threshold_winter_manual: <Wert>` u/o `shadow_brightness_threshold_entity: <entity>`)

Hier wird der Helligkeitsschwellwert in Lux konfiguriert. Wird dieser Wert überschritten, startet der Timer [B05 Schliessen nach x Sekunden](#b05-schliessen-nach-x-sekunden). Standardwert: 50000 

#### B03 Sommer Helligkeitsschwellwert
#### B04 Schwellwertpuffer Sommer/Winter


#### B05 Schliessen nach x Sekunden
(yaml: `shadow_after_seconds_manual: <Wert>` u/o `shadow_after_seconds_entity: <entity>`)

Hier wird der Zeitraum in Sekunden konfiguriert, nachdem der Behang nach Überschreiten des [Helligkeitsschwellwertes](#b02-winter-helligkeitsschwellwert) geschlossen werden soll. Standardwert: 120

#### B06 Maximale Behanghöhe
(yaml: `shadow_shutter_max_height_manual: <Wert>` u/o `shadow_shutter_max_height_entity: <entity>`)

Hier kann die maximale Behanghöhe angegeben werden. Das wird bspw. verwendet, um den Behang nicht bis ganz auf den Boden zu fahren, damit ein festfrieren im Winter vermieden wird. Standardwert: 100 

#### B07 Maximaler Lamellenwinkel
(yaml: `shadow_shutter_max_angle_manual: <Wert>` u/o `shadow_shutter_max_angle_entity: <entity>`)

Hier kann der maximale Lamellenwinkel angegeben werden. Das wird bspw. verwendet, um den Behang nicht ganz zu schliessen, damit ein zusammenfrieren der Lamellen im Winter vermieden wird. Standardwert: 100

#### B08 Durchsicht nach x Sekunden
(yaml: `shadow_shutter_look_through_seconds_manual: <Wert>` u/o `shadow_shutter_look_through_seconds_entity: <entity>`)

Fällt die Helligkeit unter den Schwellwert von [B02 Winter Helligkeitsschwellwert](#b02-winter-helligkeitsschwellwert), wird der Behang nach der hier angegeben Zeit auf Durchsichtsposition gefahren. Standardwert: 900

#### B09 Öffnen nach x Sekunden
(yaml: `shadow_shutter_open_seconds_manual: <Wert>` u/o `shadow_shutter_open_seconds_entity: <entity>`)

Nachdem der Behang auf Durchsichtsposition gefahren wurde, wird er nach der hier konfigurierten Zeit ganz geöffnet. Standardwert: 3600

#### B10 Durchsichtwinkel
(yaml: `shadow_shutter_look_through_angle_manual: <Wert>` u/o `shadow_shutter_look_through_angle_entity: <entity>`)

Hier wird der Lamellenwinkel der Durchsichtsposition in % konfiguriert. Standardwert: 0

#### B11 Höhe nach Beschattung
(yaml: `shadow_height_after_sun_manual: <Wert>` u/o `shadow_height_after_sun_entity: <entity>`)

Wenn keine Beschattungssituation mehr vorliegt, wird der Behang auf die hier in % konfigurierte Höhe gefahren. Standardwert: 0

#### B12 Winkel nach Beschattung
(yaml: `shadow_angle_after_sun_manual: <Wert>` u/o `shadow_angle_after_sun_entity: <entity>`)

Wenn keine Beschattungssituation mehr vorliegt, wird der Behang auf den hier in % konfigurierten Lamellenwinkel gefahren. Standardwert: 0





### Dämmerungseinstellungen

#### D01 Steuerung aktiv
(yaml: `dawn_control_enabled_manual: true|false` u/o `dawn_control_enabled_entity: <entity>`)

Mit dieser Option wird die Dämmerungssteuerung ein- oder ausgeschaltet. Standardwert: ein

#### D02 Dämmerungsschwellwert
(yaml: `dawn_brightness_threshold_manual: <Wert>` u/o `dawn_brightness_threshold_entity: <entity>`)

Hier wird der Helligkeitsschwellwert in Lux konfiguriert. Wird dieser Wert unterschritten, startet der Timer [D03 Schliessen nach x Sekunden](#d03-schliessen-nach-x-sekunden). Standardwert: 500

#### D03 Schliessen nach x Sekunden
(yaml: `dawn_after_seconds_manual: <Wert>` u/o `dawn_after_seconds_entity: <entity>`)

Hier wird der Zeitraum in Sekunden konfiguriert, nachdem der Behang nach Unterschreiten des [Helligkeitsschwellwertes](#d02-dämmerungsschwellwert) geschlossen werden soll. Standardwert: 120

#### D04 Maximale Behanghöhe
(yaml: `dawn_shutter_max_height_manual: <Wert>` u/o `dawn_shutter_max_height_entity: <entity>`)

Hier kann die maximale Behanghöhe angegeben werden. Das wird bspw. verwendet, um den Behang nicht bis ganz auf den Boden zu fahren, damit ein festfrieren im Winter vermieden wird. Standardwert: 100

#### D05 Maximaler Lamellenwinkel
(yaml: `dawn_shutter_max_angle_manual: <Wert>` u/o `dawn_shutter_max_angle_entity: <entity>`)

Hier kann der maximale Lamellenwinkel angegeben werden. Das wird bspw. verwendet, um den Behang nicht ganz zu schliessen, damit ein zusammenfrieren der Lamellen im Winter vermieden wird. Standardwert: 100

#### D06 Durchsicht nach x Sekunden
(yaml: `dawn_shutter_look_through_seconds_manual: <Wert>` u/o `dawn_shutter_look_through_seconds_entity: <entity>`)

Steigt die Helligkeit über den Schwellwert von [D02 Dämmerungsschwellwert](#d02-dämmerungsschwellwert), wird der Behang nach der hier angegeben Zeit auf Durchsichtposition gefahren. Standardwert: 120

#### D07 Öffnen nach x Sekunden
(yaml: `dawn_shutter_open_seconds_manual: <Wert>` u/o `dawn_shutter_open_seconds_entity: <entity>`)

Nachdem der Behang auf Durchsichtsposition gefahren wurde, wird er nach der hier konfigurierten Zeit ganz geöffnet. Standardwert: 3600

#### D08 Durchsichtwinkel
(yaml: `dawn_shutter_look_through_angle_manual: <Wert>` u/o `dawn_shutter_look_through_angle_entity: <entity>`)

Hier wird der Lamellenwinkel der Durchsichtsposition in % konfiguriert. Standardwert: 0

#### D09 Höhe nach Dämmerung
(yaml: `dawn_height_after_dawn_manual: <Wert>` u/o `dawn_height_after_dawn_entity: <entity>`)

Wenn keine Dämmerungssituation mehr vorliegt, wird der Behang auf die hier in % konfigurierte Höhe gefahren. Standardwert: 0

#### D10 Winkel nach Dämmerung
(yaml: `dawn_angle_after_dawn_manual: <Wert>` u/o `dawn_angle_after_dawn_entity: <entity>`)

Wenn keine Dämmerungssituation mehr vorliegt, wird der Behang auf den hier in % konfigurierten Lamellenwinkel gefahren. Standardwert: 0





## Konfiguration via yaml

Es ist möglich, die **Shadow Control** Instanzen via yaml zu konfigurieren. Dazu müssen die entsprechenden Konfigurationen im `configuration.yaml` einmalig eingetragen und Home Assistant neu gestartet werden. **Shadow Control** wird die yaml-Konfiguration einlesen und entsprechende Instanzen anlegen. Diese Instanzen können im Anschluss via ConfigFlow bearbeitet werden. Änderungen an der yaml-Konfiguration werden nicht übernommen, da die gesamte Konfiguration via Home Assistant ConfigFlow abgebildet wird. Sollen die yaml-Konfigurationen dennoch neu eingelesen werden, müssen die entsprechenden **Shadow Control** Instanzen zunächst gelöscht und dann Home Assistant neu gestartet werden.

### yaml Beispielkonfiguration

Die Einträge der Konfiguration folgen den oben in der Dokumentation jeweils genannten Schlüsselwörtern. Nicht verwendete Schlüsselwörter müssen auskommentiert oder entfernt werden.

```yaml
shadow_control:
  - name: "Büro West"
    # Either 'mode1', 'mode2' or 'mode3'
    # All *_angle_* settings will be ignored on mode3
    facade_shutter_type_static: mode1
    target_cover_entity:
      - cover.fenster_buro_west
    debug_enabled: false
    #
    # =======================================================================
    # Dynamic configuration inputs
    #
    # Entity which holds the current brightness
    brightness_entity: input_number.d01_brightness
    # Entity which holds the current dawn brightness. See the description above.
    #brightness_dawn_entity: input_number.d02_brightness_dawn
    #
    # Entities holding the current sun position
    sun_elevation_entity: input_number.d03_sun_elevation
    sun_azimuth_entity: input_number.d04_sun_azimuth
    #sunrise_entity:
    #sunset_entity:
    #
    # Entities to lock the integration
    lock_integration_manual: false
    lock_integration_with_position_manual: false
    #lock_integration_entity: input_boolean.d07_lock_integration
    #lock_integration_with_position_entity: input_boolean.d08_lock_integration_with_position
    #
    # Lock with position height and angle values if lock_integration_with_position is used
    # Range from 0-100 as percent values
    lock_height_manual: 0
    lock_angle_manual: 0
    #
    # Lock with position height and angle entities if lock_integration_with_position is used
    #lock_height_entity: input_number.lock_height_entity
    #lock_angle_entity: input_number.lock_angle_entity
    #
    # One of 'no_restriction', 'only_open' or 'only_close' must be given, if this option is used.
    # But in fact it makes no sense to configure something here as the shutter will not be moved 
    # anymore as soon as the final position is reached. This option is mainly used at the
    # maintenance page of a configured instance, to temporarily restrict the movement manually.
    movement_restriction_height_manual: no_restriction
    movement_restriction_angle_manual: no_restriction
    #
    # Entities to restrict the movement direction
    #movement_restriction_height_entity:
    #movement_restriction_angle_entity:
    #
    # Entity to enforce the shutter positioning
    enforce_positioning_entity: input_boolean.d13_enforce_positioning
    #
    # =======================================================================
    # General facade configuration
    facade_azimuth_static: 180
    facade_offset_sun_in_static: -90
    facade_offset_sun_out_static: 90
    facade_elevation_sun_min_static: 0
    facade_elevation_sun_max_static: 90
    facade_slat_width_static: 95
    facade_slat_distance_static: 67
    facade_slat_angle_offset_static: 0
    facade_slat_min_angle_static: 0
    facade_shutter_stepping_height_static: 5
    facade_shutter_stepping_angle_static: 5
    facade_light_strip_width_static: 0
    facade_shutter_height_static: 1000
    facade_neutral_pos_height_manual: 0
    facade_neutral_pos_angle_manual: 0
    #facade_neutral_pos_height_entity: input_number.facade_neutral_pos_height_entity
    #facade_neutral_pos_angle_entity: input_number.facade_neutral_pos_angle_entity
    facade_max_movement_duration_static: 35
    facade_modification_tolerance_height_static: 8
    facade_modification_tolerance_angle_static: 5
    #
    # =======================================================================
    # Shadow configuration
    #shadow_control_enabled_entity:
    shadow_control_enabled_manual: true
    #shadow_brightness_threshold_entity:
    shadow_brightness_threshold_winter_manual: 50000
    #shadow_after_seconds_entity:
    shadow_after_seconds_manual: 15
    #shadow_shutter_max_height_entity:
    shadow_shutter_max_height_manual: 100
    #shadow_shutter_max_angle_entity:
    shadow_shutter_max_angle_manual: 100
    #shadow_shutter_look_through_seconds_entity:
    shadow_shutter_look_through_seconds_manual: 15
    #shadow_shutter_open_seconds_entity:
    shadow_shutter_open_seconds_manual: 15
    #shadow_shutter_look_through_angle_entity:
    shadow_shutter_look_through_angle_manual: 0
    #shadow_height_after_sun_entity:
    shadow_height_after_sun_manual: 0
    #shadow_angle_after_sun_entity:
    shadow_angle_after_sun_manual: 0
    #
    # =======================================================================
    # Dawn configuration
    #dawn_control_enabled_entity:
    dawn_control_enabled_manual: true
    #dawn_brightness_threshold_entity:
    dawn_brightness_threshold_manual: 500
    #dawn_after_seconds_entity:
    dawn_after_seconds_manual: 15
    #dawn_shutter_max_height_entity:
    dawn_shutter_max_height_manual: 100
    #dawn_shutter_max_angle_entity:
    dawn_shutter_max_angle_manual: 100
    #dawn_shutter_look_through_seconds_entity:
    dawn_shutter_look_through_seconds_manual: 15
    #dawn_shutter_open_seconds_entity:
    dawn_shutter_open_seconds_manual: 15
    #dawn_shutter_look_through_angle_entity:
    dawn_shutter_look_through_angle_manual: 50
    #dawn_height_after_dawn_entity:
    dawn_height_after_dawn_manual: 0
    #dawn_angle_after_dawn_entity:
    dawn_angle_after_dawn_manual: 0
```
# Status, Rückgabewerte und direkte Optionen

Jede Instanz von **Shadow Control** legt in Home Assistant ein Gerät an, unter dem diverse Entitäten zur weiteren Verwendung zur Verfügung stehen. Hier ein Beispiel, wie das aussieht:

![Sensoren](/images/sensors.png)

## Status-Werte

### Zielhöhe
`target_height`
Hier ist die verwendete Höhe des Behangs zu finden.

### Zielwinkel
`target_angle`
Hier ist der verwendete Lamellenwinkel des Behangs zu finden. Diese Entität ist nur bei Behangtyp `mode1` und `mode2` verfügbar.

### Zielwinkel in Grad
`target_angle_degrees`
Hier ist der verwendete Lamellenwinkel des Behangs in Grad (°) zu finden. Diese Entität ist nur bei Behangtyp `mode1` und `mode2` verfügbar.

### Kalkulatorische Zielhöhe
`computed_height`
Hier ist die errechnete Höhe des Behangs zu finden. Dieser Wert kann sich von der tatsächlich angefahrenen Höhe unterscheiden, wenn bspw. eine Bewegungseinschränkung aktiv ist.

### Kalkulatorischer Zielwinkel
`computed_angle`
Hier ist der errechnete Lamellenwinkel des Behangs zu finden. Dieser Wert kann sich von dem tatsächlich angefahrenen Lamellenwinkel unterscheiden, wenn bspw. eine Bewegungseinschränkung aktiv ist. Diese Entität ist nur bei Behangtyp `mode1` und `mode2` verfügbar.

### Aktueller Status
`current_state` / `current_state_text`
Der aktuelle interne Status von **Shadow Control** wird unter `current_state` als numerischer Wert ausgegeben. Dabei sind die folgenden Status resp. Werte möglich, welche für weitere eigenen Automatisierungen verwendet werden können:

* SHADOW_FULL_CLOSE_TIMER_RUNNING = 6
* SHADOW_FULL_CLOSED = 5
* SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING = 4
* SHADOW_HORIZONTAL_NEUTRAL = 3
* SHADOW_NEUTRAL_TIMER_RUNNING = 2
* SHADOW_NEUTRAL = 1
* NEUTRAL = 0
* DAWN_NEUTRAL = -1
* DAWN_NEUTRAL_TIMER_RUNNING = -2
* DAWN_HORIZONTAL_NEUTRAL = -3
* DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING = -4
* DAWN_FULL_CLOSED = -5
* DAWN_FULL_CLOSE_TIMER_RUNNING = -6

Parallel zu `current_state` wird in der Entität `current_state_text` die Textform des aktuellen Status ausgegeben. Diese Zeichenkette kann direkt auf dem UI verwendet werden, um den momentanen Status einer **Shadow Control** Instanz anzuzeigen.

### Sperr-Status
`lock_state`
Der Wert ist `True`, wenn die Integration gesperrt ist. Anderenfalls `False`.

### Nächste Behangmodifikation
`next_shutter_modification`
Auf dieser Entität steht der Zeitpunkt der nächsten Behang-Positionierung zur Verfügung, sofern gerade ein entsprechender Timer läuft.

### In der Sonne
`is_in_sun`
Der Wert ist `True`, wenn sich die Sonne im min-max-Offsetbereich und min-max-Höhenbereich befindet. Anderenfalls `False`.

## Direkte Optionen

Direkt auf der Geräteseite einer Instanz können diverse Optionen direkt geschaltet werden:

![Steuerelemente](/images/controls.png)

Das Ändern dieser Optionen entspricht dem Ändern der Konfiguration im ConfigFlow. Die Änderungen werden sofort übernommen und die Behangpositionierung wird entsprechend angepasst.

# Konfiguration-Export

Da die **Shadow Control** Konfiguration sehr umfangreich ist, gibt es einen speziellen Service, um die aktuelle Konfiguration im YAML-Format im Log auszugeben. 

## Vorarbeiten

Damit das funktioniert, muss der Log-Modus von Home Assistant mindestens auf `info` stehen. In `configuration.yaml` muss dazu der folgende Eintrag vorhanden sein:

```yaml
logger:
  default: info
```

Am einfachsten kommt man an die Log-Ausgabe über das Terminal oder die Home Assistant Konsole. Dort kann der folgende Befehl ausgeführt werden, um das Home Assistant Log kontinuierlich auszugeben:

```bash
tail -F ~/config/home-assistant.log
```

Sobald die Log-Ausgabe läuft, den Dump-Service ausführen und die Ausgabe im Terminal beobachten. Die Ausgabe des Log kann mit im Anschluss mit `Ctrl+C` beendet werden.

## Anwendung des Service

Der Service ist via `Entwicklerwerkzeuge -> Aktionen` und dort mit der Suche nach `dump_sc_config` zu finden. Wird der Service ohne weitere Konfiguration ausgeführt, wird die Konfiguration der ersten **Shadow Control** Instanz im Log ausgegeben. Das sieht (gekürzt) in etwa wie folgt aus:

```
2025-07-06 21:12:57.136 INFO (MainThread) [custom_components.shadow_control] [SC Dummy] === DUMPING INSTANCE CONFIGURATION ===
2025-07-06 21:12:57.136 INFO (MainThread) [custom_components.shadow_control] [SC Dummy] Full configuration:
--- YAML dump start ---
brightness_entity: input_number.d01_brightness
dawn_after_seconds_manual: 10.0
dawn_angle_after_dawn_manual: 80.0
...
name: SC Dummy
...
sun_azimuth_entity: input_number.d04_sun_azimuth
sun_elevation_entity: input_number.d03_sun_elevation
target_cover_entity:
- cover.sc_dummy
--- YAML dump end ---
2025-07-06 21:12:57.137 INFO (MainThread) [custom_components.shadow_control] [SC Dummy] Associated Device: SC Dummy (id: 8d9324...
2025-07-06 21:12:57.137 INFO (MainThread) [custom_components.shadow_control] [SC Dummy] Associated Entities:
2025-07-06 21:12:57.137 INFO (MainThread) [custom_components.shadow_control] [SC Dummy] - sensor.sc_dummy_hohe: State='80.0', A...
2025-07-06 21:12:57.137 INFO (MainThread) [custom_components.shadow_control] [SC Dummy] - sensor.sc_dummy_lamellenwinkel: State...
2025-07-06 21:12:57.138 INFO (MainThread) [custom_components.shadow_control] [SC Dummy] - sensor.sc_dummy_lamellenwinkel_grad: ...
2025-07-06 21:12:57.138 INFO (MainThread) [custom_components.shadow_control] [SC Dummy] - sensor.sc_dummy_status_numerisch: Sta...
2025-07-06 21:12:57.138 INFO (MainThread) [custom_components.shadow_control] [SC Dummy] - sensor.sc_dummy_sperrstatus: State='0...
2025-07-06 21:12:57.138 INFO (MainThread) [custom_components.shadow_control] [SC Dummy] - sensor.sc_dummy_nachste_positionierun...
2025-07-06 21:12:57.138 INFO (MainThread) [custom_components.shadow_control] [SC Dummy] - sensor.sc_dummy_in_der_sonne: State='...
2025-07-06 21:12:57.138 INFO (MainThread) [custom_components.shadow_control] [SC Dummy] - sensor.sc_dummy_status: State='shadow...
2025-07-06 21:12:57.138 INFO (MainThread) [custom_components.shadow_control] [SC Dummy] - switch.sc_dummy_debug_modus: State='o...
2025-07-06 21:12:57.138 INFO (MainThread) [custom_components.shadow_control] [SC Dummy] - switch.sc_dummy_beschattungssteuerung...
2025-07-06 21:12:57.138 INFO (MainThread) [custom_components.shadow_control] [SC Dummy] - switch.sc_dummy_dammerungssteuerung: ...
2025-07-06 21:12:57.139 INFO (MainThread) [custom_components.shadow_control] [SC Dummy] - switch.sc_dummy_sperren: State='off',...
2025-07-06 21:12:57.139 INFO (MainThread) [custom_components.shadow_control] [SC Dummy] - switch.sc_dummy_sperren_mit_zwangspos...
2025-07-06 21:12:57.139 INFO (MainThread) [custom_components.shadow_control] [SC Dummy] === END INSTANCE CONFIGURATION DUMP ===
```

Zwischen den beiden Marker-Zeilen `--- YAML dump start ---` und `--- YAML dump end ---` befindet sich die gesamte Konfiguration der Instanz im YAML-Format. Diese kann kopiert und gesichert oder auch als Basis für weitere Instanzen verwendet werden.

Die auszugebende Konfiguration kann durch Angabe des entsprechenden Namens wie folgt angegeben werden:

## UI-Modus

```
name: SC Dummy 3
```

## Yaml-Modus

```yaml
action: shadow_control.dump_sc_configuration
data:
  name: SC Dummy 3
```

Ausgabe dazu:

```
2025-07-06 23:05:48.246 INFO (MainThread) [custom_components.shadow_control] [SC Dummy 3] --- DUMPING INSTANCE CONFIGURATION - START ---
2025-07-06 23:05:48.246 INFO (MainThread) [custom_components.shadow_control] [SC Dummy 3] Config Entry Data: {'name': 'SC Dummy 3'}
...
```

[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Default-blue?style=for-the-badge&logo=homeassistantcommunitystore&logoColor=ccc

[ghs]: https://github.com/sponsors/starwarsfan
[ghsbadge]: https://img.shields.io/github/sponsors/starwarsfan?style=for-the-badge&logo=github&logoColor=ccc&link=https%3A%2F%2Fgithub.com%2Fsponsors%2Fstarwarsfan&label=Sponsors

[buymecoffee]: https://www.buymeacoffee.com/starwarsfan
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a-coffee-blue.svg?style=for-the-badge&logo=buymeacoffee&logoColor=ccc

[paypal]: https://paypal.me/ysswf
[paypalbadge]: https://img.shields.io/badge/paypal-me-blue.svg?style=for-the-badge&logo=paypal&logoColor=ccc

[hainstall]: https://my.home-assistant.io/redirect/config_flow_start/?domain=shadow_control
[hainstallbadge]: https://img.shields.io/badge/dynamic/json?style=for-the-badge&logo=home-assistant&logoColor=ccc&label=usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.shadow_control.total

[tests]: https://github.com/starwarsfan/shadow-control/actions/workflows/unittest.yml
[tests-badge]: https://img.shields.io/github/actions/workflow/status/starwarsfan/shadow-control/unittest.yml?style=for-the-badge&logo=github&logoColor=ccc&label=Tests

[coverage]: https://app.codecov.io/github/starwarsfan/shadow-control
[coverage-badge]: https://img.shields.io/codecov/c/github/starwarsfan/shadow-control?style=for-the-badge&logo=codecov&logoColor=ccc&label=Coverage
