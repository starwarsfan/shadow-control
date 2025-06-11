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

Shutter height position in state _NEUTRAL_. The integration will switch to _NEUTRAL_ if

* the integration is within a shadow- or a dawn-state and the corresponding regulation will be deactivated _or_
* the sun leaves the facade range.

Default: 0

#### Neutralwinkel
`facade_neutral_pos_angle_static`

Shutter angle position in state _NEUTRAL_. Everything else is described in the previous configuration entry. Default: 0

#### Lamellenbreite
`facade_slat_width_static`)

The Width of the shutter slats in mm. Width and distance are required to compute the angle, which is used to close the shutter only that much, to prevent direct sun rays within the room. The slat width must be larger than the slat distance, otherwise it's impossible to set up the correct shadow position. Default: 95

#### Lamellenabstand
`facade_slat_distance_static`

The distance of the shutter slats in mm. Everything else is described in the previous configuration entry. Default: 67

#### Shutter angle offset
`facade_slat_angle_offset_static`

Angle offset in %. This value will be added to the computed slat angle and could be used if the computed angle needs to be corrected. This could be necessary if the shadow position has a slight gap, which lets the sun pass through. Default: 0

#### Minimaler Lamellenwinkel
`facade_slat_min_angle_static`

Min shutter slat angle in %. The slat position will be in the range of this value and 100%. This option could be used to restrict the opening range of the shutter slats. Default: 0

#### Schrittweite Höhenpositionierung
`facade_shutter_stepping_height_static`

Stepping size for shutter height positioning. Most shutters could not handle repositioning of small values within the percent range. To handle this, the height will be modified in steps of a given size. Increasing or decreasing elevation of the sun will be handled properly. Default: 5

#### Schrittweite Lamellenwinkelpositionierung
`facade_shutter_stepping_angle_static`

Same as "Schrittweite Höhenpositionierung" but for the shutter slat angle positioning. Default: 5

#### Lichtstreifenbreite
`facade_light_strip_width_static`

Width of a desired light strip. With this setting could be configured, how "deep" the sun should shine directly into the room. According to this setting, during shadow the shutter will not be at a height position of 100% (aka full closed) but instead at a computed height position, which produces the desired light strip. Default: 0

#### Gesamthöhe
`facade_shutter_height_static`

To compute the light strip given with the previous configuration option, the integration needs to know the overall height of the shutter (or window). The same unit as on light bar width must be used. Default: 1000

#### Toleranz Höhenpositionierung
`facade_modification_tolerance_height_static`

Tolerance range for external shutter height modification. If the calculated height is within the range of current height plus/minus this value, the integration will not lock itself. Default: 8

#### Toleranz Lamellenwinkelpositionierung
`facade_modification_tolerance_angle_static`

Same as [Toleranz Höhenpositionierung](#tolerance-height-modification) but for the shutter slat angle. Default: 5

#### Behangtyp
`facade_shutter_type_static`

Konfiguration of the used shutter type.

Default is pivoting range of 0°-90°. These shutters are fully closed (vertical) at 90° and horizontally open at 0°.

The other possible shutter type has a movement range from 0°-180°, whereas these shutters are closed to the inside at 0°, horizontally open at 90°, and closed to the outside at 180°.





### Dynamische Eingänge

The options within this section are called "dynamic settings," as they might be modified "dynamically." That covers such things like position updates of the sun or modification of the integration behavior in general.

#### Helligkeit
`brightness_entity`

Siehe Beschreibung unter [Helligkeit](#brightness).

#### Helligkeit (Dämmerung)
`brightness_dawn_entity`

A second brightness value could be configured here, which is used to calculate shutter position at dawn. This is especially useful if 

* more than one brightness is used, e.g., with different sensors per facade and
* more than one facade should be automated, and so more than one integration is configured. 

If you're using more than one brightness sensor, you might set up an automation, which computes the median for all these values. After that, use that automation as input here. All the shutters will move to dawn position at the same time, even if it's currently brighter on one facade than on the other side of the building.

If you have only one brightness sensor, this input should not be configured. Let the input stay empty in this case.

#### Höhe der Sonne
`sun_elevation_entity`

Siehe Beschreibung unter [Höhe der Sonne](#sun-elevation).

#### Azimut der Sonne
`sun_azimuth_entity`

Siehe Beschreibung unter [Azimut der Sonne](#sun-azimuth).

#### Integration sperren
`lock_integration_entity`

If this input is set to 'off,' the integration works as desired by updating the output (as long as the input `lock_integration_with_position` is not set to 'on'). 

If the input is set to 'on,' the integration gets locked. That means the integration is internally still working, but the configured shutter will not be updated and stay at the current position. With this approach, the integration is able to immediately move the shutter to the right position, as soon as it gets unlocked again.

#### Integration sperren mit Zwangsposition
`lock_integration_with_position_entity`

If this input is set to 'off,' the integration works as desired by updating the output (as long as the input `lock_integration` is not set to 'on').

If the input is set to 'on,' the integration gets locked. That means the integration is internally still working, but the configured shutter will be moved to the position, configured with the inputs 'lock_height' and 'lock_angle.' With this approach, the integration is able to immediately move the shutter to the right position, as soon as it gets unlocked again.

This input has precedence over 'lock_integration.' If both lock inputs are set 'on,' the shutter will be moved to the configured lock position.

#### Sperrhöhe
`lock_height_entity`

Height in %, which should be set if integration gets locked by 'lock_integration_with_position.' 

#### Sperrwinkel
`lock_angle_entity`

Angle in %, which should be set if integration gets locked by 'lock_integration_with_position.'

#### Bewegungseinschränkung Höhenpositionierung
`movement_restriction_height_entity`

With this setting, the movement direction could be restricted:

* "No restriction" (Default)
  No striction on shutter movement. The automation will open or close the shutter.
* "Only close"
  In comparison to the current position, only closing positions will be activated.
* "Only open"
  In comparison to the current position, only opening positions will be activated.

This could be used to prevent shutters from being opened after the sun goes down and close them some minutes later because of starting dawn. This setting might be modified using a timer clock or other appropriate automation.

#### Bewegungseinschränkung Lamellenwinkelpositionierung
`movement_restriction_angle_entity`

Same as [Bewegungseinschränkung Höhenpositionierung](#movement-restriction-height) but for the shutter slat angle.





### Beschattungseinstellungen

The following options are available with two flavors for each configuration: Once as a static configuration and once as entity configuration. If you need to configure something without the possibility to change that value on demand, you should use the static configuration entry. If you need to modify something on demand, use the entity configuration and choose the corresponding entity, which holds the required value. If you change the used entity, it will be taken into account within the next execution of the integration instance.

#### Beschattungssteuerung aktiviert
`shadow_control_enabled_static` / `shadow_control_enabled_entity`

With this option, the whole shadow handling could be de-/activated. Default: on

#### Beschattung: Helligkeitsschwellwert
`shadow_brightness_threshold_static` / `shadow_brightness_threshold_entity`

This is the brightness threshold in Lux. If the threshold is exceeded, the timer `shadow_after_seconds` is started. Default: 50000 

#### Beschattung: Schliessen nach x Sekunden
`shadow_after_seconds_static` / `shadow_after_seconds_entity`

This is the number of seconds which should be passed after the exceedance of `shadow_brightness_threshold`, until the shutter will be moved to the shadow position. Default: 120

#### Beschattung: Maximale Höhe
`shadow_shutter_max_height_static` / `shadow_shutter_max_height_entity`

Max height of the shutter in case of shadow position in %. Default: 100 

#### Beschattung: Maximaler Lamellenwinkel
`shadow_shutter_max_angle_static` / `shadow_shutter_max_angle_entity`

Max angle of the shutter in case of shadow position in %. Default: 100 

#### Beschattung: Durchsichtposition nach x Sekunden
`shadow_shutter_look_through_seconds_static` / `shadow_shutter_look_through_seconds_entity`

If brightness falls below the value of `shadow_brightness_threshold`, the shutter slats will be moved to horizontal position after the configured number of seconds. Default: 900

#### Beschattung: Öffnen nach x Sekunden
`shadow_shutter_open_seconds_static` / `shadow_shutter_open_seconds_entity`

If brightness stays below the value of `shadow_brightness_threshold`, the shutter will be fully opened after the configured number of seconds. Default: 3600

#### Beschattung: Durchsichtswinkel
`shadow_shutter_look_through_angle_static` / `shadow_shutter_look_through_angle_entity`

This is the shutter slat angle in %, which should be used at the "look through" position. Default: 0

#### Beschattung: Höhe nach Beschattung
`shadow_height_after_sun_static` / `shadow_height_after_sun_entity`

This is the shutter height in %, which should be set after the shadow position. Default: 0

#### Beschattung: Lamellenwinkel nach Beschattung
`shadow_angle_after_sun_static` / `shadow_angle_after_sun_entity`

This is the shutter angle in %, which should be set after the shadow position. Default: 0





### Dämmerungseinstellungen

#### Dämmerungssteuerung aktiviert
`dawn_control_enabled_static` / `dawn_control_enabled_entity`

With this option, the whole dawn handling could be de-/activated. Default: on

#### Dämmerung: Helligkeitsschwellwert
`dawn_brightness_threshold_static` / `dawn_brightness_threshold_entity`

This is the brightness threshold in Lux. If the threshold is undercut, the timer `dawn_after_seconds` is started. Default: 500

#### Dämmerung: Schliessen nach x Sekunden
`dawn_after_seconds_static` / `dawn_after_seconds_entity`

This is the number of seconds which should be passed after `dawn_brightness_threshold` was undercut, until the shutter will be moved to the dawn position. Default: 120

#### Dämmerung: Maximale Höhe
`dawn_shutter_max_height_static` / `dawn_shutter_max_height_entity`

Max height of the shutter in case of dawn position in %. Default: 100

#### Dämmerung: Maximaler Lamellenwinkel
`dawn_shutter_max_angle_static` / `dawn_shutter_max_angle_entity`

Max angle of the shutter in case of shadow position in %. Default: 100

#### Dämmerung: Durchsichtposition nach x Sekunden
`dawn_shutter_look_through_seconds_static` / `dawn_shutter_look_through_seconds_entity`

If brightness exceeds the value of `dawn_brightness_threshold`, the shutter slats will be moved to horizontal position after the configured number of seconds. Default: 120

#### Dämmerung: Öffnen nach x Sekunden
`dawn_shutter_open_seconds_static` / `dawn_shutter_open_seconds_entity`

If brightness stays above the value of `dawn_brightness_threshold`, the shutter will be fully opened after the configured number of seconds. Default: 3600

#### Dämmerung: Durchsichtswinkel
`dawn_shutter_look_through_angle_static` / `dawn_shutter_look_through_angle_entity`

This is the shutter slat angle in %, which should be used at the "look through" position. Default: 0

#### Dämmerung: Höhe nach Beschattung
`dawn_height_after_dawn_static` / `dawn_height_after_dawn_entity`

This is the shutter height in %, which should be set after the shadow position. Default: 0

#### Dämmerung: Lamellenwinkel nach Beschattung
`dawn_angle_after_dawn_static` / `dawn_angle_after_dawn_entity`

This is the shutter angle in %, which should be set after the shadow position. Default: 0

