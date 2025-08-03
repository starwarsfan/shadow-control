# Changes

## 0.9.0
* ...

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
