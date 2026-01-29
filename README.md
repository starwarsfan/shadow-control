![logo](/images/logo.svg#gh-light-mode-only)
![logo](/images/dark_logo.svg#gh-dark-mode-only)

# Shadow Control

**A Home Assistant integration to fully automate movement and positioning of rolling shutters.**

![Version](https://img.shields.io/github/v/release/starwarsfan/shadow-control?style=for-the-badge)
[![Tests][tests-badge]][tests]
[![Coverage][coverage-badge]][coverage]
[![hacs_badge][hacsbadge]][hacs]
[![github][ghsbadge]][ghs]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]
[![PayPal][paypalbadge]][paypal]
[![hainstall][hainstallbadge]][hainstall]

Gehe zur [deutschen Version](/README.de.md) der Dokumentation.

## Table of content

* [Introduction](#introduction)
  * [TL;DR – in short](#tldr--in-short)
  * [What it does - long version](#what-it-does---long-version)
  * [Adaptive brightness control](#adaptive-brightness-control)
  * [Operating modes](#operating-modes)
  * [Entity precedence](#entity-precedence)
* [Installation](#installation)
* [Configuration](#configuration)
  * [Initial instance configuration](#initial-instance-configuration)
    * [Instance name ](#instance-name-)
    * [Shutter type](#shutter-type)
    * [Covers to maintain](#covers-to-maintain)
    * [Facade azimuth](#facade-azimuth)
    * [Brightness](#brightness)
    * [Sun elevation](#sun-elevation)
    * [Sun azimuth](#sun-azimuth)
  * [Additional options](#additional-options)
    * [Facade configuration - part 1](#facade-configuration---part-1)
      * [Covers to maintain](#covers-to-maintain)
      * [Facade azimuth](#facade-azimuth)
      * [Sun start offest](#sun-start-offest)
      * [Sun end offset](#sun-end-offset)
      * [Min sun elevation](#min-sun-elevation)
      * [Max sun elevation](#max-sun-elevation)
      * [Debug mode](#debug-mode)
    * [Facade configuration - part 2](#facade-configuration---part-2)
      * [Neutral position height](#neutral-position-height)
      * [Neutral position angle](#neutral-position-angle)
      * [Shutter slat width](#shutter-slat-width)
      * [Shutter slat distance](#shutter-slat-distance)
      * [Shutter angle offset](#shutter-angle-offset)
      * [Min shutter angle](#min-shutter-angle)
      * [Height stepping](#height-stepping)
      * [Angle stepping](#angle-stepping)
      * [Width of a light strip](#width-of-a-light-strip)
      * [Overall shutter height](#overall-shutter-height)
      * [Max movement duration](#max-movement-duration)
      * [Tolerance height modification](#tolerance-height-modification)
      * [Tolerance angle modification](#tolerance-angle-modification)
    * [Dynamic input entities](#dynamic-input-entities)
      * [Brightness](#brightness)
      * [Brightness at dawn](#brightness-at-dawn)
      * [Sun elevation](#sun-elevation)
      * [Sun azimuth](#sun-azimuth)
      * [Lock integration](#lock-integration)
      * [Lock integration with position](#lock-integration-with-position)
      * [Enforced position height](#enforced-position-height)
      * [Enforced position slat angle](#enforced-position-slat-angle)
      * [Movement restriction height](#movement-restriction-height)
      * [Movement restriction angle](#movement-restriction-angle)
      * [Enforce shutter positioning](#enforce-shutter-positioning)
    * [Shadow settings](#shadow-settings)
      * [S01 Control](#s01-control-enabled)
      * [S02 Winter threshold](#s02-winter-threshold)
      * [S03 Summer threshold](#s03-summer-threshold)
      * [S04 Threshold buffer summer/winter](#s04-threshold-buffer-summerwinter)
      * [S05 after seconds](#s05-after-seconds)
      * [S06 max height](#s06-max-height)
      * [S07 max angle](#s07-max-angle)
      * [S08 Look through](#s08-look-through)
      * [S09 Look through angle](#s09-look-through-angle)
      * [S10 Open after](#s10-open-after)
      * [S11 Height after](#s11-height-after)
      * [S12 Angle after](#s12-angle-after)
    * [Dawn settings](#dawn-settings)
      * [D01 Control enabled](#d01-control-enabled)
      * [D02 Threshold](#d02-threshold)
      * [D03 after seconds](#d03-after-seconds)
      * [D04 max height](#d04-max-height)
      * [D05 max angle](#d05-max-angle)
      * [D06 Look through after](#d06-look-through-after)
      * [D07 Look through angle](#d07-look-through-angle)
      * [D08 Open after seconds](#d08-open-after-seconds)
      * [D09 Height after seconds](#d09-height-after-seconds)
      * [D10 Angle after seconds](#d10-angle-after-seconds)
  * [Configuration by yaml](#configuration-by-yaml)
    * [Example YAML configuration](#example-yaml-configuration)
* [State, return values and direct options](#state-return-values-and-direct-options)
  * [State and return values](#state-and-return-values)
    * [Target height](#target-height)
    * [Target angle](#target-angle)
    * [Target angle (degrees)](#target-angle-degrees)
    * [Computed height](#computed-height)
    * [Computed angle](#computed-angle)
    * [Current state](#current-state)
    * [Lock state](#lock-state)
    * [Next shutter modification](#next-shutter-modification)
    * [Is in the Sun](#is-in-the-sun)
  * [Direct options](#direct-options)
* [Configuration export](#configuration-export)
  * [Preparation](#preparation)
  * [Usage](#usage)
  * [UI mode](#ui-mode)
  * [YAML mode](#yaml-mode)

# Introduction

**Shadow Control** is the migration of my Edomi-LBS "Beschattungssteuerung-NG" to Home Assistant. As Edomi was [sentenced to death](https://knx-user-forum.de/forum/projektforen/edomi/1956975-quo-vadis-edomi) and because I'm not really happy with the existing solutions to automate my shutters, I decided to migrate my LBS (Edomi name for **L**ogic**B**au**S**tein, a logic block) to a Home Assistant integration. To do so was a nice deep dive into the backgrounds of Home Assistant, the idea behind and how it works. Feel free to use the integration on your needs.



## TL;DR – in short

* Control venetian blinds or vertical blinds based on brightness thresholds and timers
* Adaptive brightness control
* Height and slat angle are separately configurable for shadow and dawn
  * Shadow respectively dawn position after a brightness threshold plus time X
  * Look through position after a brightness threshold plus time Y
  * Open after time Z
* Sun area restrictable
* Lockable positioning
* Restrictable movement direction
* Configurable "no shadow" area
* Configurable stepping
* Separate entity for dawn positioning possible
* Configuration using ConfigFlow or YAML is possible

## What it does - long version

Based on several input values, the integration handles the positioning of rolling shutters. To do so, the integration needs to be configured with the azimuth of the facade, for which the shutters should be controlled. Additionally, some offset and min-max values will be used to define the area within the facade is illuminated by the sun. If the sun is within that range and the configured brightness threshold is exceeded for a (also configurable) amount of time, the shutters will be positioned to prevent direct sunlight in the room.

The determined shutter height and tilt angle depend on the current brightness, configured thresholds, dimensions of your shutter slats, some timers, and more settings. The different timers will be activated according to the current state of the integration.



## Adaptive brightness control

_Note: The functionality of the adaptive brightness threshold is based on Edomi-LBS 19001445 by Hardy Köpf (harry7922). Thank you!_

Between sunrise and sunset, a brightness threshold is calculated using a sine curve with a daily maximum value. This daily maximum value is determined using a linear formula. This serves to compensate for the variance in brightness between winter and summer.

The sun reaches its highest point at the summer solstice. This occurs annually on June 21st in the Northern Hemisphere and on December 21st in the Southern Hemisphere. **Shadow Control** determines whether the Home Assistant instance is located in the Northern or Southern Hemisphere based on its geographic coordinates. Using the summer solstice date, a daily brightness threshold is calculated via a linear formula. In midsummer, clear skies and sunshine are only considered present at a higher LUX value, while in winter, significantly lower LUX levels are required. The lower and upper limits define the variance between winter and summer. This allows for user-defined brightness levels in midsummer and winter to trigger shading. The daily maximum brightness is then calculated using a linear function between these two values. The lowest point of the sine curve, and therefore the lowest shading threshold, is the configured dawn threshold plus a safety margin.

The configuration options for this feature are [S02 Winter threshold](#s02-winter-threshold), [S03 Summer threshold](#s03-summer-threshold) and [S04 Threshold buffer summer/winter](#s04-threshold-buffer-summerwinter).



## Operating modes

In general, there are two different operation modes: _Shadow_ and _Dawn_. Both modes will be configured independently.

The integration will be triggered by updating the following entities: 

* [Brightness](#brightness)
* [Brightness (dawn)](#brightness-dawn)
* [Sun elevation](#sun-elevation)
* [Sun azimuth](#sun-azimuth)
* [Lock integration](#lock-integration)
* [Lock integration with position](#lock-integration-with-position)
* [Shadow handling dis-/enabled state](#s01-control)
* [S06 max height](#s06-max-height)
* [S07 max angle](#s07-max-angle)
* [Dawn handling dis-/enabled state](#d01-control-enabled)
* [D04 max height](#d04-max-height)
* [D05 max angle](#d05-max-angle)
* [enforce shutter positioning](#enforce-shutter-positioning)

The configured cover entity will only be updated if a value has changed since the last run of the integration, which prevents unnecessary movements.



## Entity precedence
Attention: For all options the configured entity variant takes precedence! That means if a entity is configured, the entity value will be used. Additionally the internal entity for this option will be removed. To prevent this, you need to clear the entity configuration.



# Installation

**Shadow Control** is a default HACS integration, so you can install the integration by searching for it within HACS. After that, restart Home-Assistant and add the integration.

Within further description:

* The word "facade" is similar to "window" or "door," as it simply references the azimuth of an object in the sense of viewing direction from within that object to the outside.
* The word "shutter" references rolling shutters. In the Home Assistant terminology, this is called a "cover". From the pov of this integration it's the same.
* The whole internal logic was initially developed to interact with a KNX system, so the main difference is the handling of %-values. **Shadow Control** will interact with Home Assistant correct, but the configuration as well as the log output is using 0% as fully open and 100% as fully closed.
* Most options
  * provide own controls, which could be modified on the instance view. So they could be modified easily there.
  * can be configured with own entities. As soon as this possibility is used, there's no control created but a corresponding sensor, which displays the current value of the connected entity. So the used values could be dynamically modified like with a automation in front of the instance.



# Configuration

The configuration is split into a minimalistic initial configuration, which results in a fully working cover automation and a separate configuration flow of all available options.



## Initial instance configuration

The initial instance configuration is very minimalistic and requires only the following configuration entries. Everything else will be setup up with default values, which you might tweak to your needs afterward. See section [Additional options](#additional-options).

### Instance name 
(yaml: `name`)

A descriptive and unique name for this **Shadow Control** instance. A sanitized version of this name will be used to mark corresponding log entries of this instance within the Home Assistant main log file as well as prefix for the created entities.

Example:
1. The instance is named "Dining room door"
2. The sanitized name will be "dining_room_door"
3. Log entries start with ``
4. Entities will be named e. g. like ``

#### Shutter type
(yaml: `facade_shutter_type_static`)

Configuration of the used shutter type. Default is pivoting range of 0°-90° (yaml: `mode1`). These shutters are fully closed (vertical) at 90° and horizontally open at 0°.

Other supported types:

* Shutter type with a movement range from 0°-180° (yaml: `mode2`), whereas these shutters are closed to the inside at 0°, horizontally open at 90°, and closed to the outside at 180°.
* Vertical blinds (yaml: `mode3`). With this type all the angle settings will be suppressed.

This setting can't be changed later on. To do so, you need to remove the instance of the shutter and recreate it from scratch.

### Covers to maintain
(yaml: `target_cover_entity`)

The cover entities, which should be handled by this **Shadow Control** instance. You can add as many covers as you like, but the recommendation is to use only these covers, which have at least the same azimuth. For any further calculation, only the first configured cover will be used. All other covers will just be positioned as the first one.

Within yaml you need to use the list syntax:
```yaml
    target_cover_entity:
      - cover.fenster_buro_1
      - cover.fenster_buro_2
```

### Facade azimuth
(yaml: `facade_azimuth_static`)

Azimuth of the facade in degrees, for which the integration should be configured. This is the viewing direction from the inside to the outside. A perfectly north facade has an Azimuth of 0°, a perfectly south facade has an Azimuth of 180°. The sun area at this facade is the range, from which a shadow handling is desired. This is a maximal range of 180°, from `azimuth_facade` + `offset_sun_in` to `azimuth_facade` + `offset_sun_out`.

rdeckard has provided a nice drawing to the Edomi-LBS, which is still valid at this point:

![Azimuth explanation](/images/azimut.png)

### Brightness
(yaml: `brightness_entity`)

This input needs to be configured with the current brightness, which usually comes from a weather station. The value should match the real brightness on this facade as much as possible.

### Sun elevation
(yaml: `sun_elevation_entity`)

This input should be filled with the current elevation of the sun. Usually this value comes from a weather station or the home assistant internal sun entity. Possible values are within the range from 0° (horizontal) to 90° (vertical).

### Sun azimuth
(yaml: `sun_azimuth_entity`)

This input should be filled with the current azimuth of the sun. Usually this value comes from a weather station or the home assistant internal sun entity. Possible values are within the range from 0° to 359°.

sunrise_entity
sunset_entity



## Additional options

The following options will be available by a separate config flow, which will open up with a click on "Configure" at the desired instance right on Settings > Integrations > **Shadow Control**.

### Facade configuration - part 1

#### Covers to maintain

See the description at [Covers to maintain](#covers-to-maintain).

#### Facade azimuth

See the description at [Facade azimuth](#facade-azimuth).

#### Sun start offest
(yaml: `facade_offset_sun_in_static`)

Negative offset to `facade_azimuth_static`, from which shadow handling should be done. If the azimuth of the sun is lower than `facade_azimuth_static + facade_offset_sun_in_static`, no shadow handling will be performed. Valid range: -90–0, default: -90

#### Sun end offset
(yaml: `facade_offset_sun_out_static`)

Positive offset to `facade_azimuth_static`, up to which shadow handling should be done. If the azimuth of the sun is higher than `facade_azimuth_static + facade_offset_sun_out_static`, no shadow handling will be performed. Valid range: 0–90, default: 90

#### Min sun elevation
(yaml: `facade_elevation_sun_min_static`)

Minimal elevation (height) of the sun in degrees. If the effective (!) elevation is lower than this value, no shadow handling will be performed. A use case for this configuration is another building in front of the facade, which throws shadow onto the facade, whereas the weather station on the roof is still full in the sun. Valid range: 0–90, default: 0

Hint regarding effective elevation: To compute the right shutter angle, the elevation of the sun in the right angle to the facade must be computed. This so-called "effective elevation" is written to the log. If the shadow handling is not working as desired, especially nearly the limits of the given azimuth offsets, this value needs attention.

#### Max sun elevation
(yaml: `facade_elevation_sun_max_static`)

Maximal elevation (height) of the sun in degrees. If the effective (!) elevation is higher than this value, no shadow handling will be performed. A use case for this configuration is a balcony from the story above, which throws shadow onto the facade, whereas the weather station on the roof is still full in the sun. Valid range: 0–90, default: 90

#### Debug mode
(yaml: `debug_enabled`)

With this switch, the debug mode for this instance could be activated. If activated, there will be much more detailed output within the Home Assistant main log file.



### Facade configuration - part 2

#### Neutral position height
(yaml: `facade_neutral_pos_height_manual`)

Shutter height position in state _NEUTRAL_. The integration will switch to _NEUTRAL_ if

* the integration is within a shadow- or a dawn-state and the corresponding regulation will be deactivated _or_
* the dawn mode is deactivated
* the sun leaves the facade range.

Default: 0

#### Neutral position angle
(yaml: `facade_neutral_pos_angle_manual`)

Shutter angle position in state _NEUTRAL_. Everything else is described in the previous configuration entry. Default: 0

#### Shutter slat width
(yaml: `facade_slat_width_static`)

The Width of the shutter slats in mm. Width and distance are required to compute the angle, which is used to close the shutter only that much, to prevent direct sun rays within the room. The slat width must be larger than the slat distance, otherwise it's impossible to set up the correct shadow position. Default: 95

#### Shutter slat distance
(yaml: `facade_slat_distance_static`)

The distance of the shutter slats in mm. Everything else is described in the previous configuration entry. Default: 67

#### Shutter angle offset
(yaml: `facade_slat_angle_offset_static`)

Angle offset in %. This value will be added to the computed slat angle and could be used if the computed angle needs to be corrected. This could be necessary if the shadow position has a slight gap, which lets the sun pass through. Default: 0

#### Min shutter angle
(yaml: `facade_slat_min_angle_static`)

Min shutter slat angle in %. The slat position will be in the range of this value and 100%. This option could be used to restrict the opening range of the shutter slats. Default: 0

#### Height stepping
(yaml: `facade_shutter_stepping_height_static`)

Stepping size for shutter height positioning. Most shutters could not handle repositioning of small values within the percent range. To handle this, the height will be modified in steps of a given size. Increasing or decreasing elevation of the sun will be handled properly. Default: 5

#### Angle stepping
(yaml: `facade_shutter_stepping_angle_static`)

Same as "Height stepping" but for the shutter slat angle positioning. Default: 5

#### Width of a light strip
(yaml: `facade_light_strip_width_static`)

Width of a desired light strip. With this setting could be configured, how "deep" the sun should shine directly into the room. According to this setting, during shadow the shutter will not be at a height position of 100% (aka full closed) but instead at a computed height position, which produces the desired light strip. Default: 0

#### Overall shutter height
(yaml: `facade_shutter_height_static`)

To compute the light strip given with the previous configuration option, the integration needs to know the overall height of the shutter (or window). The same unit as on light bar width must be used. Default: 1000

#### Max movement duration
(yaml: `facade_max_movement_duration_static`)

Define the movement duration from fully closed (down) to fully open (up) in seconds. This is required to handle automatic instance lock properly in case the shutter position is modified manually.

#### Tolerance height modification
(yaml: `facade_modification_tolerance_height_static`)

Tolerance range for external shutter height modification. If the calculated height is within the range of current height plus/minus this value, the integration will not lock itself. Default: 8

#### Tolerance angle modification
(yaml: `facade_modification_tolerance_angle_static`)

Same as [Tolerance height modification](#tolerance-height-modification) but for the shutter slat angle. Default: 5





### Dynamic input entities

The options within this section are called "dynamic settings," as they might be modified "dynamically." That covers such things like position updates of the sun or modification of the integration behavior in general.

#### Brightness

See the description at [Brightness](#brightness).

#### Brightness at dawn
(yaml: `brightness_dawn_entity`)

A second brightness value could be configured here, which is used to calculate shutter position at dawn. This is especially useful if 

* more than one brightness is used, e.g., with different sensors per facade and
* more than one facade should be automated, and so more than one integration is configured. 

If you're using more than one brightness sensor, you might set up an automation, which computes the median for all these values. After that, use that automation as input here. All the shutters will move to dawn position at the same time, even if it's currently brighter on one facade than on the other side of the building.

If you have only one brightness sensor, this input should not be configured. Let the input stay empty in this case.

#### Sun elevation

See the description at [Sun elevation](#sun-elevation).

#### Sun azimuth

See the description at [Sun azimuth](#sun-azimuth).

#### Lock integration
(yaml: `lock_integration_manual: true|false` u/o `lock_integration_entity: <entity>`)

If this input is set to 'off,' the integration works as desired by updating the output (as long as the input `lock_integration_with_position` is not set to 'on'). 

If the input is set to 'on,' the integration gets locked. That means the integration is internally still working, but the configured shutter will not be updated and stay at the current position. With this approach, the integration is able to immediately move the shutter to the right position, as soon as it gets unlocked again.

Attention, see note at [Entity precedence](#entity-precedence).

#### Lock integration with position
(yaml: `lock_integration_with_position_manual: true|false` u/o `lock_integration_with_position_entity: <entity>`)

If this input is set to 'off,' the integration works as desired by updating the output (as long as the input `lock_integration` is not set to 'on').

If the input is set to 'on,' the integration gets locked. That means the integration is internally still working, but the configured shutter will be moved to the position, configured with the inputs 'lock_height' and 'lock_angle.' With this approach, the integration is able to immediately move the shutter to the right position, as soon as it gets unlocked again.

This input has precedence over 'lock_integration.' If both lock inputs are set 'on,' the shutter will be moved to the configured lock position.

Attention, see note at [Entity precedence](#entity-precedence).

#### Enforced position height
(yaml: `lock_height_manual: true|false` u/o `lock_height_entity: <entity>`)

Height in %, which should be set if integration gets locked by 'lock_integration_with_position.' 

Attention, see note at [Entity precedence](#entity-precedence).

#### Enforced position slat angle
(yaml: `lock_angle_manual: true|false` u/o `lock_angle_entity: <entity>`)

Angle in %, which should be set if integration gets locked by 'lock_integration_with_position.'

Attention, see note at [Entity precedence](#entity-precedence).

#### Movement restriction height
(yaml: `movement_restriction_height_manual: true|false` u/o `movement_restriction_height_entity: <entity>`)

With this setting, the movement direction could be restricted:

* "No restriction" (default value):
  No restriction on shutter movement. The automation will open or close the shutter.
* "Only close":
  In comparison to the last (previous) position, only closing positions will be activated.
* "Only open":
  In comparison to the last (previous) position, only opening positions will be activated.

This could be used to prevent shutters from being opened after the sun goes down and close them some minutes later because of starting dawn. This setting might be modified using a timer clock or other appropriate automation.

Attention, see note at [Entity precedence](#entity-precedence).

#### Movement restriction angle
(yaml: `movement_restriction_angle_manual: true|false` u/o `movement_restriction_angle_entity: <entity>`)

Same as [Movement restriction height](#movement-restriction-height) but for the shutter slat angle.

Attention, see note at [Entity precedence](#entity-precedence).

#### Enforce shutter positioning
(yaml: `enforce_positioning_entity: <entity>`)

This input could be wired with a boolean entity. If this entity is switched to "on," the shutter positioning will be enforced. That means that with every run of the integration, the shutter will be positioned. This could be used to align the shutter position with the computed position of the integration but should normally not be activated all the time. Otherwise, the shutter slats might close and immediately open again as that is how rolling shutters work: At first the move to the given height and position the shutter slats afterward.

Additionally to the previous entity configuration, this push button entity could be used to enforce the shutter positioning once. If this button is pressed, the shutter will be positioned according to the computed values.





### Shadow settings

The shading settings use the prefix **S&lt;number&gt;** to achieve a logical grouping and order of the options. This ensures that the configured values are displayed in this order in the instance view. Note that an option is only visible under **Controls** if no entity has been configured for it. Otherwise, it can be found under **Sensors** and displays the value of the configured entity. Here is an example of the beginning of the controls:

![Controls](/images/controls.png)



#### S01 Control enabled
(yaml: `shadow_control_enabled_manual: true|false` u/o `shadow_control_enabled_entity: <entity>`)

With this option, the whole shadow handling could be de-/activated. Default: on

#### S02 Winter threshold
(yaml: `shadow_brightness_threshold_winter_manual: true|false` u/o `shadow_brightness_threshold_winter_entity: <entity>`)

This is the brightness threshold in Lux. If the threshold is exceeded, the timer `shadow_after_seconds` is started. Default: 30000 

Together with the parameters [S03 Summer threshold](#s03-summer-threshold) and [S04 Threshold buffer summer/winter](#s04-threshold-buffer-summerwinter) the brightness difference between summer and winter could be handled. To do so, a sine curve between the two threshold values is computed, where the top of the curve is at summer solstice. Northern and Southern Hemisphere will be handled according to the location of the Home Assistant instance. The sine value for the current day is used as the effective brightness threshold.

This functionality will be used as soon as the value of [S03 Summer threshold](#s03-summer-threshold) is configured with a greater value than this one.

#### S03 Summer threshold
(yaml: `shadow_brightness_threshold_summer_manual: true|false` u/o `shadow_brightness_threshold_summer_entity: <entity>`)

Second value for sine curve computation. For details see previous option [S02 Winter threshold](#s02-winter-threshold). Default: 50000

#### S04 Threshold buffer summer/winter
(yaml: `shadow_brightness_threshold_buffer_manual: true|false` u/o `shadow_brightness_threshold_buffer_entity: <entity>`)

This value is used to shift the entire sine curve from the previous two options upwards to avoid false triggers in the limiting range of shading. For details see [S02 Winter threshold](#s02-winter-threshold). Default: 1000

#### S05 after seconds
(yaml: `shadow_after_seconds_manual: true|false` u/o `shadow_after_seconds_entity: <entity>`)

This is the number of seconds which should be passed after the exceedance of `shadow_brightness_threshold`, until the shutter will be moved to the shadow position. Default: 120

#### S06 max height
(yaml: `shadow_shutter_max_height_manual: true|false` u/o `shadow_shutter_max_height_entity: <entity>`)

Max height of the shutter in case of shadow position in %. Default: 100 

#### S07 max angle
(yaml: `shadow_shutter_max_angle_manual: true|false` u/o `shadow_shutter_max_angle_entity: <entity>`)

Max angle of the shutter in case of shadow position in %. Default: 100 

#### S08 Look through
(yaml: `shadow_shutter_look_through_seconds_manual: true|false` u/o `shadow_shutter_look_through_seconds_entity: <entity>`)

If brightness falls below the value of `shadow_brightness_threshold`, the shutter slats will be moved to horizontal position after the configured number of seconds. Default: 900

#### S09 Look through angle
(yaml: `shadow_shutter_look_through_angle_manual: true|false` u/o `shadow_shutter_look_through_angle_entity: <entity>`)

This is the shutter slat angle in %, which should be used at the "look through" position. Default: 0

#### S10 Open after
(yaml: `shadow_shutter_open_seconds_manual: true|false` u/o `shadow_shutter_open_seconds_entity: <entity>`)

If brightness stays below the value of `shadow_brightness_threshold`, the shutter will be fully opened after the configured number of seconds. Default: 3600

#### S11 Height after
(yaml: `shadow_height_after_sun_manual: true|false` u/o `shadow_height_after_sun_entity: <entity>`)

This is the shutter height in %, which should be set after the shadow position. Default: 0

#### S12 Angle after
(yaml: `shadow_angle_after_sun_manual: true|false` u/o `shadow_angle_after_sun_entity: <entity>`)

This is the shutter angle in %, which should be set after the shadow position. Default: 0





### Dawn settings

The dawn settings use the prefix **D&lt;number&gt;** to achieve a logical grouping and order of the options. This ensures that the configured values are displayed in this order in the instance view. Note that an option is only visible under **Controls** if no entity has been configured for it. Otherwise, it can be found under **Sensors** and displays the value of the configured entity. Here is an example of the beginning of the controls:

![Controls](/images/controls.png)



#### D01 Control enabled
(yaml: `dawn_control_enabled_manual: true|false` u/o `dawn_control_enabled_entity: <entity>`)

With this option, the whole dawn handling could be de-/activated. Default: on

#### D02 Threshold
(yaml: `dawn_brightness_threshold_manual: true|false` u/o `dawn_brightness_threshold_entity: <entity>`)

This is the brightness threshold in Lux. If the threshold is undercut, the timer `dawn_after_seconds` is started. Default: 500

#### D03 after seconds
(yaml: `dawn_after_seconds_manual: true|false` u/o `dawn_after_seconds_entity: <entity>`)

This is the number of seconds which should be passed after `dawn_brightness_threshold` was undercut, until the shutter will be moved to the dawn position. Default: 120

#### D04 max height
(yaml: `dawn_shutter_max_height_manual: true|false` u/o `dawn_shutter_max_height_entity: <entity>`)

Max height of the shutter in case of dawn position in %. Default: 100

#### D05 max angle
(yaml: `dawn_shutter_max_angle_manual: true|false` u/o `dawn_shutter_max_angle_entity: <entity>`)

Max angle of the shutter in case of dawn position in %. Default: 100

#### D06 Look through after
(yaml: `dawn_shutter_look_through_seconds_manual: true|false` u/o `dawn_shutter_look_through_seconds_entity: <entity>`)

If brightness exceeds the value of `dawn_brightness_threshold`, the shutter slats will be moved to horizontal position after the configured number of seconds. Default: 120

#### D07 Look through angle
(yaml: `dawn_shutter_look_through_angle_manual: true|false` u/o `dawn_shutter_look_through_angle_entity: <entity>`)

This is the shutter slat angle in %, which should be used at the "look through" position. Default: 0

#### D08 Open after seconds
(yaml: `dawn_shutter_open_seconds_manual: true|false` u/o `dawn_shutter_open_seconds_entity: <entity>`)

If brightness stays above the value of `dawn_brightness_threshold`, the shutter will be fully opened after the configured number of seconds. Default: 3600

#### D09 Height after seconds
(yaml: `dawn_height_after_dawn_manual: true|false` u/o `dawn_height_after_dawn_entity: <entity>`)

This is the shutter height in %, which should be set after the dawn position. Default: 0

#### D10 Angle after seconds
(yaml: `dawn_angle_after_dawn_manual: true|false` u/o `dawn_angle_after_dawn_entity: <entity>`)

This is the shutter angle in %, which should be set after the dawn position. Default: 0





## Configuration by YAML

It is possible to configure **Shadow Control** instances using YAML. To do so, you need to add the corresponding configuration to `configuration.yaml` and restart Home Assistant. After that, the YAML configuration be loaded and **Shadow Control** creates the corresponding instances. These instances could be modified afterward using Home Assistant ConfigFlow. Modifications right on the YAML content is not supportet. To reload the YAML configuration, you need to remove the existing **Shadow Control** instances and restart Home Assistant.

### Example YAML configuration

The entries within the configuration follow the mentioned keywords within the documentation above. Unused keywords must be commented (disabled) or removed.

```yaml
shadow_control:
  - name: "Büro West"
    #
    # Configure shutter mode by entering 'mode1', 'mode2' or 'mode3'
    # All *_angle_* settings will be ignored on mode3
    facade_shutter_type_static: mode1
    #
    # List of cover entities to handle by this Shadow Control instance
    target_cover_entity:
      - cover.fenster_buro_west
    #
    # Enable debug mode for way more log output
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
    #
    # Entities with next sunrise/sunset for adaptive brightness calculation
    #sunrise_entity: sensor.sun_next_rising
    #sunset_entity: sensor.sun_next_setting
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
    #enforce_positioning_entity: input_boolean.d13_enforce_positioning
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
    #shadow_brightness_threshold_winter_entity:
    #shadow_brightness_threshold_winter_manual: 30000
    #shadow_brightness_threshold_summer_entity:
    #shadow_brightness_threshold_summer_manual: 50000
    #shadow_brightness_threshold_buffer_entity:
    #shadow_brightness_threshold_buffer_manual: 1000
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
# State, return values and direct options

Each instance of **Shadow Control** creates a device within Home Assistant, which contains the following entities for further usage: 

![Sensors](/images/sensors.png)

## State and return values

### Target height
`target_height`
This entity holds the used shutter height.

### Target angle
`target_angle`
This entity holds the used shutter angle. This entity is only available with shutter type `mode1` and `mode2`.

### Target angle (degrees)
`target_angle_degrees`
This entity holds the used shutter angle in degrees (°). This entity is only available with shutter type `mode1` and `mode2`.

### Computed height
`computed_height`
Here you can find the calculated height of the cover. This value may differ from the actual height reached, for example if a movement restriction is active.

### Computed angle
`computed_angle`
Here you can find the calculated slat angle of the cover. This value may differ from the actual slat angle reached, for example if a movement restriction is active. This entity is only available for cover type `mode1` and `mode2`.

### Current state
`current_state` / `current_state_text` 
The entity `current_state` holds the current internal state of the integration as a numeric value. The following values will be available here for further usage within other automations:

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

Parallel to `current_state`, the entity `current_state_text` contains a textual representation aka a translated string of the current state. This string could be used right on the UI to show the current state of the corresponding **Shadow Control** instance.

### Lock state
`lock_state`
This entity is `True`, if the integration is locked. Otherwise `False`.

### Next shutter modification
`next_shutter_modification`
On this entity the integration publishes the next point in time, where a running timer will be finished.

### Is in the Sun
`is_in_sun`
This entity is either `True`, if the sun within the min-max-offset and the min-max-height range. Otherwise `False`.



## Direct options

Right on each device page some options could be switched on/off directly:

![Controls](/images/controls.png)

Modifying these options is the same as modifying them within the configuration flow.



# Configuration export

As the **Shadow Control** configuration might be very extensive, there is a special service to write the current configuration using YAML format to the Home Assistant log. 

## Preparation

For this to work, the log level of Home Assistant must be set to at least `info`. The following entry must be present in `configuration.yaml`:

```yaml
logger:
  default: info
```

The easiest way to access the log output is via the terminal or the Home Assistant console. There, you can run the following command to continuously display the Home Assistant log:

```bash
tail -F ~/config/home-assistant.log
```

Once the log output is running, execute the dump service and monitor the output in the terminal. You can stop the log output afterward with `Ctrl+C`.

## Usage

This service is available via `Developer tools -> Actions` by searching for `dump_sc_config`. If the service is triggered without further modification, the configuration of the first **Shadow Control** instance will be dumped to the log. That might look like this:

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

Between the two marker lines `--- YAML dump start ---` and `--- YAML dump end ---` is the complete configuration of the instance in YAML format. This can be copied and saved or used as a basis for additional instances.

The name of the configuration which should be exported can be given by the parameter `name`:

## UI mode

```
name: SC Dummy 3
```

## YAML mode

```yaml
action: shadow_control.dump_sc_configuration
data:
  name: SC Dummy 3
```

Resulting output within the log:

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
