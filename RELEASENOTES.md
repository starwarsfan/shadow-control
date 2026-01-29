# Changes

## 0.11.0
* Breaking change:
  * **Important: If you're using yaml configuration, you must rename the following options within your yaml files before updating to version 0.11.0 or higher!**
    * lock_integration_**static** -> lock_integration_**manual**
    * lock_integration_with_position_**static** -> lock_integration_with_position_**manual**
    * lock_height_**static** -> lock_height_**manual**
    * lock_angle_**static** -> lock_angle_**manual**
    * movement_restriction_height_**static** -> movement_restriction_height_**manual**
    * movement_restriction_angle_**static** -> movement_restriction_angle_**manual**
    * facade_neutral_pos_height_**static** -> facade_neutral_pos_height_**manual**
    * facade_neutral_pos_angle_**static** -> facade_neutral_pos_angle_**manual**
    * All options with **_static** suffix to **_manual** suffix within **shadow** configuration
    * All options with **_static** suffix to **_manual** suffix within **dawn** configuration
  * These renamed options are no longer configuration entries within ConfigFlow. They are now dynamically created as `switch`, `number` or `select` entities per **Shadow Control** instance and could be used either right on the instance detail view or directly within own automations. See [README.md](README.md) for naming of these entities.
* New additional entity `enforce_positioning_manual` with push button functionality to trigger recalculation and positioning of the shutter.
* Fix usage of default values if configuring a new instance via HA UI ConfigFlow.
* Use HA internal slugify functionality to sanitize instance names
* Enforcing of shutter positioning works now with configured external entity as well as a corresponding button on the instance view in parallel.
* Movement restriction handling for external entities refactored. The external entities could now use strings according to the used UI translation. Check [Movement restriction height within README.md](README.md#movement-restriction-height) or the readme.md of your UI language for details.
* Fix shutter repositioning after release of lock with position
* Fix initialization after Home Assistant restart
* Fix ignored lock in case lock is active and shutter are modified manually
* Implement automatic instance lock in case shutters are modified manually
* New config option `facade_max_movement_duration_static` to configure max movement duration from full closed to full open
* Activate automatic testing and add a ton of testcases ;-)
* Implement new feature to handle shadow brightness threshold according to summer solstice. To handle this the parameter `shadow_brightness_threshold_*` was renamed to `shadow_brightness_threshold_winter_*` and two new parameters were introduced: `shadow_brightness_threshold_summer_*` and `shadow_brightness_threshold_buffer_*`. As soon as `shadow_brightness_threshold_summer_*` is configured with a value greater than `shadow_brightness_threshold_winter_*`, the used brightness threshold will be computed using a sine curve between the two threshold values, with top of the curve at summer solstice. Northern and Southern Hemisphere will be handled according to the location of the Home Assistant instance. Option `shadow_brightness_threshold_buffer_*` could be used to shift the entire sine curve upwards to avoid false triggers in the limiting range of shading.
* Update naming of shadow and dawn configuration entries. Now they are streamlined from the configuration through the instance view up to the German and English documentation. Additionally they use a prefixes like "**S01 ...**", "**S02 ...**" ("**B01 ...**", "**B01 ...**" in German) and "**D01 ...**", "**D02 ...**" a.s.o. to define a logical order of **S**hadow and **D**awn configuration entries. This order is used within the ConfigFlow as well as the instance view.
* Error handling in case the used yaml configuration contains deprecated configuration keys from previous **Shadow Control** versions.

## 0.10.0
* Bugfix: Fixed position handling if movement is restricted and integration gets unlocked
* Additional sensor values to show computed height and angle in contrast to used height and angle. The values may differ because of movement restrictions or locking.

## 0.9.0
* Bugfix: Fixed position handling if movement is restricted and integration gets unlocked
* Internals: 
  * Automate release creation using GitHub Actions
  * Add full configuration example

## 0.8.0
* Reduce log output during normal operation
* Use local timezone for log statements regarding the next shutter position update
* Shutter mode 3:
  * Fixed warning messages within the log
  * Disabled some obsolete internal calculations

## 0.7.0
* Improve log dump service to generate c&p ready YAML output

## 0.6.0
* Implement usage of entities to restrict the height and angle movement direction
* Readme finetuning

## 0.5.0
* Add configuration dump service
* Implement new shutter type "Rolling shutter / blind"
* Improve readme files

## 0.4.0
* Allow usage of `input_boolean` as well as `binary_sensor` at 
  * `shadow_control_enabled_entity`
  * `dawn_control_enabled_entity`
  * `lock_integration_entity`
  * `lock_integration_with_position_entity`
  * `enforce_positioning_entity`
* Implement issue [#3 Show states in translated cleartext](https://github.com/starwarsfan/shadow-control/issues/3)
  * A new state sensor for each instance represents the textual value of the current state.
  * The sensor with the numeric state is still available
* Bump ruff from 0.12.1 to 0.12.2

## 0.3.0
* Own icon and logo within HACS
* Fixed trigger event handling
* Added configuration options to use separate entities 
  * to lock the instance or lock the instance with forced position
  * to set neutral height and neutral angle
* Added direct controls to dis-/enable right on the instance device page:
  * Instance lock
  * Instance lock with forced position
* Bump ruff from 0.12.0 to 0.12.1

## 0.2.0
* Added direct controls to dis-/enable right on the instance device page:
  * Shadow control mode
  * Dawn control mode
  * Debug mode
* Prepared icons and logos for usage within HACS branding repository
* Bump ruff from 0.11.13 to 0.12.0

## 0.1.0
* Initial release
* Migrated functionality from Edomi-LBS into Home Assistant custom integration
* Fully configurable using 
  * Home Assistant ConfigFlow
  * YAML import
