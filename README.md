# Shadow Control

**A custom component for Home Assistant to fully automate movement and positioning of rolling shutters.**

Shadow Control is the migration of my Edomi-LBS "Beschattungssteuerung-NG" to Home Assistant. As Edomi was [sentenced to death](https://knx-user-forum.de/forum/projektforen/edomi/1956975-quo-vadis-edomi) and because I'm not really happy with the existing solutions to automate my shutters, I decided to migrate the LBS (Edomi naming for **L**ogic**B**au**S**tein, a logic block) to a Home Assistant integration. To do so was a nice deep dive into the backgrounds of Home Assistant, the idea behind and how it works. Feel free to use the integration on your needs.

Within further description the word "facade" is similar to "window" or "door", as it simply references the azimuth of an object in the sense of view direction from that object to the sun.

## What it does

Based on several input values, the integration handles the positioning of rolling shutters. To do so, the integration needs to be configured with the azimuth of the facade, for which the shutters should be controlled. Additionally, some offset and min-max values will be used to define the area within the facade is illuminated by the sun. If the sun is within that range and the configured brightness threshold is passed for a (also configurable) amount of time, the shutters will be positioned to prevent direct sunlight in the room.

The determined shutter height and tilt angle depends on the current brightness, configured thresholds, dimensions of your shutter slats, some timers, and more settings. The different timers will be activated according to the current state of the integration.

In general, there are two different operation modes: _Shadow_ and _Dawn_. Both modes will be configured independently.

The integration will be triggered by updating the following entities: 

* brightness
* brightness_dawn
* sun_elevation
* sun_azimuth
* lock_integration
* lock_integration_with_position
* shadow_control_enabled
* dawn_control_enabled

The configured cover entity will only be updated, if a value has changed since the last run of the integration, which prevents unnecessary movements.

## Input entities

The configuration is structured into four blocks, which will be described in the following sections.

### Dynamic input entities

#### brightness

This input needs to be configured with the current brightness, which usually comes from a weather station. The value should match the real brightness on this facade as much as possible.

#### brightness_dawn

A second brightness value could be configured here, which is used to calculate shutter position at dawn. This is especially useful if more than one facade should be maintained and so more than one integration is configured. If all integrations use the same value here, all the shutters will move to dawn position at the same time, even if it's currently brighter on one facade than on the other side of the building.

If you have only one brightness sensor, this input should not be configured. Let the input stay empty in this case.

#### sun_elevation

This input should be filled with the current elevation of the sun. Usually this value is used from a weather station or the home assistant internal sun entity. Possible values are within the range from 0° (horizontal) to 90° (vertical).

#### sun_azimuth

This input should be filled with the current azimuth of the sun. Usually this value is used from a weather station or the home assistant internal sun entity. Possible values are within the range from 0° to 360°.

#### shutter_current_height

Connect this input with the actual, current height of the shutter. If the calculated height differs from the value on this input, the integration will lock itself.

This could be used to deactivate the automatic shutter positioning, in case the position was manually overridden. So if you open the shutter manually, this will not be replaced at the next run of the integration. You should unlock the integration after a certain amount of time manually or by using a timer. See `lock_integration` and `lock_integration_with_position`.

It is important how the used shutter actor behaves! If the actor updates its current position during runtime, it might lead to a deactivated integration. The reason for this is that the integration assumes a manual modification in this case. There are two solutions to handle this:

* Ignore the current shutter position
* Delay the update of this input by the amount of time, which your shutter requires for a full move.

#### shutter_current_angle

Connect this input with the actual, current angle of the shutter. The rest is the same as the previous configuration.

#### lock_integration

If this input is set to 'off', the integration works as desired by updating the output (as long as the input `lock_integration_with_position` is not set to 'on'). 

If the input is set to 'on', the integration gets locked. That means the integration is internally still working, but the configured shutter will not be updated but stay at the current position. With this approach the integration is able to immediately move the shutter to the right position, as soon as it gets unlocked again.

#### lock_integration_with_position

If this input is set to 'off', the integration works as desired by updating the output (as long as the input `lock_integration` is not set to 'on').

If the input is set to 'on', the integration gets locked. That means the integration is internally still working, but the configured shutter will be moved to the position, configured with the inputs 'lock_height' and 'lock_angle.' With this approach the integration is able to immediately move the shutter to the right position, as soon as it gets unlocked again.

This input has precedence over 'lock_integration.' If both lock inputs are set 'on', the shutter will be moved to the configured lock position.

#### lock_height

Height in %, which should be set if integration gets locked by 'lock_integration_with_position.' 

#### lock_angle

Angle in %, which should be set if integration gets locked by 'lock_integration_with_position.'

#### modification_tolerance_height

Tolerance range for external shutter height modification ('shutter_current_height'). If the calculated height is within the range of current height plus/minus this value, the integration will not lock itself. Default: 8

#### modification_tolerance_angle

Tolerance range for external shutter angle modification ('shutter_current_angle'). If the calculated angle is within the range of current angle plus/minus this value, the integration will not lock itself. Default: 5



### General settings

#### azimuth_facade

Azimuth of the facade in degrees, for which the integration should be configured. This is viewing direction from the inside to the outside. A perfectly north facade has an Azimuth of 0°, a perfectly south facade has an Azimuth of 180°. The sun area at this facade is the range, from which a shadow handling is desired. This is a maximal range of 180°, from `azimuth_facade` + `offset_sun_in` to `azimuth_facade` + `offset_sun_out`. 

#### offset_sun_in

Negative offset to `azimuth_facade`, from which shadow handling should be done. Default: -90

#### offset_sun_out

Positive offset to `azimuth_facade`, up to which shadow handling should be done. Default: 90

#### elevation_sun_min

Minimal elevation (height) of the sun in degrees. If the effective (!) elevation is lower than this value, no shadow handling will be performed. A use case for this configuration is another building in front of the facade, which throws shadow onto the facade, whereas the weather station on the roof is still full in the sun. Default: 0

Hint regarding effective elevation: To compute the right shutter angle, the elevation of the sun in the right angle to the facade must be computed. This so-called "effective elevation" is written to the log. If the shadow handling is not working as desired, especially nearly the limits of the given azimuth offsets, this value needs attention.

#### elevation_sun_max

Maximal elevation (height) of the sun in degrees. If the effective (!) elevation is higher than this value, no shadow handling will be performed. A use case for this configuration is a balcony from the story above, which throws shadow onto the facade, whereas the weather station on the roof is still full in the sun. Default: 90

#### slat_width

Width of the shutter slats in mm. Width and distance are required to compute the angle, which is used to close the shutter only that much, to prevent direct sun rays within the room. The slat width must be larger than the slat distance, otherwise it's impossible to set up the correct shadow position. Default: 80

#### slat_distance

Distance of the shutter slats in mm. Everything else described on previous configuation entry. Default: 40

#### angle_offset

#### min_slat_angle

#### stepping_height

#### stepping_angle

#### shutter_type

#### light_bar_width

#### shutter_height

#### neutral_pos_height

#### neutral_pos_angle

#### movement_restriction_height

#### movement_restriction_angle

#### update_lock_output

### Shadow settings

#### shadow_control_enabled

#### shadow_brightness_level

#### shadow_after_seconds

#### shadow_max_height

#### shadow_max_angle

#### shadow_look_through_seconds

#### shadow_open_seconds

#### shadow_look_through_angle

#### after_shadow_height

#### after_shadow_angle

### Dawn settings

#### dawn_control_enabled

#### dawn_brightness_level

#### dawn_after_seconds

#### dawn_max_height

#### dawn_max_angle

#### dawn_look_through_seconds

#### dawn_open_seconds

#### dawn_look_through_angle

#### after_dawn_height

#### after_dawn_angle
