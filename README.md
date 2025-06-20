# Shadow Control

**A Home Assistant integration to fully automate movement and positioning of rolling shutters.**

## Table of content

* [Shadow Control](#shadow-Control)
  * [Table of content](#table-of-content)
* [Introduction](#introduction)
* [What it does](#what-it-does)
* [Configuration](#configuration)
  * [Initial instance configuration](#initial-instance-configuration)
    * [Instance name ](#instance-name-)
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
      * [Tolerance height modification](#tolerance-height-modification)
      * [Tolerance angle modification](#tolerance-angle-modification)
      * [Shutter type](#shutter-type)
    * [Dynamic input entities](#dynamic-input-entities)
      * [Brightness](#brightness)
      * [Brightness Dawn](#brightness-Dawn)
      * [Sun elevation](#sun-elevation)
      * [Sun azimuth](#sun-azimuth)
      * [Lock integration](#lock-integration)
      * [Lock integration with position](#lock-integration-with-position)
      * [Lock height](#lock-height)
      * [Lock angle](#lock-angle)
      * [Movement restriction height](#movement-restriction-height)
      * [Movement restriction angle](#movement-restriction-angle)
      * [Enforce shutter positioning](#enforce-shutter-positioning)
    * [Shadow settings](#shadow-settings)
      * [Shadow control enabled](#shadow-control-enabled)
      * [Shadow brightness threshold](#shadow-brightness-threshold)
      * [Shadow after seconds](#shadow-after-seconds)
      * [Shadow max height](#shadow-max-height)
      * [Shadow max angle](#shadow-max-angle)
      * [Shadow look through seconds](#shadow-look-through-seconds)
      * [Shadow open seconds](#shadow-open-seconds)
      * [Shadow look through angle](#shadow-look-through-angle)
      * [Shadow height after sun](#shadow-height-after-sun)
      * [Shadow angle after sun](#shadow-angle-after-sun)
    * [Dawn settings](#dawn-settings)
      * [Dawn control enabled](#dawn-control-enabled)
      * [Dawn brightness threshold](#dawn-brightness-threshold)
      * [Dawn after seconds](#dawn-after-seconds)
      * [Dawn max height](#dawn-max-height)
      * [Dawn max angle](#dawn-max-angle)
      * [Dawn look through seconds](#dawn-look-through-seconds)
      * [Dawn open seconds](#dawn-open-seconds)
      * [Dawn look through angle](#dawn-look-through-angle)
      * [After dawn height](#after-dawn-height)
      * [After dawn angle](#after-dawn-angle)
  * [Configuration by yaml](#configuration-by-yaml)
    * [Example YAML configuration](#example-yaml-configuration)
* [State and return values](#state-and-return-values)
  * [Target height](#target-height)
  * [Target angle](#target-angle)
  * [Target angle (degrees)](#target-angle-degrees)
  * [Current state](#current-state)
  * [Lock state](#lock-state)
  * [Next shutter modification](#next-shutter-modification)
  * [Is in the Sun](#is-in-the-sun)

# Introduction

**Shadow Control** is the migration of my Edomi-LBS "Beschattungssteuerung-NG" to Home Assistant. As Edomi was [sentenced to death](https://knx-user-forum.de/forum/projektforen/edomi/1956975-quo-vadis-edomi) and because I'm not really happy with the existing solutions to automate my shutters, I decided to migrate my LBS (Edomi name for **L**ogic**B**au**S**tein, a logic block) to a Home Assistant integration. To do so was a nice deep dive into the backgrounds of Home Assistant, the idea behind and how it works. Feel free to use the integration on your needs.

Within further description:

* The word "facade" is similar to "window" or "door," as it simply references the azimuth of an object in the sense of view direction from within that object to the outside.
* The word "shutter" references rolling shutters. In the Home Assistant terminology, this is called a "cover". From the pov of this integration it's the same.
* The whole internal logic was initially developed to interact with a KNX system, so the main difference is the handling of %-values. **Shadow Control** will interact with Home Assistant correct but the configuration as well as the log output is using 0% as fully open and 100% as fully closed.

# What it does

Based on several input values, the integration handles the positioning of rolling shutters. To do so, the integration needs to be configured with the azimuth of the facade, for which the shutters should be controlled. Additionally, some offset and min-max values will be used to define the area within the facade is illuminated by the sun. If the sun is within that range and the configured brightness threshold is exceeded for a (also configurable) amount of time, the shutters will be positioned to prevent direct sunlight in the room.

The determined shutter height and tilt angle depend on the current brightness, configured thresholds, dimensions of your shutter slats, some timers, and more settings. The different timers will be activated according to the current state of the integration.

In general, there are two different operation modes: _Shadow_ and _Dawn_. Both modes will be configured independently.

The integration will be triggered by updating the following entities: 

* [Brightness](#brightness)
* [Brightness (dawn)](#brightness-dawn)
* [Sun elevation](#sun-elevation)
* [Sun azimuth](#sun-azimuth)
* [Lock integration](#lock-integration)
* [Lock integration with position](#lock-integration-with-position)
* [Shadow handling dis-/enabled state](#shadow-control-enabled)
* [Dawn handling dis-/enabled state](#dawn-control-enabled)

The configured cover entity will only be updated if a value has changed since the last run of the integration, which prevents unnecessary movements.

# Configuration

The configuration is split into a minimalistic initial configuration, which results in a fully working cover automation and a separate configuration flow of all available options.



## Initial instance configuration

The initial instance configuration is very minimalistic and requires only the following configuration entries. Everything else will be setup up with default values, which you might tweak to your needs afterward. See section "Optional configuration."

### Instance name 
`name`

A descriptive and unique name for this **Shadow Control** (SC) instance. A sanitized version of this name will be used to mark corresponding log entries of this instance within the Home Assistant main log file.

### Covers to maintain
`target_cover_entity`

The cover entities, which should be handled by this **Shadow Control** (SC) instance. You can add as many covers as you like, but the recommendation is to use only these covers, which have at least the same azimuth. For any further calculation, only the first configured cover will be used. All other covers will just be positioned as the first one.

### Facade azimuth
`facade_azimuth_static`

Azimuth of the facade in degrees, for which the integration should be configured. This is the viewing direction from the inside to the outside. A perfectly north facade has an Azimuth of 0°, a perfectly south facade has an Azimuth of 180°. The sun area at this facade is the range, from which a shadow handling is desired. This is a maximal range of 180°, from `azimuth_facade` + `offset_sun_in` to `azimuth_facade` + `offset_sun_out`.

rdeckard has provided a nice drawing to the Edomi-LBS, which is still valid at this point:

![Azimuth explanation](/images/azimut.png)

### Brightness
`brightness_entity`

This input needs to be configured with the current brightness, which usually comes from a weather station. The value should match the real brightness on this facade as much as possible.

### Sun elevation
`sun_elevation_entity`

This input should be filled with the current elevation of the sun. Usually this value comes from a weather station or the home assistant internal sun entity. Possible values are within the range from 0° (horizontal) to 90° (vertical).

### Sun azimuth
`sun_azimuth_entity`

This input should be filled with the current azimuth of the sun. Usually this value comes from a weather station or the home assistant internal sun entity. Possible values are within the range from 0° to 359°.





## Additional options

The following options will be available by a separate config flow, which will open up with a click on "Configure" at the desired instance right on Settings > Integrations > **Shadow Control**.

### Facade configuration - part 1

#### Covers to maintain
`target_cover_entity`

See the description at [Covers to maintain](#covers-to-maintain).

#### Facade azimuth
`facade_azimuth_static`

See the description at [Facade azimuth](#facade-azimuth).

#### Sun start offest
`facade_offset_sun_in_static`

Negative offset to `facade_azimuth_static`, from which shadow handling should be done. If the azimuth of the sun is lower than `facade_azimuth_static + facade_offset_sun_in_static`, no shadow handling will be performed. Valid range: -90–0, default: -90

#### Sun end offset
`facade_offset_sun_out_static`

Positive offset to `facade_azimuth_static`, up to which shadow handling should be done. If the azimuth of the sun is higher than `facade_azimuth_static + facade_offset_sun_out_static`, no shadow handling will be performed. Valid range: 0–90, default: 90

#### Min sun elevation
`facade_elevation_sun_min_static`

Minimal elevation (height) of the sun in degrees. If the effective (!) elevation is lower than this value, no shadow handling will be performed. A use case for this configuration is another building in front of the facade, which throws shadow onto the facade, whereas the weather station on the roof is still full in the sun. Valid range: 0–90, default: 0

Hint regarding effective elevation: To compute the right shutter angle, the elevation of the sun in the right angle to the facade must be computed. This so-called "effective elevation" is written to the log. If the shadow handling is not working as desired, especially nearly the limits of the given azimuth offsets, this value needs attention.

#### Max sun elevation
`facade_elevation_sun_max_static`

Maximal elevation (height) of the sun in degrees. If the effective (!) elevation is higher than this value, no shadow handling will be performed. A use case for this configuration is a balcony from the story above, which throws shadow onto the facade, whereas the weather station on the roof is still full in the sun. Valid range: 0–90, default: 90

#### Debug mode
`debug_enabled`

With this switch, the debug mode for this instance could be activated. If activated, there will be much more detailed output within the Home Assistant main log file.



### Facade configuration - part 2

#### Neutral position height
`facade_neutral_pos_height_static`

Shutter height position in state _NEUTRAL_. The integration will switch to _NEUTRAL_ if

* the integration is within a shadow- or a dawn-state and the corresponding regulation will be deactivated _or_
* the sun leaves the facade range.

Default: 0

#### Neutral position angle
`facade_neutral_pos_angle_static`

Shutter angle position in state _NEUTRAL_. Everything else is described in the previous configuration entry. Default: 0

#### Shutter slat width
`facade_slat_width_static`)

The Width of the shutter slats in mm. Width and distance are required to compute the angle, which is used to close the shutter only that much, to prevent direct sun rays within the room. The slat width must be larger than the slat distance, otherwise it's impossible to set up the correct shadow position. Default: 95

#### Shutter slat distance
`facade_slat_distance_static`

The distance of the shutter slats in mm. Everything else is described in the previous configuration entry. Default: 67

#### Shutter angle offset
`facade_slat_angle_offset_static`

Angle offset in %. This value will be added to the computed slat angle and could be used if the computed angle needs to be corrected. This could be necessary if the shadow position has a slight gap, which lets the sun pass through. Default: 0

#### Min shutter angle
`facade_slat_min_angle_static`

Min shutter slat angle in %. The slat position will be in the range of this value and 100%. This option could be used to restrict the opening range of the shutter slats. Default: 0

#### Height stepping
`facade_shutter_stepping_height_static`

Stepping size for shutter height positioning. Most shutters could not handle repositioning of small values within the percent range. To handle this, the height will be modified in steps of a given size. Increasing or decreasing elevation of the sun will be handled properly. Default: 5

#### Angle stepping
`facade_shutter_stepping_angle_static`

Same as "Height stepping" but for the shutter slat angle positioning. Default: 5

#### Width of a light strip
`facade_light_strip_width_static`

Width of a desired light strip. With this setting could be configured, how "deep" the sun should shine directly into the room. According to this setting, during shadow the shutter will not be at a height position of 100% (aka full closed) but instead at a computed height position, which produces the desired light strip. Default: 0

#### Overall shutter height
`facade_shutter_height_static`

To compute the light strip given with the previous configuration option, the integration needs to know the overall height of the shutter (or window). The same unit as on light bar width must be used. Default: 1000

#### Tolerance height modification
`facade_modification_tolerance_height_static`

Tolerance range for external shutter height modification. If the calculated height is within the range of current height plus/minus this value, the integration will not lock itself. Default: 8

#### Tolerance angle modification
`facade_modification_tolerance_angle_static`

Same as [Tolerance height modification](#tolerance-height-modification) but for the shutter slat angle. Default: 5

#### Shutter type
`facade_shutter_type_static`

Configuration of the used shutter type.

Default is pivoting range of 0°-90°. These shutters are fully closed (vertical) at 90° and horizontally open at 0°.

The other possible shutter type has a movement range from 0°-180°, whereas these shutters are closed to the inside at 0°, horizontally open at 90°, and closed to the outside at 180°.





### Dynamic input entities

The options within this section are called "dynamic settings," as they might be modified "dynamically." That covers such things like position updates of the sun or modification of the integration behavior in general.

#### Brightness
`brightness_entity`

See the description at [Brightness](#brightness).

#### Brightness Dawn
`brightness_dawn_entity`

A second brightness value could be configured here, which is used to calculate shutter position at dawn. This is especially useful if 

* more than one brightness is used, e.g., with different sensors per facade and
* more than one facade should be automated, and so more than one integration is configured. 

If you're using more than one brightness sensor, you might set up an automation, which computes the median for all these values. After that, use that automation as input here. All the shutters will move to dawn position at the same time, even if it's currently brighter on one facade than on the other side of the building.

If you have only one brightness sensor, this input should not be configured. Let the input stay empty in this case.

#### Sun elevation
`sun_elevation_entity`

See the description at [Sun elevation](#sun-elevation).

#### Sun azimuth
`sun_azimuth_entity`

See the description at [Sun azimuth](#sun-azimuth).

#### Lock integration
`lock_integration_entity`

If this input is set to 'off,' the integration works as desired by updating the output (as long as the input `lock_integration_with_position` is not set to 'on'). 

If the input is set to 'on,' the integration gets locked. That means the integration is internally still working, but the configured shutter will not be updated and stay at the current position. With this approach, the integration is able to immediately move the shutter to the right position, as soon as it gets unlocked again.

#### Lock integration with position
`lock_integration_with_position_entity`

If this input is set to 'off,' the integration works as desired by updating the output (as long as the input `lock_integration` is not set to 'on').

If the input is set to 'on,' the integration gets locked. That means the integration is internally still working, but the configured shutter will be moved to the position, configured with the inputs 'lock_height' and 'lock_angle.' With this approach, the integration is able to immediately move the shutter to the right position, as soon as it gets unlocked again.

This input has precedence over 'lock_integration.' If both lock inputs are set 'on,' the shutter will be moved to the configured lock position.

#### Lock height
`lock_height_static`

Height in %, which should be set if integration gets locked by 'lock_integration_with_position.' 

#### Lock angle
`lock_angle_static`

Angle in %, which should be set if integration gets locked by 'lock_integration_with_position.'

#### Movement restriction height
`movement_restriction_height_entity`

With this setting, the movement direction could be restricted:

* "No restriction" (Default)
  No striction on shutter movement. The automation will open or close the shutter.
* "Only close"
  In comparison to the current position, only closing positions will be activated.
* "Only open"
  In comparison to the current position, only opening positions will be activated.

This could be used to prevent shutters from being opened after the sun goes down and close them some minutes later because of starting dawn. This setting might be modified using a timer clock or other appropriate automation.

#### Movement restriction angle
`movement_restriction_angle_entity`

Same as [Movement restriction height](#movement-restriction-height) but for the shutter slat angle.

#### Enforce shutter positioning
`enforce_positioning_entity`

This input could be wired with a boolean entity. If this entity is switched to "on," the shutter positioning will be enforced. That means that with every run of the integration, the shutter will be positioned. This could be used to align the shutter position with the computed position of the integration but should normally not be activated all the time. Otherwise, the shutter slats might close and immediately open again as that is how rolling shutters work: At first the move to the given height and position the shutter slats afterward.



### Shadow settings

The following options are available with two flavors for each configuration: Once as a static configuration and once as entity configuration. If you need to configure something without the possibility to change that value on demand, you should use the static configuration entry. If you need to modify something on demand, use the entity configuration and choose the corresponding entity, which holds the required value. If you change the used entity, it will be taken into account within the next execution of the integration instance.

#### Shadow control enabled
`shadow_control_enabled_static` / `shadow_control_enabled_entity`

With this option, the whole shadow handling could be de-/activated. Default: on

#### Shadow brightness threshold
`shadow_brightness_threshold_static` / `shadow_brightness_threshold_entity`

This is the brightness threshold in Lux. If the threshold is exceeded, the timer `shadow_after_seconds` is started. Default: 50000 

#### Shadow after seconds
`shadow_after_seconds_static` / `shadow_after_seconds_entity`

This is the number of seconds which should be passed after the exceedance of `shadow_brightness_threshold`, until the shutter will be moved to the shadow position. Default: 120

#### Shadow max height
`shadow_shutter_max_height_static` / `shadow_shutter_max_height_entity`

Max height of the shutter in case of shadow position in %. Default: 100 

#### Shadow max angle
`shadow_shutter_max_angle_static` / `shadow_shutter_max_angle_entity`

Max angle of the shutter in case of shadow position in %. Default: 100 

#### Shadow look through seconds
`shadow_shutter_look_through_seconds_static` / `shadow_shutter_look_through_seconds_entity`

If brightness falls below the value of `shadow_brightness_threshold`, the shutter slats will be moved to horizontal position after the configured number of seconds. Default: 900

#### Shadow open seconds
`shadow_shutter_open_seconds_static` / `shadow_shutter_open_seconds_entity`

If brightness stays below the value of `shadow_brightness_threshold`, the shutter will be fully opened after the configured number of seconds. Default: 3600

#### Shadow look through angle
`shadow_shutter_look_through_angle_static` / `shadow_shutter_look_through_angle_entity`

This is the shutter slat angle in %, which should be used at the "look through" position. Default: 0

#### Shadow height after sun
`shadow_height_after_sun_static` / `shadow_height_after_sun_entity`

This is the shutter height in %, which should be set after the shadow position. Default: 0

#### Shadow angle after sun
`shadow_angle_after_sun_static` / `shadow_angle_after_sun_entity`

This is the shutter angle in %, which should be set after the shadow position. Default: 0





### Dawn settings

#### Dawn control enabled
`dawn_control_enabled_static` / `dawn_control_enabled_entity`

With this option, the whole dawn handling could be de-/activated. Default: on

#### Dawn brightness threshold
`dawn_brightness_threshold_static` / `dawn_brightness_threshold_entity`

This is the brightness threshold in Lux. If the threshold is undercut, the timer `dawn_after_seconds` is started. Default: 500

#### Dawn after seconds
`dawn_after_seconds_static` / `dawn_after_seconds_entity`

This is the number of seconds which should be passed after `dawn_brightness_threshold` was undercut, until the shutter will be moved to the dawn position. Default: 120

#### Dawn max height
`dawn_shutter_max_height_static` / `dawn_shutter_max_height_entity`

Max height of the shutter in case of dawn position in %. Default: 100

#### Dawn max angle
`dawn_shutter_max_angle_static` / `dawn_shutter_max_angle_entity`

Max angle of the shutter in case of shadow position in %. Default: 100

#### Dawn look through seconds
`dawn_shutter_look_through_seconds_static` / `dawn_shutter_look_through_seconds_entity`

If brightness exceeds the value of `dawn_brightness_threshold`, the shutter slats will be moved to horizontal position after the configured number of seconds. Default: 120

#### Dawn open seconds
`dawn_shutter_open_seconds_static` / `dawn_shutter_open_seconds_entity`

If brightness stays above the value of `dawn_brightness_threshold`, the shutter will be fully opened after the configured number of seconds. Default: 3600

#### Dawn look through angle
`dawn_shutter_look_through_angle_static` / `dawn_shutter_look_through_angle_entity`

This is the shutter slat angle in %, which should be used at the "look through" position. Default: 0

#### After dawn height
`dawn_height_after_dawn_static` / `dawn_height_after_dawn_entity`

This is the shutter height in %, which should be set after the shadow position. Default: 0

#### After dawn angle
`dawn_angle_after_dawn_static` / `dawn_angle_after_dawn_entity`

This is the shutter angle in %, which should be set after the shadow position. Default: 0

## Configuration by YAML

It is possible to configure **Shadow Control** instances using YAML. To do so, you need to add the corresponding configuration to `configuration.yaml` and restart Home Assistant. After that, the YAML configuration be loaded and **Shadow Control** creates the corresponding instances. These instances could be modified afterward using Home Assistant ConfigFlow. Modifications right on the YAML content is not supportet. To reload the YAML configuration, you need to remove the existing **Shadow Control** instances and restart Home Assistant.

### Example YAML configuration

The entries within the configuration follow the mentioned keywords within the documentation above. Unused keywords must be commented (disabled) or removed.

```yaml
shadow_control:
  - name: "Büro West"
    debug_enabled: false
    target_cover_entity:
      - cover.fenster_buro_west

    # =======================================================================
    # Dynamic configuration inputs
    brightness_entity: input_number.d01_brightness
    #brightness_dawn_entity: input_number.d02_brightness_dawn
    sun_elevation_entity: input_number.d03_sun_elevation
    sun_azimuth_entity: input_number.d04_sun_azimuth
    lock_integration_entity: input_boolean.d07_lock_integration
    lock_integration_with_position_entity: input_boolean.d08_lock_integration_with_position
    lock_height_static: 0
    lock_angle_static: 0
    movement_restriction_height_entity: no_restriction
    movement_restriction_angle_entity: no_restriction
    enforce_positioning_entity: input_boolean.d13_enforce_positioning

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
    # Either 'mode1' or 'mode2'
    facade_shutter_type_static: mode1
    facade_light_strip_width_static: 0
    facade_shutter_height_static: 1000
    facade_neutral_pos_height_static: 0
    facade_neutral_pos_angle_static: 0
    facade_modification_tolerance_height_static: 8
    facade_modification_tolerance_angle_static: 5

    # =======================================================================
    # Shadow configuration
    #shadow_control_enabled_entity:
    shadow_control_enabled_static: true
    #shadow_brightness_threshold_entity:
    shadow_brightness_threshold_static: 50000
    #shadow_after_seconds_entity:
    shadow_after_seconds_static: 15
    #shadow_shutter_max_height_entity:
    shadow_shutter_max_height_static: 100
    #shadow_shutter_max_angle_entity:
    shadow_shutter_max_angle_static: 100
    #shadow_shutter_look_through_seconds_entity:
    shadow_shutter_look_through_seconds_static: 15
    #shadow_shutter_open_seconds_entity:
    shadow_shutter_open_seconds_static: 15
    #shadow_shutter_look_through_angle_entity:
    shadow_shutter_look_through_angle_static: 0
    #shadow_height_after_sun_entity:
    shadow_height_after_sun_static: 0
    #shadow_angle_after_sun_entity:
    shadow_angle_after_sun_static: 0

    # =======================================================================
    # Dawn configuration
    #dawn_control_enabled_entity:
    dawn_control_enabled_static: true
    #dawn_brightness_threshold_entity:
    dawn_brightness_threshold_static: 500
    #dawn_after_seconds_entity:
    dawn_after_seconds_static: 15
    #dawn_shutter_max_height_entity:
    dawn_shutter_max_height_static: 100
    #dawn_shutter_max_angle_entity:
    dawn_shutter_max_angle_static: 100
    #dawn_shutter_look_through_seconds_entity:
    dawn_shutter_look_through_seconds_static: 15
    #dawn_shutter_open_seconds_entity:
    dawn_shutter_open_seconds_static: 15
    #dawn_shutter_look_through_angle_entity:
    dawn_shutter_look_through_angle_static: 50
    #dawn_height_after_dawn_entity:
    dawn_height_after_dawn_static: 0
    #dawn_angle_after_dawn_entity:
    dawn_angle_after_dawn_static: 0
```
# State and return values

Each instance of **Shadow Control** creates a device within Home Assistant, which contains the following entities for further usage: 

## Target height
`target_height`
This entity holds the calculated shutter height.

## Target angle
`target_angle`
This entity holds the calculated shutter angle.

## Target angle (degrees)
`target_angle_degrees`
This entity holds the calculated shutter angle in degrees (°).

## Current state
`current_state`
This entity holds the current internal state of the integration as a numeric value. The follwoing values will be available here for further usage within other automations:

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

## Lock state
`lock_state`
This entity is `True`, if the integration is locked. Otherwise `False`.

## Next shutter modification
`next_shutter_modification`
On this entity the integration publishes the next point in time, where a running timer will be finished.

## Is in the Sun
`is_in_sun`
This entity is either `True`, if the sun within the min-max-offset and the min-max-height range. Otherwise `False`.
