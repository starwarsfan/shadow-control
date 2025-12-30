"""Constants for shadow_control tests."""

from custom_components.shadow_control.const import (
    DEBUG_ENABLED,
    SC_CONF_COVERS,
    SC_CONF_NAME,
    TARGET_COVER_ENTITY,  # ✅ Ohne _ID!
)

# Mock Config Data - Minimale Konfiguration für einen Cover
MOCK_COVER_CONFIG = {
    TARGET_COVER_ENTITY: "cover.test_cover",  # ✅ Richtig!
}

MOCK_CONFIG_DATA = {
    SC_CONF_NAME: "Test Shadow Control",
    SC_CONF_COVERS: [MOCK_COVER_CONFIG],
    DEBUG_ENABLED: False,
}

# Mock User Input für Config Flow
MOCK_CONFIG_USER_INPUT = {
    SC_CONF_NAME: "Test Shadow Control",
    DEBUG_ENABLED: False,
}

# Mock Cover Entity ID
MOCK_COVER_ENTITY_ID = "cover.test_cover"
