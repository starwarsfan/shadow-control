# =======================================================================
# State DAWN_NEUTRAL
from custom_components.shadow_control import ShutterState


async def _handle_state_dawn_neutral(self) -> ShutterState:
    self.logger.debug("Handle DAWN_NEUTRAL")
    current_brightness = self._get_current_brightness()

    shadow_handling_active = await self._is_shadow_control_enabled()
    shadow_threshold_close = self._shadow_config.brightness_threshold
    shadow_close_delay = self._shadow_config.after_seconds

    dawn_handling_active = await self._is_dawn_control_enabled()
    dawn_brightness = self._get_current_dawn_brightness()
    dawn_threshold_close = self._dawn_config.brightness_threshold
    dawn_close_delay = self._dawn_config.after_seconds
    height_after_dawn = self._dawn_config.height_after_dawn
    angle_after_dawn = self._dawn_config.angle_after_dawn

    is_in_sun = await self._check_if_facade_is_in_sun()
    neutral_height = self._facade_config.neutral_pos_height
    neutral_angle = self._facade_config.neutral_pos_angle

    if dawn_handling_active:
        if (
            dawn_brightness is not None
            and dawn_threshold_close is not None
            and dawn_brightness < dawn_threshold_close
            and dawn_close_delay is not None
        ):
            self.logger.debug(
                "State %s (%s): Dawn mode active and brightness (%s) below dawn threshold (%s), starting timer for %s (%ss)",
                ShutterState.DAWN_NEUTRAL,
                ShutterState.DAWN_NEUTRAL.name,
                dawn_brightness,
                dawn_threshold_close,
                ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING,
                dawn_close_delay,
            )
            await self._start_timer(dawn_close_delay)
            return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING
        if (
            is_in_sun
            and shadow_handling_active
            and current_brightness is not None
            and shadow_threshold_close is not None
            and current_brightness > shadow_threshold_close
            and shadow_close_delay is not None
        ):
            self.logger.debug(
                "State %s (%s): Within sun, shadow mode active and brightness (%s) above shadow threshold (%s), starting timer for %s (%ss)",
                ShutterState.DAWN_NEUTRAL,
                ShutterState.DAWN_NEUTRAL.name,
                current_brightness,
                shadow_threshold_close,
                ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING,
                shadow_close_delay,
            )
            await self._start_timer(shadow_close_delay)
            return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING
        if height_after_dawn is not None and angle_after_dawn is not None:
            await self._position_shutter(
                float(height_after_dawn),
                float(angle_after_dawn),
                stop_timer=True,
            )
            self.logger.debug(
                "State %s (%s): Moving shutter to after-dawn position (%s%%, %s%%).",
                ShutterState.DAWN_NEUTRAL,
                ShutterState.DAWN_NEUTRAL.name,
                height_after_dawn,
                angle_after_dawn,
            )
            return ShutterState.DAWN_NEUTRAL
        self.logger.warning(
            "State %s (%s): Height or angle after dawn not configured, staying at %s",
            ShutterState.DAWN_NEUTRAL,
            ShutterState.DAWN_NEUTRAL.name,
            ShutterState.DAWN_NEUTRAL,
        )
        return ShutterState.DAWN_NEUTRAL

    if (
        is_in_sun
        and shadow_handling_active
        and current_brightness is not None
        and shadow_threshold_close is not None
        and current_brightness > shadow_threshold_close
        and shadow_close_delay is not None
    ):
        self.logger.debug(
            "State %s (%s): Within sun, shadow mode active and brightness (%s) above shadow threshold (%s), starting timer for %s (%ss)",
            ShutterState.DAWN_NEUTRAL,
            ShutterState.DAWN_NEUTRAL.name,
            current_brightness,
            shadow_threshold_close,
            ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING,
            shadow_close_delay,
        )
        await self._start_timer(shadow_close_delay)
        return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING

    if neutral_height is not None and neutral_angle is not None:
        await self._position_shutter(
            float(neutral_height),
            float(neutral_angle),
            stop_timer=True,
        )
        self.logger.debug(
            "State %s (%s): Dawn mode disabled or requirements for shadow not given, moving to neutral position (%s%%, %s%%)",
            ShutterState.DAWN_NEUTRAL,
            ShutterState.DAWN_NEUTRAL.name,
            neutral_height,
            neutral_angle,
        )
        return ShutterState.NEUTRAL
    self.logger.warning(
        "State %s (%s): Neutral height or angle not configured, transitioning to %s",
        ShutterState.DAWN_NEUTRAL,
        ShutterState.DAWN_NEUTRAL.name,
        ShutterState.NEUTRAL,
    )
    return ShutterState.NEUTRAL
