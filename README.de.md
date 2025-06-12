# Shadow Control

**Eine Home Assistant Integration zur vollständig automatischen Steuerung von Raffstoren.**

## Inhaltsverzeichnis

* [Shadow Control](#shadow-Control)
  * [Inhaltsverzeichnis](#inhaltsverzeichnis)
* [Einführung](#einführung)
* [Was macht **Shadow Control**?](#was-macht-shadow-control)
* [Konfiguration](#konfiguration)
  * [Initiale Instanzkonfiguration](#initiale-instanzkonfiguration)
    * [Name der Instanz](#name-der-instanz)
    * [Zu automatisierende Rollläden](#zu-automatisierende-rollläden)
    * [Azimut der Fassade](#azimut-der-fassade)
    * [Helligkeit](#helligkeit)
    * [Höhe der Sonne](#höhe-der-sonne)
    * [Azimut der Sonne](#azimut-der-sonne)
  * [Optionale Konfiguration](#optionale-konfiguration)
    * [Fassadenkonfiguration - Teil 1](#fassadenkonfiguration---teil-1)
      * [Zu automatisierende Rollläden](#zu-automatisierende-rollläden)
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
      * [Shutter angle offset](#shutter-angle-offset)
      * [Minimaler Lamellenwinkel](#minimaler-lamellenwinkel)
      * [Schrittweite Höhenpositionierung](#schrittweite-höhenpositionierung)
      * [Schrittweite Lamellenwinkelpositionierung](#schrittweite-lamellenwinkelpositionierung)
      * [Lichtstreifenbreite](#lichtstreifenbreite)
      * [Gesamthöhe](#gesamthöhe)
      * [Toleranz Höhenpositionierung](#toleranz-höhenpositionierung)
      * [Toleranz Lamellenwinkelpositionierung](#toleranz-lamellenwinkelpositionierung)
      * [Behangtyp](#behangtyp)
    * [Dynamische Eingänge](#dynamische-eingänge)
      * [Helligkeit](#brightness)
      * [Helligkeit Dawn](#brightness-Dawn)
      * [Höhe der Sonne](#sun-elevation)
      * [Azimut der Sonne](#sun-azimuth)
      * [Integration sperren](#integration-sperren)
      * [Integration sperren mit Zwangsposition](#integration-sperren-mit-zwangsposition)
      * [Sperrhöhe](#sperrhöhe)
      * [Sperrwinkel](#sperrwinkel)
      * [Bewegungseinschränkung Höhenpositionierung](#bewegungseinschränkung-höhenpositionierung)
      * [Bewegungseinschränkung Lamellenwinkelpositionierung](#bewegungseinschränkung-lamellenwinkelpositionierung)
      * [Zwangspositionierung auslösen](#zwangspositionierung-auslösen)
    * [Beschattungseinstellungen](#beschattungseinstellungen)
      * [Beschattungssteuerung aktiviert](#beschattungssteuerung-aktiviert)
      * [Beschattung: Helligkeitsschwellwert](#beschattung-helligkeitsschwellwert)
      * [Beschattung: Schliessen nach x Sekunden](#beschattung-schliessen-nach-x-sekunden)
      * [Beschattung: Maximale Höhe](#beschattung-maximale-höhe)
      * [Beschattung: Maximaler Lamellenwinkel](#beschattung-maximaler-lamellenwinkel)
      * [Beschattung: Durchsichtposition nach x Sekunden](#beschattung-durchsichtposition-nach-x-sekunden)
      * [Beschattung: Öffnen nach x Sekunden](#beschattung-öffnen-nach-x-sekunden)
      * [Beschattung: Durchsichtswinkel](#beschattung-durchsichtswinkel)
      * [Beschattung: Höhe nach Beschattung](#beschattung-höhe-nach-beschattung)
      * [Beschattung: Lamellenwinkel nach Beschattung](#beschattung-lamellenwinkel-nach-beschattung)
    * [Dämmerungseinstellungen](#dämmerungseinstellungen)
      * [Dämmerungssteuerung aktiviert](#dämmerungssteuerung-aktiviert)
      * [Dämmerung: Helligkeitsschwellwert](#dämmerung-helligkeitsschwellwert)
      * [Dämmerung: Schliessen nach x Sekunden](#dämmerung-schliessen-nach-x-sekunden)
      * [Dämmerung: Maximale Höhe](#dämmerung-maximale-höhe)
      * [Dämmerung: Maximaler Lamellenwinkel](#dämmerung-maximaler-lamellenwinkel)
      * [Dämmerung: Durchsichtposition nach x Sekunden](#dämmerung-durchsichtposition-nach-x-sekunden)
      * [Dämmerung: Öffnen nach x Sekunden](#dämmerung-öffnen-nach-x-sekunden)
      * [Dämmerung: Durchsichtswinkel](#dämmerung-durchsichtswinkel)
      * [Dämmerung: Höhe nach Beschattung](#dämmerung-höhe-nach-beschattung)
      * [Dämmerung: Lamellenwinkel nach Beschattung](#dämmerung-lamellenwinkel-nach-beschattung)

# Einführung

**Shadow Control** ist die Portierung des Edomi-LBS "Beschattungssteuerung-NG" für Home Assistant. Da Edomi [zum Tode verurteilt wurde](https://knx-user-forum.de/forum/projektforen/edomi/1956975-quo-vadis-edomi) und ich mit den bestehenden Beschattungslösungen nicht wirklich zufrieden war, habe ich mich dazu entschlossen, meinen LBS (Edomi-Bezeichnung für **L**ogic**B**au**S**tein) in eine Home Assistant Integration zu portieren. Das war ein sehr interessanter "Tauchgang" in die Hintergründe von Homa Assistant, der Idee dahinter und wie das Ganze im Detail funktioniert. Viel Spass mit der Integration.

In den folgenden Abschnitten gilt Folgendes:

* Das Wort "Fassade" ist gleichbedeutend mit "Fenster" oder "Tür", da es hier lediglich den Bezug zum Azimut eines Objektes in Blickrichtung von innen nach aussen darstellt.
* Das Wort "Behang" bezieht sich auf Raffstoren. In der Home Assistant Terminologie ist das ein "cover", was aus Sicht dieser Integration das Gleiche ist.
* Die gesamte interne Logik wurde ursprünglich für die Interaktion mit KNX-Systemen entwickelt. Der Hauptunterschied ist daher die Handhabung von Prozentwerten. **Shadow Control** wird mit Home Assistant korrekt interagieren aber die Konfiguration sowie die Logausgaben verwenden 0 % als geöffnet und 100 % als geschlossen.

# Was macht **Shadow Control**?

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
* [Beschattungssteuerung ein/aus](#beschattungssteuerung-aktiviert)
* [Dämmerungssteuerung ein/aus](#dämmerungssteuerung-aktiviert)

Der konfigurierte Behang wird nur dann neu positioniert, wenn sich die berechneten Werte seit dem letzten Lauf der Integration geändert haben. Damit wird die unnötige Neupositionierung der Raffstorenlamellen verhindert.

# Konfiguration

Die Konfiguration ist unterteilt in die minimalistische Initialkonfiguration sowie in eine separate Detailkonfiguration. Die Initialkonfiguration führt bereits zu einer vollständig funktionieren Behangautomatisierung, welche über die Detailkonfiguration bei Bedarf jederzeit angepasst werden kann.



## Initiale Instanzkonfiguration

Die initiale Instanzkonfiguration ist sehr minimalistisch und benötigt nur die folgenden Konfigurationswerte. Alle anderen Einstellungen werden mit Standardwerten vorbelegt, welche im Nachhinein an die persönlichen Wünsche angepasst werden können. Siehe dazu den Abschnitt ["Optionale Konfiguration"](#optionale-konfiguration).

### Name der Instanz
`name`

Ein beschreibender und eindeutiger Name für diese **Shadow Control** Instanz. Eine bereinigte Version dieses Namens wird zur Kennzeichnung der Log-Einträge in der Home Assistant Logdatei verwendet.

### Zu automatisierende Rollläden
`target_cover_entity`

Hier werden die zu steuernden Behang-Entitäten verbunden. Es können beliebig viele davon gleichzeitig gesteuert werden. Allerdings empfiehlt es sich, nur die Storen zu steuern, welche sich auf der gleichen Fassade befinden, also das gleiche Azimut haben. Für die alle weiteren internen Berechnungen wird der erste konfigurierte Behang herangezogen. Alle anderen Storen werden identisch positioniert.

### Azimut der Fassade
`facade_azimuth_static`

Azimut der Fassade in Grad, also die Blickrichtung von innen nach aussen. Eine perfekt nach Norden ausgerichtete Fassade hat ein Azimut von 0°, eine nach Süden ausgerichtete Fassade demzufolge 180°. Der Sonnenbereich dieser Fassade ist der Bereich, in dem die Beschattungssteuerung via **Shadow Control** erfolgen soll. Das ist maximal ein Bereich von 180°, also [Azimut der Fassade](#azimut-der-fassade) + [Beschattungsbeginn](#beschattungsbeginn) bis [Azimut der Fassade](#azimut-der-fassade) + [Beschattungsende](#beschattungsende).

### Helligkeit
`brightness_entity`

Aktuelle Helligkeit auf der Fassade. Im Regelfall kommt dieser Wert von einer Wetterstation und sollte der tatsächlichen Helligkeit auf dieser Fassade möglichst nah kommen.

### Höhe der Sonne
`sun_elevation_entity`

Hier wird die aktuelle Höhe (Elevation) der Sonne konfiguriert. Dieser Wert kommt ebenfalls von einer Wetterstation oder direkt von der Home Assistant Sonne-Entität. Gültig ist dabei der Bereich von 0° (horizontal) bis 90° (vertikal).

### Azimut der Sonne
`sun_azimuth_entity`

Hier wird der aktuelle Winkel (Azimut) der Sonne konfiguriert. Dieser Wert kommt ebenfalls von einer Wetterstation oder direkt von der Home Assistant Sonne-Entität. Gültig ist dabei der Bereich von 0° bis 359°.





## Optionale Konfiguration

The following options will be available by a separate config flow, which will open up with a click on "Configure" at the desired instance right on Settings > Integrations > **Shadow Control**.

### Fassadenkonfiguration - Teil 1

#### Zu automatisierende Rollläden
`target_cover_entity`

Siehe Beschreibung unter [Zu automatisierende Rollläden](#zu-automatisierende-rollläden).

#### Azimut der Fassade
`facade_azimuth_static`

Siehe Beschreibung unter [Azimut der Fassade](#azimut-der-fassade).

#### Beschattungsbeginn
`facade_offset_sun_in_static`

Negativoffset zum [Azimut der Fassade](#azimut-der-fassade), ab welchem die Beschattung erfolgen soll. Wenn das Azimut der Sonne kleiner ist als [Azimut der Fassade](#azimut-der-fassade) + [Beschattungsbeginn](#beschattungsbeginn), wird keine Beschattungsberechnung ausgelöst. Gültiger Wertebereich: -90–0, Standardwert: -90

#### Beschattungsende
`facade_offset_sun_out_static`

Positivoffset zum [Azimut der Fassade](#azimut-der-fassade), bis zu welchem die Beschattung erfolgen soll. Wenn das Azimut der Sonne grösser ist als [Azimut der Fassade](#azimut-der-fassade) + [Beschattungsende](#beschattungsende), wird keine Beschattungsberechnung ausgelöst. Gültiger Wertebereich: 0-90, Standardwert: 90

#### Minimale Sonnenhöhe
`facade_elevation_sun_min_static`

Minimale Höhe der Sonne in Grad. Ist die effektive Höhe kleiner als dieser Wert, wird keine Beschattungsberechnung ausgelöst. Ein Anwendungsfall dafür ist bspw. wenn sich vor der Fassade ein anderes Gebäude befindet, welches Schatten auf die Fassade wird, während die Wetterstation auf dem Dach noch voll in der Sonne ist. Wertebereich: 0-90, Standardwert: 0

Hinweis bzgl. "effektiver Höhe": Um den korrekten Lamellenwinkel zu berechnen, muss die Höhe der Sonne im rechten Winkel zur Fassade errechnet werden. Das ist die sog. "effektive Höhe", welche so auch im Log zu finden ist. Wenn die Beschattungssteuerung insbesondere im Grenzbereich der beiden Beginn- und Ende-Offsets nicht wie erwartet arbeitet, muss dieser Wert genauer betrachtet werden.

#### Maximale Sonnenhöhe
`facade_elevation_sun_max_static`

Maximale Höhe der Sonne in Grad. Ist die effektive Höhe grösser als dieser Wert, wird keine Beschattungsberechnung ausgelöst. Ein Anwendungsfall dafür ist bspw. wenn sich über der Fassade resp. dem Fenster ein Balkon befindet, welcher Schatten auf die Fassade wird, während die Wetterstation auf dem Dach noch voll in der Sonne ist. Wertebereich: 0-90, Standardwert: 90

#### Debugmodus
`debug_enabled`

Mit diesem Schalter kann der Debugmodus aktiviert werden. Damit werden erheblich mehr Informationen zum Verhalten und der Berechnung für diese Fassade ins Log geschrieben.



### Fassadenkonfiguration - Teil 2

#### Neutralhöhe
`facade_neutral_pos_height_static`

Behanghöhe in % in Neutralposition. Die Integration wird in die Neutralposition fahren, wenn mindestens eine der folgenden Bedingungen erfüllt ist: 

* Die Sonne befindet sich im Beschattungsbereich und die Beschattungsregelung wird deaktiviert
* Die Dämmerungsregelung wird deaktiviert
* Die Sonne verlässt den Beschattungsbereich

Standardwert: 0

#### Neutralwinkel
`facade_neutral_pos_angle_static`

Lamellenwinkel in % in Neutralposition. Alles andere identisch zu [Neutralhöhe](#neutralhöhe). Standardwert: 0

#### Lamellenbreite
`facade_slat_width_static`)

Die Breite der Lamellen in mm. Breite und Abstand werden benötigt, um den Lamellenwinkel zu berechnen, der benötigt wird, die Lamellen gerade so schräg zu stellen, dass kein direktes Sonnenlicht in den Raum fällt. Die Lamellenbreite muss zwingend grösser als der Lamellenabstand sein, anderenfalls ist es nicht möglich, eine korrekte Beschattungsposition anzufahren. Standardwert: 95

#### Lamellenabstand
`facade_slat_distance_static`

Der Abstand der Lamellen in mm. Alles andere siehe [Lamellenbreite](#lamellenbreite). Standardwert: 67

#### Shutter angle offset
`facade_slat_angle_offset_static`

Lamellenwinkeloffset in %. Dieser Wert wird zum berechneten Lamellenwinkel addiert. Er kann somit verwendet werden, um allfällige Ungenauigkeiten im Grenzbereich der Beschattung zu korrigieren. Das ist bspw. der Fall, wenn der Behang in Beschattungsposition ist aber dennoch ein schmaler Lichtstrahl hindurchfällt. Standardwert: 0

#### Minimaler Lamellenwinkel
`facade_slat_min_angle_static`

Minimaler Lamellenwinkel in %. Die Lamellen werden im Bereich von diesem Wert bis 100% positioniert. Damit kann diese Option dazu verwendet werden, den Öffnungsbereich zu begrenzen. Standardwert: 0

#### Schrittweite Höhenpositionierung
`facade_shutter_stepping_height_static`

Schrittweite der Höhenpositionierung. Die meissten Rollläden sind nicht in der Lage, sehr kleine Positionierungsschritte anzufahren. Um dem zu begegnen, kann hier die Schrittweite eingestellt werden, in welcher der Behang positioniert werden soll. Dabei wird berücksichtigt, ob die Sonne steigt oder fällt. Standardwert: 5

#### Schrittweite Lamellenwinkelpositionierung
`facade_shutter_stepping_angle_static`

Schrittweite der Lamellenwinkelpositionierung. Details siehe [Schrittweite Höhenpositionierung](#schrittweite-höhenpositionierung). Standardwert: 5

#### Lichtstreifenbreite
`facade_light_strip_width_static`

Breite eines nicht zu beschattenden Lichtstreifens am Boden. Mit dieser Einstellung wird festgelegt, wie tief oder weit die Sonne in den Raum hinein scheinen soll. Dementsprechend wird der Behang in der Höhe nicht 100% geschlossen sondern auf die Höhe gefahren, welche in den hier definierten Lichtstreifen resultiert. Standardwert: 0

#### Gesamthöhe
`facade_shutter_height_static`

Um den Lichtstreifen aus [Lichtstreifenbreite](#lichtstreifenbreite) zu berechnen, wird die Gesamthöhe des Behangs resp. des Fensters benötigt. Damit muss die gleiche Einheit verwendet werden, also bspw. beide Werte in mm. Standardwert: 1000

#### Toleranz Höhenpositionierung
`facade_modification_tolerance_height_static`

_Wird aktuell noch nicht ausgewertet!_

Toleranzbereich für externe Höhenmodifikation. Weicht die kalkulierte Höhe von der tatsächlichen Höhe +/- der hier angegebenem Toleranz ab, sperrt sich die Integration nicht selbst. Standardwert: 8

#### Toleranz Lamellenwinkelpositionierung
`facade_modification_tolerance_angle_static`

_Wird aktuell noch nicht ausgewertet!_

Toleranzbereich für externe Lamellenwinkelmodifikation, alles weitere siehe [Toleranz Höhenpositionierung](#toleranz-höhenpositionierung). Standardwert: 5

#### Behangtyp
`facade_shutter_type_static`

Der verwendete Behangtyp. Standardeinstellung ist der 90°-Behangtyp. Bei diesem Typ sind die Lamellen bei 0% waagerecht, also offen und bei 100% (i.d.R. nach aussen) vollständig geschlossen.

Der zweite mögliche Behangtyp hat einen Schwenkbereich von ca. 180°, also bei 0% (i.d.R. nach aussen) geschlossen, bei 50% waagerecht offen und bei 100% (i.d.R. nach innen) wiederum geschlossen.





### Dynamische Eingänge

Dieser Abschnitt konfiguriert die dynmischen Eingänge. Damit werden die Werte eingerichtet, welche sich im täglichen Betrieb ändern können wie bspw. der Sonnenstand oder andere Verhaltenseinstellungen der Integration.

#### Helligkeit
`brightness_entity`

Siehe Beschreibung unter [Helligkeit](#brightness).

#### Helligkeit (Dämmerung)
`brightness_dawn_entity`

Hier kann eine separate Helligkeit für die Dämmerungssteuerung eingestellt werden. Das ist insbesondere dann sinnvoll, wenn für die einzelnen **Shadow Control** Instanzen resp. Fassaden unterschiedliche Helligkeitssensoren verwendet werden, der Behang aber im gesamten Gebäude zur Dämmerung gleichzeitig geschlossen werden soll. 

In diesem Fall sollte über eine separate Automation bspw. der Mittelwert aus allen Helligkeiten berechnet und hier verknüpft werden. Damit werden alle Raffstoren gleichzeitig in die Dämmerungsposition gefahren.

Wenn nur eine Helligkeit für das gesamte Gebäude vorhanden ist, muss dieser Eingang leer bleiben.

#### Höhe der Sonne
`sun_elevation_entity`

Siehe Beschreibung unter [Höhe der Sonne](#sun-elevation).

#### Azimut der Sonne
`sun_azimuth_entity`

Siehe Beschreibung unter [Azimut der Sonne](#sun-azimuth).

#### Integration sperren
`lock_integration_entity`

Mit diesem Eingang kann die gesamte Integration gesperrt werden. Wird der Eingang auf 'off' gesetzt, arbeitet die Integration normal weiter, solange nicht [Integration sperren mit Zwangsposition](#integration-sperren-mit-zwangsposition) aktiv ist.

Wird der Eingang aktiviert, also auf 'on' gesetzt, arbeitet die Integration intern normal weiter, aktualisiert aber den verbundenen Behang nicht. Damit wird erreicht, dass beim Entsperren direkt die nun gültige Position angefahren werden kann. 

#### Integration sperren mit Zwangsposition
`lock_integration_with_position_entity`

Mit diesem Eingang kann die gesamte Integration gesperrt und eine Zwangsposition angefahren werden. Wird der Eingang auf 'off' gesetzt, arbeitet die Integration normal weiter, solange nicht [Integration sperren](#integration-sperren) aktiv ist.

Wird der Eingang aktiviert, also auf 'on' gesetzt, arbeitet die Integration intern normal weiter, fährt aber den Behang auf die via [Sperrhöhe](#sperrhöhe)/[Sperrwinkel](#sperrwinkel) konfigurierte Position. Damit wird erreicht, dass beim Entsperren direkt die nun gültige Position angefahren werden kann.

Dieser Eingang hat Vorrang vor [Integration sperren](#integration-sperren). Werden beide Sperren auf 'on' gesetzt, wird die Zwangsposition angefahren.

#### Sperrhöhe
`lock_height_entity`

Anzufahrende Höhe in %, wenn die Integration via [Integration sperren mit Zwangsposition](#integration-sperren-mit-zwangsposition) gesperrt wird.

#### Sperrwinkel
`lock_angle_entity`

Anzufahrender Lamellenwinkel in %, wenn die Integration via [Integration sperren mit Zwangsposition](#integration-sperren-mit-zwangsposition) gesperrt wird.

#### Bewegungseinschränkung Höhenpositionierung
`movement_restriction_height_entity`

Mit diesem Setting kann die Bewegungsrichtung der Höhenpositionierung wie folgt eingeschränkt werden

* "Keine Einschränkung" (Default)
  Keine Einschränkung der Höhenpositionierung. Die Integration wird den Behang öffnen oder schliessen.
* "Nur schliessen"
  Im Vergleich zur aktuellen Position werden nur weiter schliessende Positionen angefahren.
* "Nur öffnen"
  Im Vergleich zur aktuellen Position werden nur weiter öffnende Positionen angefahren.

Das kann dafür verwendet werden, dass der Behang nicht nach der Beschattung hoch gefahren und kurze Zeit später durch schnell einsetzende Dämmerung wieder heruntergefahren wird. Durch eine separate, bspw. tageszeitabhängige Automation, kann dieser Eingang entsprechend modifiziert werden.

#### Bewegungseinschränkung Lamellenwinkelpositionierung
`movement_restriction_angle_entity`

Siehe [Bewegungseinschränkung Höhenpositionierung](#bewegungseinschränkung-höhenpositionierung), hier nur für den Lamellenwinkel.

#### Zwangspositionierung auslösen
`enforce_positioning_entity`

Dieser Eingang kann mit einer Boolean-Entität verknüpft werden. Wird diese Entität auf 'on' gestellt, wird eine Zwangspositionierung ausgelöst. Das ist mitunter hilfreich, wenn die tatsächliche Behangposition nicht mehr mit der von der Integration angenommenen Position übereinstimmt.



### Beschattungseinstellungen

Die folgenden Einstellungen sind jeweils in zwei Ausprägungen vorhanden. Einmal als statischer Wert und einmal als Entität. Wird ein Wert fix konfiguriert und soll sich zur Laufzeit nicht ändern, wird das über die statische Konfiguration gemacht. Soll der Wert aber dynamisch angepasst werden, muss er mit einer entsprechenden Entität verknüpft werden.

#### Beschattungssteuerung aktiviert
`shadow_control_enabled_static` / `shadow_control_enabled_entity`

Mit dieser Option wird die Beschattungssteuerung ein- oder ausgeschaltet. Standardwert: ein

#### Beschattung: Helligkeitsschwellwert
`shadow_brightness_threshold_static` / `shadow_brightness_threshold_entity`

Hier wird der Helligkeitsschwellwert in Lux konfiguriert. Wird dieser Wert überschritten, startet der Timer [Beschattung: Schliessen nach x Sekunden](#beschattung-schliessen-nach-x-sekunden). Standardwert: 50000 

#### Beschattung: Schliessen nach x Sekunden
`shadow_after_seconds_static` / `shadow_after_seconds_entity`

Hier wird der Zeitraum in Sekunden konfiguriert, nachdem der Behang nach Überschreiten des [Helligkeitsschwellwertes](#beschattung-helligkeitsschwellwert) geschlossen werden soll. Standardwert: 120

#### Beschattung: Maximale Höhe
`shadow_shutter_max_height_static` / `shadow_shutter_max_height_entity`

Hier kann die maximale Behanghöhe angegeben werden. Das wird bspw. verwendet, um den Behang nicht bis ganz auf den Boden zu fahren, damit ein festfrieren im Winter vermieden wird. Standardwert: 100 

#### Beschattung: Maximaler Lamellenwinkel
`shadow_shutter_max_angle_static` / `shadow_shutter_max_angle_entity`

Hier kann der maximale Lamellenwinkel angegeben werden. Das wird bspw. verwendet, um den Behang nicht ganz zu schliessen, damit ein zusammenfrieren der Lamellen im Winter vermieden wird. Standardwert: 100

#### Beschattung: Durchsichtposition nach x Sekunden
`shadow_shutter_look_through_seconds_static` / `shadow_shutter_look_through_seconds_entity`

Fällt die Helligkeit unter den Schwellwert von [Beschattung: Helligkeitsschwellwert](#beschattung-helligkeitsschwellwert), wird der Behang nach der hier angegeben Zeit auf Durchsichtsposition gefahren. Standardwert: 900

#### Beschattung: Öffnen nach x Sekunden
`shadow_shutter_open_seconds_static` / `shadow_shutter_open_seconds_entity`

Nachdem der Behang auf Durchsichtsposition gefahren wurde, wird er nach der hier konfigurierten Zeit ganz geöffnet. Standardwert: 3600

#### Beschattung: Durchsichtswinkel
`shadow_shutter_look_through_angle_static` / `shadow_shutter_look_through_angle_entity`

Hier wird der Lamellenwinkel der Durchsichtsposition in % konfiguriert. Standardwert: 0

#### Beschattung: Höhe nach Beschattung
`shadow_height_after_sun_static` / `shadow_height_after_sun_entity`

Wenn keine Beschattungssituation mehr vorliegt, wird der Behang auf die hier in % konfigurierte Höhe gefahren. Standardwert: 0

#### Beschattung: Lamellenwinkel nach Beschattung
`shadow_angle_after_sun_static` / `shadow_angle_after_sun_entity`

Wenn keine Beschattungssituation mehr vorliegt, wird der Behang auf den hier in % konfigurierten Lamellenwinkel gefahren. Standardwert: 0






### Dämmerungseinstellungen

Wie die [Beschattungseinstellungen](#beschattungseinstellungen) sind auch die Dämmerungseinstellungen in jeweils in zwei Ausprägungen vorhanden. Einmal als statischer Wert und einmal als Entität. Wird ein Wert fix konfiguriert und soll sich zur Laufzeit nicht ändern, wird das über die statische Konfiguration gemacht. Soll der Wert aber dynamisch angepasst werden, muss er mit einer entsprechenden Entität verknüpft werden.

#### Dämmerungssteuerung aktiviert
`dawn_control_enabled_static` / `dawn_control_enabled_entity`

Mit dieser Option wird die Dämmerungssteuerung ein- oder ausgeschaltet. Standardwert: ein

#### Dämmerung: Helligkeitsschwellwert
`dawn_brightness_threshold_static` / `dawn_brightness_threshold_entity`

Hier wird der Helligkeitsschwellwert in Lux konfiguriert. Wird dieser Wert unterschritten, startet der Timer [Dämmerung: Schliessen nach x Sekunden](#dämmerung-schliessen-nach-x-sekunden). Standardwert: 500

#### Dämmerung: Schliessen nach x Sekunden
`dawn_after_seconds_static` / `dawn_after_seconds_entity`

Hier wird der Zeitraum in Sekunden konfiguriert, nachdem der Behang nach Unterschreiten des [Helligkeitsschwellwertes](#dämmerung-helligkeitsschwellwert) geschlossen werden soll. Standardwert: 120

#### Dämmerung: Maximale Höhe
`dawn_shutter_max_height_static` / `dawn_shutter_max_height_entity`

Hier kann die maximale Behanghöhe angegeben werden. Das wird bspw. verwendet, um den Behang nicht bis ganz auf den Boden zu fahren, damit ein festfrieren im Winter vermieden wird. Standardwert: 100

#### Dämmerung: Maximaler Lamellenwinkel
`dawn_shutter_max_angle_static` / `dawn_shutter_max_angle_entity`

Hier kann der maximale Lamellenwinkel angegeben werden. Das wird bspw. verwendet, um den Behang nicht ganz zu schliessen, damit ein zusammenfrieren der Lamellen im Winter vermieden wird. Standardwert: 100

#### Dämmerung: Durchsichtposition nach x Sekunden
`dawn_shutter_look_through_seconds_static` / `dawn_shutter_look_through_seconds_entity`

Steigt die Helligkeit über den Schwellwert von [Dämmerung: Helligkeitsschwellwert](#dämmerung-helligkeitsschwellwert), wird der Behang nach der hier angegeben Zeit auf Durchsichtposition gefahren. Standardwert: 120

#### Dämmerung: Öffnen nach x Sekunden
`dawn_shutter_open_seconds_static` / `dawn_shutter_open_seconds_entity`

Nachdem der Behang auf Durchsichtsposition gefahren wurde, wird er nach der hier konfigurierten Zeit ganz geöffnet. Standardwert: 3600

#### Dämmerung: Durchsichtswinkel
`dawn_shutter_look_through_angle_static` / `dawn_shutter_look_through_angle_entity`

Hier wird der Lamellenwinkel der Durchsichtsposition in % konfiguriert. Standardwert: 0

#### Dämmerung: Höhe nach Beschattung
`dawn_height_after_dawn_static` / `dawn_height_after_dawn_entity`

Wenn keine Dämmerungssituation mehr vorliegt, wird der Behang auf die hier in % konfigurierte Höhe gefahren. Standardwert: 0

#### Dämmerung: Lamellenwinkel nach Beschattung
`dawn_angle_after_dawn_static` / `dawn_angle_after_dawn_entity`

Wenn keine Dämmerungssituation mehr vorliegt, wird der Behang auf den hier in % konfigurierten Lamellenwinkel gefahren. Standardwert: 0

