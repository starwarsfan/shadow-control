#!/usr/bin/env bash

set -e

cd "$(dirname "$0")/.."

# Install test configurations
for currentConfig in custom_components/shadow_control/test/*.test.json; do
    targetName=${currentConfig//*\//}
    targetName="config/.storage/${targetName/.test.json/}"
    echo "Installing ${currentConfig} to ${targetName}"
    cp "${currentConfig}" "${targetName}"
done
