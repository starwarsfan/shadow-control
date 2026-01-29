"""Configuration validation helpers for Shadow Control."""

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .const import DEPRECATED_CONFIG_KEYS


def validate_and_warn_deprecated_config(
    hass: HomeAssistant,
    config: dict[str, Any],
    logger: logging.Logger,
    instance_name: str | None = None,
) -> dict[str, Any]:
    """
    Check for deprecated config keys and warn user.

    Args:
        hass: Home Assistant instance
        config: The configuration dict (will be modified in-place)
        logger: Logger instance
        instance_name: Optional instance name for notifications

    Returns:
        Modified config dict with deprecated keys removed

    """
    found_deprecated = []

    for key, info in DEPRECATED_CONFIG_KEYS.items():
        if key in config:
            deprecated_value = config[key]
            found_deprecated.append((key, deprecated_value, info))

            # Remove deprecated key from config
            config.pop(key)

            # Log detailed warning
            logger.warning(
                "DEPRECATED CONFIG: '%s' is no longer supported (deprecated in %s). Configured value '%s' will be IGNORED. Migration: %s",
                key,
                info["deprecated_in"],
                deprecated_value,
                info["migration_hint"],
            )

    # Also check in sc_internal_values if present
    if "sc_internal_values" in config:
        internal_values = config["sc_internal_values"]
        for key, info in DEPRECATED_CONFIG_KEYS.items():
            if key in internal_values:
                deprecated_value = internal_values[key]
                found_deprecated.append((key, deprecated_value, info))

                # Remove from internal values
                internal_values.pop(key)

                logger.warning(
                    "DEPRECATED CONFIG in sc_internal_values: '%s' is no longer supported (deprecated in %s). "
                    "Configured value '%s' will be IGNORED. Migration: %s",
                    key,
                    info["deprecated_in"],
                    deprecated_value,
                    info["migration_hint"],
                )

    # Create persistent notification if deprecated keys found
    if found_deprecated:
        _create_deprecation_notification(hass, found_deprecated, instance_name)

        # Summary log
        logger.warning(
            "Found %d deprecated configuration option(s) in %s. "
            "Please update your configuration.yaml to avoid this warning. "
            "Check Home Assistant notifications for migration guide.",
            len(found_deprecated),
            f"instance '{instance_name}'" if instance_name else "configuration",
        )

    return config


def _create_deprecation_notification(
    hass: HomeAssistant,
    deprecated_items: list[tuple[str, Any, dict]],
    instance_name: str | None,
) -> None:
    """
    Create a persistent notification about deprecated config.

    Args:
        hass: Home Assistant instance
        deprecated_items: List of (key, value, info) tuples
        instance_name: Optional instance name

    """
    title = "Shadow Control: Deprecated Configuration"
    if instance_name:
        title += f" ({instance_name})"

    message = "## ⚠️ Deprecated Configuration Options Found\n\n"
    message += "The following configuration options are **no longer supported** and have been **ignored**:\n\n"

    for key, value, info in deprecated_items:
        message += f"### `{key}`\n"
        message += f"- **Your value:** `{value}`\n"
        message += f"- **Deprecated in:** {info['deprecated_in']}\n"
        message += f"- **Migration:** {info['migration_hint']}\n\n"

    message += "---\n\n"
    message += "**Action Required:** Please update your `configuration.yaml` a/o your used `*.yaml` files to remove these deprecated options.\n\n"
    message += "See the [documentation](https://github.com/starwarsfan/shadow-control) for the current configuration format."

    # Create unique notification ID per instance
    notification_id = "shadow_control_deprecated_config"
    if instance_name:
        # Sanitize instance name for notification ID
        safe_name = instance_name.lower().replace(" ", "_").replace("-", "_")
        notification_id += f"_{safe_name}"

    # Use service call instead of hass.components (which may not be loaded yet)
    async def _create_notification_when_ready() -> None:
        """Create notification after HA has started."""
        await hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": title,
                "message": message,
                "notification_id": notification_id,
            },
            blocking=False,
        )

    # Schedule notification creation for when HA is ready
    hass.async_create_task(_create_notification_when_ready())
